"""Background orchestration of the Arena pipeline (crawl -> aggregate loop)."""

from __future__ import annotations

import asyncio
import logging

from src.aggregation.aggregator import Aggregator
from src.config import Settings
from src.crawler.worker import Crawler
from src.database.db import Database
from src.database.repositories import (
    ChampionMetaRepository,
    CrawlQueueRepository,
    ItemPurchaseRepository,
    MatchRepository,
    ParticipantRepository,
)
from src.reference.data import ReferenceData
from src.riot.client import RiotClient

logger = logging.getLogger(__name__)

__all__ = ["PipelineService"]


class PipelineService:
    """Runs recurring crawl + aggregation cycles against a shared database."""

    def __init__(self, settings: Settings, db: Database) -> None:
        self._settings = settings
        self._db = db
        self._matches = MatchRepository(db)
        self._participants = ParticipantRepository(db)
        self._purchases = ItemPurchaseRepository(db)
        self._queue = CrawlQueueRepository(db)
        self._meta = ChampionMetaRepository(db)
        self.reference = ReferenceData()

    async def crawl_and_aggregate(self) -> int:
        """Perform a single crawl pass followed by aggregation.

        Returns the number of new matches processed (0 when there is no work).
        """
        if not self._settings.configured:
            logger.warning("Riot API key not configured; skipping crawl cycle")
            return 0

        if not self._settings.crawler_seed_puuids and not self._queue.pending(limit=1):
            return 0

        new_matches = 0
        async with RiotClient(
            self._settings.riot_api_key,
            self._settings.riot_base_url,
            timeout=self._settings.request_timeout,
        ) as client:
            crawler = Crawler(
                client,
                self._matches,
                self._participants,
                self._purchases,
                self._queue,
                self._settings,
                max_matches=self._settings.crawler_cycle_max_matches,
            )
            new_matches = await crawler.crawl(self._settings.crawler_seed_puuids)

        if new_matches:
            aggregator = Aggregator(self._participants, self._purchases, self._meta, self.reference)
            champions = aggregator.aggregate_all()
            logger.info("Aggregated %d champions after %d new matches", champions, new_matches)
        return new_matches

    async def run_forever(self) -> None:
        """Run crawl+aggregate cycles forever (until cancelled)."""
        while True:
            try:
                await self.crawl_and_aggregate()
            except Exception:
                logger.exception("Pipeline cycle failed")
            await asyncio.sleep(self._settings.crawler_interval_seconds)
