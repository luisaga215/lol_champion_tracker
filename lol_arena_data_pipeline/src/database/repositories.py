"""Repository layer implementing the repository pattern over SQLite.

Each repository owns a single aggregate/table and exposes a narrow, typed API so
the crawler, aggregator, and HTTP layer never touch raw SQL.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Sequence

from src.database.db import Database

__all__ = [
    "ParticipantStatsRecord",
    "ItemPurchaseRecord",
    "ChampionMetaRecord",
    "MatchRepository",
    "ParticipantRepository",
    "ItemPurchaseRepository",
    "ChampionMetaRepository",
    "CrawlQueueRepository",
]


def _patch_sort_key(version: str) -> tuple[int, ...]:
    """Numeric sort key so ``26.9`` sorts before ``26.21``."""
    try:
        return tuple(int(part) for part in version.split("."))
    except ValueError:
        return ()


@dataclass(frozen=True)
class ParticipantStatsRecord:
    """A single participant's aggregated per-match Arena stats."""

    match_id: str
    puuid: str
    champion_id: int
    champion_name: str
    patch_minor: str
    placement: int
    subteam_placement: int | None
    team_id: int | None
    partner_champion_id: int | None
    items: Sequence[int]
    augments: Sequence[int]
    skill_order_str: str
    skill_progression: str | None = None


@dataclass(frozen=True)
class ItemPurchaseRecord:
    """A timeline-derived item purchase mapped to an Arena shop round."""

    match_id: str
    puuid: str
    patch_minor: str
    champion_id: int
    item_id: int
    round_number: int | None
    timestamp: int


@dataclass(frozen=True)
class ChampionMetaRecord:
    """Aggregated champion meta for a single patch and build style."""

    champion_id: int
    patch_version: str
    champion_name: str
    total_games: int
    win_count: int
    top4_count: int
    win_rate: float
    top4_rate: float
    avg_placement: float
    tier_rank: str
    skill_priority: str
    build_style: str = "Recommended"
    skill_order_distribution: list[dict[str, Any]] = field(default_factory=list)
    skill_progression: str | None = None
    augments_overall: list[dict[str, Any]] = field(default_factory=list)
    augments_silver: list[dict[str, Any]] = field(default_factory=list)
    augments_gold: list[dict[str, Any]] = field(default_factory=list)
    augments_prismatic: list[dict[str, Any]] = field(default_factory=list)
    boots: list[dict[str, Any]] = field(default_factory=list)
    prismatic_items: list[dict[str, Any]] = field(default_factory=list)
    full_build: list[dict[str, Any]] = field(default_factory=list)
    round_items: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    elixirs: list[dict[str, Any]] = field(default_factory=list)
    build_styles: list[dict[str, Any]] = field(default_factory=list)
    partner_synergies: list[dict[str, Any]] = field(default_factory=list)


class MatchRepository:
    """Persistence for the ``raw_matches`` registry."""

    def __init__(self, db: Database) -> None:
        self._db = db

    def exists(self, match_id: str) -> bool:
        row = self._db.fetch_one("SELECT 1 FROM raw_matches WHERE match_id = ?", (match_id,))
        return row is not None

    def insert(
        self,
        match_id: str,
        game_version: str,
        patch_minor: str,
        game_duration: int | None,
    ) -> None:
        self._db.execute(
            "INSERT OR IGNORE INTO raw_matches (match_id, game_version, patch_minor, game_duration) "
            "VALUES (?, ?, ?, ?)",
            (match_id, game_version, patch_minor, game_duration),
        )

    def count(self) -> int:
        row = self._db.fetch_one("SELECT COUNT(*) AS n FROM raw_matches")
        return int(row["n"]) if row else 0


class ParticipantRepository:
    """Persistence for ``arena_participant_stats``."""

    _COLS = (
        "match_id",
        "puuid",
        "champion_id",
        "champion_name",
        "patch_minor",
        "placement",
        "subteam_placement",
        "team_id",
        "partner_champion_id",
        "item0",
        "item1",
        "item2",
        "item3",
        "item4",
        "item5",
        "item6",
        "player_augment1",
        "player_augment2",
        "player_augment3",
        "player_augment4",
        "skill_order_str",
        "skill_progression",
    )

    def __init__(self, db: Database) -> None:
        self._db = db

    def upsert(self, record: ParticipantStatsRecord) -> None:
        items = list(record.items)
        while len(items) < 7:
            items.append(0)
        augments = list(record.augments)
        while len(augments) < 4:
            augments.append(0)
        values = (
            record.match_id,
            record.puuid,
            record.champion_id,
            record.champion_name,
            record.patch_minor,
            record.placement,
            record.subteam_placement,
            record.team_id,
            record.partner_champion_id,
            *items[:7],
            *augments[:4],
            record.skill_order_str,
            record.skill_progression,
        )
        placeholders = ", ".join("?" for _ in self._COLS)
        self._db.execute(
            f"INSERT OR REPLACE INTO arena_participant_stats ({', '.join(self._COLS)}) "
            f"VALUES ({placeholders})",
            values,
        )

    def for_champion(self, champion_id: int, patch_minor: str) -> list[dict[str, Any]]:
        return self._db.fetch_all(
            "SELECT * FROM arena_participant_stats WHERE champion_id = ? AND patch_minor = ?",
            (champion_id, patch_minor),
        )

    def distinct_champions(self, patch_minor: str) -> list[dict[str, Any]]:
        return self._db.fetch_all(
            "SELECT champion_id, MAX(champion_name) AS champion_name "
            "FROM arena_participant_stats WHERE patch_minor = ? "
            "GROUP BY champion_id ORDER BY champion_id",
            (patch_minor,),
        )

    def distinct_patches(self) -> list[str]:
        rows = self._db.fetch_all("SELECT DISTINCT patch_minor FROM arena_participant_stats")
        return sorted(
            (row["patch_minor"] for row in rows),
            key=_patch_sort_key,
            reverse=True,
        )

    def champion_names(self, patch_minor: str | None = None) -> dict[int, str]:
        if patch_minor is not None:
            rows = self._db.fetch_all(
                "SELECT champion_id, MAX(champion_name) AS champion_name "
                "FROM arena_participant_stats WHERE patch_minor = ? "
                "GROUP BY champion_id",
                (patch_minor,),
            )
        else:
            rows = self._db.fetch_all(
                "SELECT champion_id, MAX(champion_name) AS champion_name "
                "FROM arena_participant_stats GROUP BY champion_id"
            )
        return {int(row["champion_id"]): row["champion_name"] for row in rows}


class ItemPurchaseRepository:
    """Persistence for ``arena_item_purchases``."""

    def __init__(self, db: Database) -> None:
        self._db = db

    def insert_many(self, records: Sequence[ItemPurchaseRecord]) -> None:
        if not records:
            return
        rows = [
            (
                r.match_id,
                r.puuid,
                r.patch_minor,
                r.champion_id,
                r.item_id,
                r.round_number,
                r.timestamp,
            )
            for r in records
        ]
        self._db.executemany(
            "INSERT OR IGNORE INTO arena_item_purchases "
            "(match_id, puuid, patch_minor, champion_id, item_id, round_number, timestamp) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            rows,
        )

    def for_champion(self, champion_id: int, patch_minor: str) -> list[dict[str, Any]]:
        return self._db.fetch_all(
            "SELECT * FROM arena_item_purchases WHERE champion_id = ? AND patch_minor = ?",
            (champion_id, patch_minor),
        )


class ChampionMetaRepository:
    """Persistence for ``champion_arena_meta`` (JSON columns are auto-serialized)."""

    _JSON_COLS = (
        "skill_order_distribution_json",
        "augments_overall_json",
        "augments_silver_json",
        "augments_gold_json",
        "augments_prismatic_json",
        "boots_json",
        "prismatic_items_json",
        "full_build_json",
        "round_items_json",
        "elixirs_json",
        "build_styles_json",
        "partner_synergies_json",
    )

    def __init__(self, db: Database) -> None:
        self._db = db

    def upsert(self, record: ChampionMetaRecord) -> None:
        j = lambda value: json.dumps(value, separators=(",", ":"))  # noqa: E731
        self._db.execute(
            """
            INSERT OR REPLACE INTO champion_arena_meta (
                champion_id, patch_version, build_style, champion_name, total_games,
                win_count, top4_count, win_rate, top4_rate, avg_placement, tier_rank,
                skill_priority, skill_order_distribution_json, skill_progression,
                augments_overall_json, augments_silver_json, augments_gold_json,
                augments_prismatic_json, boots_json, prismatic_items_json, full_build_json,
                round_items_json, elixirs_json, build_styles_json, partner_synergies_json,
                updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (
                record.champion_id,
                record.patch_version,
                record.build_style,
                record.champion_name,
                record.total_games,
                record.win_count,
                record.top4_count,
                record.win_rate,
                record.top4_rate,
                record.avg_placement,
                record.tier_rank,
                record.skill_priority,
                j(record.skill_order_distribution),
                record.skill_progression,
                j(record.augments_overall),
                j(record.augments_silver),
                j(record.augments_gold),
                j(record.augments_prismatic),
                j(record.boots),
                j(record.prismatic_items),
                j(record.full_build),
                j(record.round_items),
                j(record.elixirs),
                j(record.build_styles),
                j(record.partner_synergies),
            ),
        )

    def get(
        self, champion_id: int, patch_version: str, build_style: str = "Recommended"
    ) -> dict[str, Any] | None:
        row = self._db.fetch_one(
            "SELECT * FROM champion_arena_meta "
            "WHERE champion_id = ? AND patch_version = ? AND build_style = ?",
            (champion_id, patch_version, build_style),
        )
        return self._parse_row(row) if row else None

    def list(
        self, patch_version: str | None = None, build_style: str = "Recommended"
    ) -> list[dict[str, Any]]:
        if patch_version is not None:
            rows = self._db.fetch_all(
                "SELECT * FROM champion_arena_meta "
                "WHERE patch_version = ? AND build_style = ? "
                "ORDER BY tier_rank, win_rate DESC",
                (patch_version, build_style),
            )
        else:
            rows = self._db.fetch_all(
                "SELECT * FROM champion_arena_meta WHERE build_style = ? "
                "ORDER BY patch_version, champion_id",
                (build_style,),
            )
        return [self._parse_row(row) for row in rows]

    def list_styles(self, champion_id: int, patch_version: str) -> list[dict[str, Any]]:
        """Return available build styles with game counts + a representative icon.

        The icon references the champion's actual items for that style (preferring
        prismatic items, then boots, then round-1 items).
        """
        rows = self._db.fetch_all(
            "SELECT build_style, total_games, prismatic_items_json, boots_json, "
            "round_items_json FROM champion_arena_meta "
            "WHERE champion_id = ? AND patch_version = ? ORDER BY total_games DESC",
            (champion_id, patch_version),
        )
        return [
            {
                "build_style": row["build_style"],
                "total_games": row["total_games"],
                "icon": self._style_icon(row),
            }
            for row in rows
        ]

    @staticmethod
    def _style_icon(row: dict[str, Any]) -> str:
        """Pick a representative icon for a style: prismatic > boots > round-1."""
        for column in ("prismatic_items_json", "boots_json"):
            try:
                items = json.loads(row.get(column) or "[]")
            except (TypeError, ValueError):
                items = []
            if isinstance(items, list):
                for item in items:
                    if isinstance(item, dict) and item.get("icon"):
                        return item["icon"]
        try:
            rounds = json.loads(row.get("round_items_json") or "{}")
        except (TypeError, ValueError):
            rounds = {}
        if isinstance(rounds, dict):
            for round_key in sorted(rounds, key=lambda value: int(value)):
                for item in rounds[round_key]:
                    if item.get("icon"):
                        return item["icon"]
        return ""

    def list_patches(self) -> list[str]:
        rows = self._db.fetch_all("SELECT DISTINCT patch_version FROM champion_arena_meta")
        return sorted(
            (row["patch_version"] for row in rows),
            key=_patch_sort_key,
            reverse=True,
        )

    def list_champions(self, patch_version: str | None = None) -> list[dict[str, Any]]:
        if patch_version is not None:
            rows = self._db.fetch_all(
                "SELECT DISTINCT champion_id, champion_name FROM champion_arena_meta "
                "WHERE patch_version = ? ORDER BY champion_name",
                (patch_version,),
            )
        else:
            rows = self._db.fetch_all(
                "SELECT champion_id, MAX(champion_name) AS champion_name "
                "FROM champion_arena_meta GROUP BY champion_id ORDER BY champion_name"
            )
        return rows

    @classmethod
    def _parse_row(cls, row: dict[str, Any]) -> dict[str, Any]:
        parsed = dict(row)
        for column in cls._JSON_COLS:
            parsed[column.removesuffix("_json")] = cls._loads(parsed.pop(column, None))
        return parsed

    @staticmethod
    def _loads(value: Any) -> Any:
        if value is None or value == "":
            return None
        try:
            return json.loads(value)
        except (TypeError, ValueError):
            return value


class CrawlQueueRepository:
    """Persistence for the PUUID crawl frontier (``crawl_queue``)."""

    def __init__(self, db: Database) -> None:
        self._db = db

    def enqueue(self, puuid: str, queue_id: int) -> bool:
        """Add a PUUID/queue to the frontier; return True if newly added."""
        result = self._db.insert(
            "INSERT OR IGNORE INTO crawl_queue (puuid, queue_id, status) VALUES (?, ?, 'pending')",
            (puuid, queue_id),
        )
        return result > 0

    def mark_crawled(self, puuid: str, queue_id: int) -> None:
        self._db.execute(
            "UPDATE crawl_queue SET status = 'done', last_crawled_at = CURRENT_TIMESTAMP "
            "WHERE puuid = ? AND queue_id = ?",
            (puuid, queue_id),
        )

    def pending(self, limit: int = 100) -> list[dict[str, Any]]:
        return self._db.fetch_all(
            "SELECT puuid, queue_id FROM crawl_queue WHERE status = 'pending' LIMIT ?",
            (limit,),
        )

    def is_crawled(self, puuid: str, queue_id: int) -> bool:
        row = self._db.fetch_one(
            "SELECT status FROM crawl_queue WHERE puuid = ? AND queue_id = ?",
            (puuid, queue_id),
        )
        return row is not None and row["status"] == "done"
