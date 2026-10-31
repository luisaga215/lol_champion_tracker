"""Tests for the FastAPI HTTP layer."""

from __future__ import annotations

from fastapi.testclient import TestClient

from src.api.main import create_app
from src.config import Settings
from src.database.db import Database
from src.database.repositories import ChampionMetaRecord, ChampionMetaRepository


def seed_meta(db: Database) -> None:
    repo = ChampionMetaRepository(db)
    repo.upsert(
        ChampionMetaRecord(
            champion_id=266,
            patch_version="26.21",
            champion_name="Aatrox",
            total_games=10,
            win_count=5,
            top4_count=7,
            win_rate=0.5,
            top4_rate=0.7,
            avg_placement=2.3,
            tier_rank="S",
            skill_priority="Q > W > E",
            augments_overall=[{"augment_id": 60001, "count": 5, "pick_rate": 0.5}],
            boots=[{"item_id": 3111, "count": 8, "pick_rate": 0.8}],
        )
    )


def make_client(db: Database) -> TestClient:
    settings = Settings(
        riot_api_key="test-key",
        database_path=":memory:",
        reference_fetch_enabled=False,
    )
    app = create_app(settings=settings, db=db)
    return TestClient(app)


def test_health(db: Database) -> None:
    with make_client(db) as client:
        response = client.get("/health")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"
        assert body["riot_configured"] is True


def test_list_patches(db: Database) -> None:
    seed_meta(db)
    with make_client(db) as client:
        response = client.get("/api/arena/patches")
        assert response.status_code == 200
        assert response.json() == ["26.21"]


def test_list_meta(db: Database) -> None:
    seed_meta(db)
    with make_client(db) as client:
        response = client.get("/api/arena/meta")
        assert response.status_code == 200
        body = response.json()
        assert len(body) == 1
        assert body[0]["champion_id"] == 266
        assert body[0]["boots"][0]["item_id"] == 3111


def test_get_meta_latest(db: Database) -> None:
    seed_meta(db)
    with make_client(db) as client:
        response = client.get("/api/arena/meta/266")
        assert response.status_code == 200
        assert response.json()["tier_rank"] == "S"


def test_get_meta_specific_patch(db: Database) -> None:
    seed_meta(db)
    with make_client(db) as client:
        response = client.get("/api/arena/meta/266/patch/26.21")
        assert response.status_code == 200
        assert response.json()["champion_name"] == "Aatrox"


def test_get_meta_not_found(db: Database) -> None:
    with make_client(db) as client:
        response = client.get("/api/arena/meta/999")
        assert response.status_code == 404


def test_list_meta_tier_filter(db: Database) -> None:
    seed_meta(db)
    with make_client(db) as client:
        response = client.get("/api/arena/meta", params={"tier": "B"})
        assert response.status_code == 200
        assert response.json() == []


def test_seed_crawl(db: Database) -> None:
    with make_client(db) as client:
        response = client.post(
            "/api/arena/crawl/seed",
            json={"puuids": ["p1", "p2"]},
        )
        assert response.status_code == 200
        # 2 PUUIDs enqueued across the default two Arena queues.
        assert response.json() == {"queued": 4}
