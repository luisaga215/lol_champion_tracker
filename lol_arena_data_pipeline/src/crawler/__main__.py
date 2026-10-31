"""Command-line entry point for the Arena match crawler.

Usage::

    python -m src.crawler --seed <PUUID> [--seed <PUUID> ...] [--patch 26.21]

Requires ``RIOT_API_KEY`` (or a local ``.env``). Seeds default to any pending
PUUIDs already present in the ``crawl_queue`` table.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
from pathlib import Path

from src.config import get_settings
from src.crawler.worker import Crawler
from src.database.db import Database
from src.database.repositories import (
    CrawlQueueRepository,
    ItemPurchaseRepository,
    MatchRepository,
    ParticipantRepository,
)
from src.riot.client import RiotClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Arena match crawler")
    parser.add_argument("--seed", action="append", default=[], help="Seed PUUID (repeatable)")
    parser.add_argument("--patch", default=None, help="Only process matches from this patch minor")
    parser.add_argument(
        "--max-matches",
        type=int,
        default=None,
        help="Stop after processing this many new matches (bounded runs)",
    )
    return parser.parse_args()


async def run(seeds: list[str], target_patch: str | None, max_matches: int | None) -> None:
    settings = get_settings()
    schema = Path(__file__).resolve().parent.parent / "database" / "schema.sql"
    db = Database(settings.database_path, schema_path=schema)

    matches = MatchRepository(db)
    participants = ParticipantRepository(db)
    purchases = ItemPurchaseRepository(db)
    queue_repo = CrawlQueueRepository(db)

    if not settings.configured and not seeds:
        db.close()
        raise SystemExit("No Riot API key configured and no seed PUUIDs provided.")

    client = RiotClient(
        settings.riot_api_key, settings.riot_base_url, timeout=settings.request_timeout
    )
    crawler = Crawler(
        client,
        matches,
        participants,
        purchases,
        queue_repo,
        settings,
        target_patch_minor=target_patch,
        max_matches=max_matches,
    )
    try:
        processed = await crawler.crawl(seeds)
        logging.getLogger(__name__).info("Crawl finished; %d new matches processed", processed)
    finally:
        await client.close()
        db.close()


def main() -> None:
    args = parse_args()
    asyncio.run(run(args.seed, args.patch, args.max_matches))


if __name__ == "__main__":
    main()
