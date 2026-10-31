"""Recursive Arena match crawler and timeline parser.

The crawler performs a breadth-first traversal of Arena match histories. It
starts from seed PUUIDs, fetches their Arena match ids, and for each unseen
match downloads the match and its timeline, parses participant stats and item
purchases into the database, and enqueues every newly discovered PUUID so the
dataset expands continuously.
"""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from typing import Iterable, Sequence

from src.config import Settings
from src.crawler.timeline import (
    assign_rounds_to_purchases,
    build_skill_orders,
    build_skill_progression,
    extract_item_purchases,
    extract_skill_level_ups,
)
from src.database.repositories import (
    CrawlQueueRepository,
    ItemPurchaseRecord,
    ItemPurchaseRepository,
    MatchRepository,
    ParticipantRepository,
    ParticipantStatsRecord,
)
from src.riot.client import RiotClient
from src.riot.models import Match, Participant

logger = logging.getLogger(__name__)

__all__ = ["Crawler", "extract_patch_minor"]


def extract_patch_minor(game_version: str) -> str:
    """Extract the major.minor patch (e.g. ``"26.21"``) from a game version."""
    parts = game_version.split(".")
    return ".".join(parts[:2]) if len(parts) >= 2 else game_version


def build_partner_map(match: Match) -> dict[str, int | None]:
    """Map each PUUID to its duo partner's champion id.

    Arena subteams are two-player pairs; participants are grouped by
    ``subteamId`` (falling back to ``teamId`` for custom lobbies without
    subteam metadata).
    """
    groups: dict[int, list[Participant]] = defaultdict(list)
    for participant in match.info.participants:
        key = participant.subteam_id if participant.subteam_id is not None else participant.team_id
        groups[key].append(participant)

    partner_by_puuid: dict[str, int | None] = {}
    for group in groups.values():
        for participant in group:
            partner = next(
                (other.champion_id for other in group if other.puuid != participant.puuid),
                None,
            )
            partner_by_puuid[participant.puuid] = partner
    return partner_by_puuid


class Crawler:
    """Asynchronous recursive Arena match crawler."""

    def __init__(
        self,
        client: RiotClient,
        matches: MatchRepository,
        participants: ParticipantRepository,
        purchases: ItemPurchaseRepository,
        queue_repo: CrawlQueueRepository,
        settings: Settings,
        *,
        target_patch_minor: str | None = None,
        max_matches: int | None = None,
    ) -> None:
        self._client = client
        self._matches = matches
        self._participants = participants
        self._purchases = purchases
        self._queue_repo = queue_repo
        self._settings = settings
        self._target_patch_minor = target_patch_minor
        self._max_matches = max_matches

        self._queue_ids: tuple[int, ...] = tuple(settings.queue_ids)
        self._inbox: asyncio.Queue[tuple[str, int]] = asyncio.Queue()
        self._queued: set[tuple[str, int]] = set()
        self._new_matches = 0
        self._stop_event = asyncio.Event()

    async def crawl(self, seed_puuids: Iterable[str]) -> int:
        """Crawl from the given seeds and return the number of new matches seen.

        Crawling stops early when ``max_matches`` (set on the constructor) is
        reached, which is useful for bounded smoke runs and resumable batches.
        """
        self._new_matches = 0
        self._stop_event.clear()
        for puuid in seed_puuids:
            await self._enqueue_puuid(puuid)

        for row in self._queue_repo.pending(limit=5000):
            await self._enqueue_puuid(row["puuid"], row["queue_id"])

        workers = [
            asyncio.create_task(self._worker(), name=f"crawler-{index}")
            for index in range(self._settings.crawler_concurrency)
        ]
        await asyncio.wait(
            {
                asyncio.create_task(self._inbox.join()),
                asyncio.create_task(self._stop_event.wait()),
            },
            return_when=asyncio.FIRST_COMPLETED,
        )
        for worker in workers:
            worker.cancel()
        await asyncio.gather(*workers, return_exceptions=True)
        return self._new_matches

    async def _worker(self) -> None:
        while not self._stop_event.is_set():
            puuid, queue_id = await self._inbox.get()
            try:
                await self._crawl_seed(puuid, queue_id)
                if self._max_matches is not None and self._new_matches >= self._max_matches:
                    self._stop_event.set()
            except Exception:
                logger.exception("Failed to crawl PUUID %s (queue %s)", puuid, queue_id)
            finally:
                self._inbox.task_done()

    async def _enqueue_puuid(self, puuid: str, queue_id: int | None = None) -> None:
        target_queues: Iterable[int] = self._queue_ids if queue_id is None else (queue_id,)
        for qid in target_queues:
            key = (puuid, qid)
            if key in self._queued:
                continue
            self._queued.add(key)
            if self._queue_repo.is_crawled(puuid, qid):
                continue
            self._queue_repo.enqueue(puuid, qid)
            await self._inbox.put(key)

    async def _crawl_seed(self, puuid: str, queue_id: int) -> None:
        match_ids = await self._fetch_match_ids(puuid, queue_id)
        for match_id in match_ids:
            if self._matches.exists(match_id):
                continue
            await self._process_match(match_id)
        self._queue_repo.mark_crawled(puuid, queue_id)

    async def _fetch_match_ids(self, puuid: str, queue_id: int) -> list[str]:
        ids: list[str] = []
        count = self._settings.crawler_match_history_count
        for page in range(self._settings.crawler_max_matches_per_seed):
            batch = await self._client.get_match_history(
                puuid, queue_id, count=count, start=page * count
            )
            ids.extend(batch)
            if len(batch) < count:
                break
        return ids

    async def _process_match(self, match_id: str) -> None:
        match = await self._client.get_match(match_id)
        patch_minor = extract_patch_minor(match.game_version)

        if self._target_patch_minor is not None and patch_minor != self._target_patch_minor:
            self._matches.insert(
                match.match_id, match.game_version, patch_minor, match.info.game_duration
            )
            return

        timeline = await self._client.get_timeline(match_id)
        purchases = assign_rounds_to_purchases(extract_item_purchases(timeline))
        level_ups = extract_skill_level_ups(timeline)
        skill_orders = build_skill_orders(level_ups)
        partner_map = build_partner_map(match)

        self._matches.insert(
            match.match_id, match.game_version, patch_minor, match.info.game_duration
        )

        item_records: list[ItemPurchaseRecord] = []
        for purchase in purchases:
            participant = match.participant_by_id(purchase.participant_id)
            if participant is None:
                continue
            item_records.append(
                ItemPurchaseRecord(
                    match_id=match.match_id,
                    puuid=participant.puuid,
                    patch_minor=patch_minor,
                    champion_id=participant.champion_id,
                    item_id=purchase.item_id,
                    round_number=purchase.round_number,
                    timestamp=purchase.timestamp,
                )
            )
        self._purchases.insert_many(item_records)

        for index, participant in enumerate(match.info.participants, start=1):
            self._participants.upsert(
                ParticipantStatsRecord(
                    match_id=match.match_id,
                    puuid=participant.puuid,
                    champion_id=participant.champion_id,
                    champion_name=participant.champion_name,
                    patch_minor=patch_minor,
                    placement=participant.placement,
                    subteam_placement=participant.subteam_placement,
                    team_id=participant.team_id,
                    partner_champion_id=partner_map.get(participant.puuid),
                    items=participant.items,
                    augments=participant.augments,
                    skill_order_str=skill_orders.get(index, ""),
                    skill_progression=build_skill_progression(level_ups, index),
                )
            )
            await self._enqueue_puuid(participant.puuid)

        self._new_matches += 1
        logger.info("Processed match %s (%s)", match.match_id, patch_minor)
