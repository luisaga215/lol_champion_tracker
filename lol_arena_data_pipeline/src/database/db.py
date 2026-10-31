"""SQLite database access layer for the Arena data pipeline."""

from __future__ import annotations

__all__ = ["Database"]

import sqlite3
import threading
from pathlib import Path
from typing import Any, Iterable, Sequence


class Database:
    """A small, thread-safe wrapper around the standard-library ``sqlite3``.

    A single connection guarded by a re-entrant lock is shared across threads
    (the crawler event loop and the FastAPI worker threads). Write-ahead logging
    is enabled for reliability, and foreign-key enforcement is turned on.
    """

    def __init__(self, path: str | Path, schema_path: str | Path | None = None) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.RLock()
        with self._lock:
            self._conn.execute("PRAGMA journal_mode=WAL;")
            self._conn.execute("PRAGMA foreign_keys=ON;")
        if schema_path is not None:
            self.apply_schema(schema_path)

    def apply_schema(self, schema_path: str | Path) -> None:
        """Execute a SQL schema script (idempotent ``CREATE ... IF NOT EXISTS``)."""
        script = Path(schema_path).read_text(encoding="utf-8")
        with self._lock:
            self._migrate()
            self._conn.executescript(script)
            self._conn.commit()

    def _migrate(self) -> None:
        """Reconcile pre-existing tables with the current schema."""
        meta_cols = {
            row["name"]
            for row in self._conn.execute("PRAGMA table_info(champion_arena_meta)").fetchall()
        }
        required_meta_cols = {"build_style", "skill_progression", "skill_order_distribution_json"}
        if meta_cols and not required_meta_cols.issubset(meta_cols):
            self._conn.execute("DROP TABLE champion_arena_meta")

        participant_cols = {
            row["name"]
            for row in self._conn.execute("PRAGMA table_info(arena_participant_stats)").fetchall()
        }
        if participant_cols and "skill_progression" not in participant_cols:
            self._conn.execute(
                "ALTER TABLE arena_participant_stats ADD COLUMN skill_progression TEXT"
            )

        ref_cols = {
            row["name"]
            for row in self._conn.execute("PRAGMA table_info(reference_items)").fetchall()
        }
        if ref_cols and "price" not in ref_cols:
            self._conn.execute("ALTER TABLE reference_items ADD COLUMN price INTEGER")

    def execute(self, sql: str, params: Sequence[Any] = ()) -> int:
        """Execute a single statement and return the lastrowid/rowcount."""
        with self._lock:
            cursor = self._conn.execute(sql, params)
            self._conn.commit()
            return cursor.lastrowid if cursor.lastrowid is not None else cursor.rowcount

    def insert(self, sql: str, params: Sequence[Any] = ()) -> int:
        """Execute an INSERT and return the number of rows actually inserted.

        Unlike :meth:`execute`, this always reports ``rowcount`` so ``INSERT OR
        IGNORE`` no-ops (which leave ``lastrowid`` unchanged) are detected
        correctly.
        """
        with self._lock:
            cursor = self._conn.execute(sql, params)
            self._conn.commit()
            return cursor.rowcount

    def executemany(self, sql: str, params: Iterable[Sequence[Any]]) -> int:
        """Execute a statement for each parameter sequence in a single commit."""
        with self._lock:
            cursor = self._conn.executemany(sql, list(params))
            self._conn.commit()
            return cursor.rowcount

    def fetch_one(self, sql: str, params: Sequence[Any] = ()) -> dict[str, Any] | None:
        """Fetch a single row as a dict, or ``None``."""
        with self._lock:
            row = self._conn.execute(sql, params).fetchone()
        return dict(row) if row is not None else None

    def fetch_all(self, sql: str, params: Sequence[Any] = ()) -> list[dict[str, Any]]:
        """Fetch all rows as a list of dicts."""
        with self._lock:
            rows = self._conn.execute(sql, params).fetchall()
        return [dict(row) for row in rows]

    def close(self) -> None:
        """Close the underlying connection."""
        with self._lock:
            self._conn.close()
