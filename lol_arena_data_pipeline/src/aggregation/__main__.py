"""Command-line entry point to recompute champion Arena meta.

Usage::

    python -m src.aggregation [--patch 26.21]
"""

from __future__ import annotations

import argparse
import asyncio
import logging
from pathlib import Path

from src.aggregation.aggregator import Aggregator
from src.config import get_settings
from src.database.db import Database
from src.database.repositories import (
    ChampionMetaRepository,
    ItemPurchaseRepository,
    ParticipantRepository,
)
from src.reference.loader import load_reference_data

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")


async def run(patch: str | None) -> None:
    settings = get_settings()
    schema = Path(__file__).resolve().parent.parent / "database" / "schema.sql"
    db = Database(settings.database_path, schema_path=schema)

    reference = await load_reference_data(db)
    aggregator = Aggregator(
        ParticipantRepository(db),
        ItemPurchaseRepository(db),
        ChampionMetaRepository(db),
        reference,
    )

    try:
        if patch:
            count = aggregator.aggregate_patch(patch)
        else:
            count = aggregator.aggregate_all()
        logging.getLogger(__name__).info("Aggregated %d champions", count)
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Aggregate champion Arena meta")
    parser.add_argument("--patch", default=None, help="Restrict aggregation to a patch minor")
    args = parser.parse_args()
    asyncio.run(run(args.patch))


if __name__ == "__main__":
    main()
