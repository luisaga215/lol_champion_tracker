"""Tests for the Arena timeline parser."""

from __future__ import annotations

from src.crawler.timeline import (
    ItemPurchase,
    assign_rounds_to_purchases,
    build_skill_orders,
    build_skill_progression,
    cluster_timestamps,
    extract_item_purchases,
    extract_skill_level_ups,
    reconstruct_skill_priority,
    round_for_phase,
)
from src.crawler.worker import extract_patch_minor
from src.riot.models import Timeline, TimelineEvent, TimelineFrame, TimelineInfo


def make_timeline() -> Timeline:
    return Timeline(
        info=TimelineInfo(
            frames=[
                TimelineFrame(
                    timestamp=0,
                    events=[
                        TimelineEvent(
                            type="ITEM_PURCHASED", timestamp=500, participantId=1, itemId=1001
                        ),
                        TimelineEvent(
                            type="SKILL_LEVEL_UP", timestamp=600, participantId=1, skillSlot=1
                        ),
                    ],
                ),
                TimelineFrame(
                    timestamp=1000,
                    events=[
                        TimelineEvent(
                            type="ITEM_PURCHASED", timestamp=1500, participantId=2, itemId=3111
                        ),
                    ],
                ),
            ]
        )
    )


def test_round_for_phase() -> None:
    assert round_for_phase(0) == 1
    assert round_for_phase(1) == 2
    assert round_for_phase(2) == 4
    assert round_for_phase(3) == 6
    assert round_for_phase(4) == 9
    assert round_for_phase(5) == 11
    assert round_for_phase(6) is None


def test_cluster_timestamps() -> None:
    # Two shop phases separated by a ~90s combat round.
    timestamps = [1000, 1500, 2000, 95_000, 96_000, 97_500]
    clusters = cluster_timestamps(timestamps, gap_threshold=30_000)
    assert clusters == [[1000, 1500, 2000], [95_000, 96_000, 97_500]]


def test_cluster_timestamps_empty() -> None:
    assert cluster_timestamps([]) == []


def test_assign_rounds_to_purchases() -> None:
    purchases = [
        ItemPurchase(participant_id=1, item_id=1001, timestamp=1000),
        ItemPurchase(participant_id=2, item_id=3111, timestamp=1500),
        ItemPurchase(participant_id=1, item_id=2000, timestamp=95_000),
    ]
    assigned = assign_rounds_to_purchases(purchases, gap_threshold=30_000)
    assert [purchase.round_number for purchase in assigned] == [1, 1, 2]


def test_extract_item_purchases() -> None:
    purchases = extract_item_purchases(make_timeline())
    assert len(purchases) == 2
    assert purchases[0].item_id == 1001
    assert purchases[0].participant_id == 1


def test_reconstruct_skill_priority() -> None:
    level_ups = extract_skill_level_ups(make_timeline())
    assert reconstruct_skill_priority(level_ups, participant_id=1) == "Q"


def test_reconstruct_skill_priority_orders_by_count_and_first_seen() -> None:
    level_ups = [
        TimelineEvent(type="SKILL_LEVEL_UP", timestamp=0, participantId=1, skillSlot=3),  # E
        TimelineEvent(type="SKILL_LEVEL_UP", timestamp=1, participantId=1, skillSlot=1),  # Q
        TimelineEvent(type="SKILL_LEVEL_UP", timestamp=2, participantId=1, skillSlot=2),  # W
        TimelineEvent(type="SKILL_LEVEL_UP", timestamp=3, participantId=1, skillSlot=1),  # Q
        TimelineEvent(type="SKILL_LEVEL_UP", timestamp=4, participantId=1, skillSlot=2),  # W
    ]
    orders = build_skill_orders(level_ups)
    assert orders[1] == "Q > W > E"


def test_build_skill_orders_multiple_participants() -> None:
    level_ups = [
        TimelineEvent(type="SKILL_LEVEL_UP", timestamp=0, participantId=1, skillSlot=1),
        TimelineEvent(type="SKILL_LEVEL_UP", timestamp=1, participantId=2, skillSlot=2),
    ]
    orders = build_skill_orders(level_ups)
    assert orders == {1: "Q", 2: "W"}


def test_build_skill_progression() -> None:
    level_ups = [
        TimelineEvent(type="SKILL_LEVEL_UP", timestamp=0, participantId=1, skillSlot=1),  # Q
        TimelineEvent(type="SKILL_LEVEL_UP", timestamp=1, participantId=1, skillSlot=2),  # W
        TimelineEvent(type="SKILL_LEVEL_UP", timestamp=2, participantId=1, skillSlot=4),  # R
        TimelineEvent(type="SKILL_LEVEL_UP", timestamp=3, participantId=1, skillSlot=1),  # Q
    ]
    progression = build_skill_progression(level_ups, participant_id=1)
    assert progression == "QWRQ"


def test_extract_patch_minor() -> None:
    assert extract_patch_minor("26.21.1234.5678") == "26.21"
    assert extract_patch_minor("26.21") == "26.21"
