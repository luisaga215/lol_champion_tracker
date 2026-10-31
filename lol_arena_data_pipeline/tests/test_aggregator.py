"""Tests for the champion meta aggregator."""

from __future__ import annotations

from src.aggregation.aggregator import (
    build_champion_meta,
    classify_rows,
    perf_tier_from_win_rate,
    tier_from_score,
    tier_score,
)
from src.reference.data import AugmentRef, ItemRef, ReferenceData


def make_reference() -> ReferenceData:
    items = {
        3111: ItemRef(id=3111, name="Mercury's Treads", categories=("Boots", "MagicResist")),
        3006: ItemRef(id=3006, name="Berserker's Greaves", categories=("Boots", "AttackSpeed")),
        2138: ItemRef(id=2138, name="Elixir of Iron", categories=("Consumable",)),
        1234: ItemRef(id=1234, name="Prismatic Sword", categories=("Damage",)),
        3031: ItemRef(id=3031, name="Infinity Edge", categories=("Damage",)),
        3089: ItemRef(id=3089, name="Rabadon's Deathcap", categories=("SpellDamage",)),
    }
    augments = {
        60001: AugmentRef(id=60001, name="Blood Brother", rarity=0),
        60002: AugmentRef(id=60002, name="Dual Wield", rarity=1),
        60003: AugmentRef(id=60003, name="Fan the Hammer", rarity=2),
    }
    return ReferenceData(
        items=items,
        augments=augments,
        boots=frozenset({3111, 3006}),
        elixirs=frozenset({2138}),
        prismatic=frozenset({1234}),
    )


def make_rows() -> list[dict]:
    return [
        {
            "match_id": "m1",
            "puuid": "p1",
            "champion_id": 266,
            "champion_name": "Aatrox",
            "patch_minor": "26.21",
            "placement": 1,
            "partner_champion_id": 99,
            "skill_order_str": "Q > W > E",
            "skill_progression": "QWQER",
            "item0": 3031,
            "item1": 3111,
            "item2": 0,
            "item3": 0,
            "item4": 0,
            "item5": 0,
            "item6": 0,
            "player_augment1": 60001,
            "player_augment2": 0,
            "player_augment3": 0,
            "player_augment4": 0,
        },
        {
            "match_id": "m2",
            "puuid": "p2",
            "champion_id": 266,
            "champion_name": "Aatrox",
            "patch_minor": "26.21",
            "placement": 3,
            "partner_champion_id": 99,
            "skill_order_str": "Q > W > E",
            "skill_progression": "QWQER",
            "item0": 3031,
            "item1": 3111,
            "item2": 0,
            "item3": 0,
            "item4": 0,
            "item5": 0,
            "item6": 0,
            "player_augment1": 60002,
            "player_augment2": 0,
            "player_augment3": 0,
            "player_augment4": 0,
        },
        {
            "match_id": "m3",
            "puuid": "p3",
            "champion_id": 266,
            "champion_name": "Aatrox",
            "patch_minor": "26.21",
            "placement": 8,
            "partner_champion_id": 100,
            "skill_order_str": "W > Q > E",
            "skill_progression": "WQER",
            "item0": 3089,
            "item1": 0,
            "item2": 0,
            "item3": 0,
            "item4": 0,
            "item5": 0,
            "item6": 0,
            "player_augment1": 60001,
            "player_augment2": 0,
            "player_augment3": 0,
            "player_augment4": 0,
        },
    ]


def make_purchases() -> list[dict]:
    return [
        {
            "match_id": "m1",
            "puuid": "p1",
            "champion_id": 266,
            "patch_minor": "26.21",
            "item_id": 3111,
            "round_number": 1,
            "timestamp": 100,
        },
        {
            "match_id": "m2",
            "puuid": "p2",
            "champion_id": 266,
            "patch_minor": "26.21",
            "item_id": 3111,
            "round_number": 1,
            "timestamp": 100,
        },
        {
            "match_id": "m1",
            "puuid": "p1",
            "champion_id": 266,
            "patch_minor": "26.21",
            "item_id": 2138,
            "round_number": 9,
            "timestamp": 200,
        },
    ]


def test_build_champion_meta_core_stats() -> None:
    record = build_champion_meta(266, "26.21", make_rows(), make_purchases(), make_reference())

    assert record.total_games == 3
    assert record.win_count == 1
    assert record.top4_count == 2
    assert record.win_rate == round(1 / 3, 4)
    assert record.top4_rate == round(2 / 3, 4)
    assert record.avg_placement == round(4.0, 4)
    assert record.champion_name == "Aatrox"
    assert record.skill_priority == "Q > W > E"
    assert record.build_style == "Recommended"
    assert record.skill_progression == "QWQER"


def test_build_champion_meta_tier_rank() -> None:
    record = build_champion_meta(266, "26.21", make_rows(), make_purchases(), make_reference())
    assert record.tier_rank == "S"


def test_build_champion_meta_items_with_names() -> None:
    record = build_champion_meta(266, "26.21", make_rows(), make_purchases(), make_reference())
    assert record.boots[0]["item_id"] == 3111
    assert record.boots[0]["name"] == "Mercury's Treads"
    assert record.boots[0]["count"] == 2
    assert record.elixirs[0]["item_id"] == 2138
    assert record.round_items["1"][0]["item_id"] == 3111
    assert record.round_items["9"][0]["item_id"] == 2138


def test_build_champion_meta_augments_by_tier() -> None:
    record = build_champion_meta(266, "26.21", make_rows(), make_purchases(), make_reference())
    silver_ids = {entry["augment_id"] for entry in record.augments_silver}
    gold_ids = {entry["augment_id"] for entry in record.augments_gold}
    assert silver_ids == {60001}
    assert gold_ids == {60002}
    by_id = {entry["augment_id"]: entry for entry in record.augments_overall}
    assert by_id[60001]["name"] == "Blood Brother"
    assert by_id[60001]["tier"] == "silver"
    assert by_id[60001]["performance_tier"] == "A"


def test_build_champion_meta_skill_distribution() -> None:
    record = build_champion_meta(266, "26.21", make_rows(), make_purchases(), make_reference())
    dist = {entry["order"]: entry for entry in record.skill_order_distribution}
    assert dist["Q > W > E"]["count"] == 2
    assert dist["Q > W > E"]["pick_rate"] == round(2 / 3, 4)


def test_classify_rows() -> None:
    reference = make_reference()
    rows = make_rows()
    style_by_game = classify_rows(rows, reference)
    assert style_by_game[("m1", "p1")] == "AD"
    assert style_by_game[("m2", "p2")] == "AD"
    assert style_by_game[("m3", "p3")] == "AP"


def test_classify_empty() -> None:
    reference = make_reference()
    assert reference.classify([]) == "Recommended"
    assert reference.classify([0, 0, 0]) == "Recommended"


def test_perf_tier_and_tier_bounds() -> None:
    assert perf_tier_from_win_rate(0.62) == "S+"
    assert perf_tier_from_win_rate(0.56) == "S"
    assert perf_tier_from_win_rate(0.51) == "A"
    assert perf_tier_from_win_rate(0.46) == "B"
    assert perf_tier_from_win_rate(0.40) == "C"
    assert tier_from_score(0.70) == "S+"
    assert tier_from_score(0.10) == "C"
    assert tier_score(1.0, 1.0, 1.0) == 1.0
