"""Pytest configuration and shared fixtures."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Ensure the package root is importable regardless of the pytest invocation dir.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import Settings  # noqa: E402
from src.database.db import Database  # noqa: E402

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "src" / "database" / "schema.sql"


@pytest.fixture
def db(tmp_path: Path) -> Database:
    """An empty, schema-initialized SQLite database."""
    database = Database(tmp_path / "test.db", schema_path=SCHEMA_PATH)
    yield database
    database.close()


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    """Settings pointing at an isolated database file."""
    return Settings(
        riot_api_key="test-key",
        database_path=str(tmp_path / "pipeline.db"),
    )
