"""Tests for the repository layer and SQLite schema."""

from __future__ import annotations

from src.database.db import Database
from src.database.repositories import (
    ChampionMetaRecord,
    ChampionMetaRepository,
    CrawlQueueRepository,
    ItemPurchaseRecord,
    ItemPurchaseRepository,
    MatchRepository,
    ParticipantRepository,
    ParticipantStatsRecord,
)


def make_participant(match_id: str = "m1", puuid: str = "p1") -> ParticipantStatsRecord:
    return ParticipantStatsRecord(
        match_id=match_id,
        puuid=puuid,
        champion_id=266,
        champion_name="Aatrox",
        patch_minor="26.21",
        placement=1,
        subteam_placement=1,
        team_id=100,
        partner_champion_id=99,
        items=[1001, 0, 0, 0, 0, 0, 0],
        augments=[60001, 0, 0, 0],
        skill_order_str="Q > W > E",
    )


def test_match_registry(db: Database) -> None:
    matches = MatchRepository(db)
    matches.insert("NA1_1", "26.21.1.1", "26.21", 900)
    assert matches.exists("NA1_1")
    assert not matches.exists("NA1_2")
    assert matches.count() == 1


def test_participant_upsert(db: Database) -> None:
    participants = ParticipantRepository(db)
    participants.upsert(make_participant())
    rows = participants.for_champion(266, "26.21")
    assert len(rows) == 1
    assert rows[0]["skill_order_str"] == "Q > W > E"

    assert participants.distinct_champions("26.21")[0]["champion_name"] == "Aatrox"
    assert participants.distinct_patches() == ["26.21"]
    assert participants.champion_names("26.21") == {266: "Aatrox"}


def test_item_purchase_roundtrip(db: Database) -> None:
    purchases = ItemPurchaseRepository(db)
    purchases.insert_many(
        [
            ItemPurchaseRecord(
                match_id="m1",
                puuid="p1",
                patch_minor="26.21",
                champion_id=266,
                item_id=3111,
                round_number=1,
                timestamp=100,
            )
        ]
    )
    rows = purchases.for_champion(266, "26.21")
    assert len(rows) == 1
    assert rows[0]["item_id"] == 3111
    assert rows[0]["round_number"] == 1


def test_crawl_queue(db: Database) -> None:
    queue = CrawlQueueRepository(db)
    assert queue.enqueue("p1", 1700) is True
    assert queue.enqueue("p1", 1700) is False
    assert queue.enqueue("p1", 1710) is True
    assert queue.pending() == [{"puuid": "p1", "queue_id": 1700}, {"puuid": "p1", "queue_id": 1710}]
    queue.mark_crawled("p1", 1700)
    assert queue.is_crawled("p1", 1700)
    assert not queue.is_crawled("p1", 1710)


def test_champion_meta_roundtrip(db: Database) -> None:
    meta = ChampionMetaRepository(db)
    record = ChampionMetaRecord(
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
        build_style="AD",
        skill_order_distribution=[{"order": "Q > W > E", "count": 8, "pick_rate": 0.8}],
        skill_progression="QWQEWR",
        augments_overall=[{"augment_id": 60001, "count": 5, "pick_rate": 0.5}],
        boots=[{"item_id": 3111, "count": 8, "pick_rate": 0.8}],
        round_items={"1": [{"item_id": 1001, "count": 3}]},
        partner_synergies=[{"champion_id": 99, "games": 6, "win_rate": 0.66}],
    )
    meta.upsert(record)

    fetched = meta.get(266, "26.21", build_style="AD")
    assert fetched is not None
    assert fetched["tier_rank"] == "S"
    assert fetched["build_style"] == "AD"
    assert fetched["skill_progression"] == "QWQEWR"
    assert fetched["skill_order_distribution"][0]["order"] == "Q > W > E"
    assert fetched["augments_overall"][0]["augment_id"] == 60001
    assert fetched["boots"][0]["item_id"] == 3111
    assert fetched["round_items"]["1"][0]["item_id"] == 1001
    assert fetched["partner_synergies"][0]["champion_id"] == 99

    assert meta.list_patches() == ["26.21"]
    assert len(meta.list("26.21", build_style="AD")) == 1
    assert meta.list_champions("26.21") == [{"champion_id": 266, "champion_name": "Aatrox"}]
    styles = meta.list_styles(266, "26.21")
    assert len(styles) == 1
    assert styles[0]["build_style"] == "AD"
    assert styles[0]["total_games"] == 10
    assert "icon" in styles[0]
