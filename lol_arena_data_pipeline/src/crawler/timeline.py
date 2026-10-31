"""Parsing utilities for Arena match timelines.

Extracts item purchases and skill level-ups from the Riot match-v5 timeline and
maps them to Arena shop rounds (Round 1, 2, 4, 6, 9) and skill-max priority
strings (``Q > W > E``) respectively.

Riot Arena timelines do not expose explicit round-start events, so shop rounds
are recovered by clustering ``ITEM_PURCHASED`` timestamps: purchases in a shop
phase occur close together, while consecutive shop phases are separated by one
or more combat rounds (tens of seconds). The first five phases map to the
tracked shop rounds ``1, 2, 4, 6, 9``.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, replace
from typing import Sequence

from src.riot.models import Timeline

__all__ = [
    "SHOP_ROUNDS",
    "SHOP_GAP_THRESHOLD_MS",
    "ItemPurchase",
    "SkillLevelUp",
    "extract_item_purchases",
    "extract_skill_level_ups",
    "round_for_phase",
    "cluster_timestamps",
    "assign_rounds_to_purchases",
    "build_skill_orders",
    "build_skill_progression",
    "reconstruct_skill_priority",
]

#: Arena shop rounds tracked by the pipeline (initial buy = Round 1).
SHOP_ROUNDS: tuple[int, ...] = (1, 2, 4, 6, 9, 11)

#: Minimum gap (ms) that separates two consecutive shop phases.
SHOP_GAP_THRESHOLD_MS = 30_000

#: Timeline ``skillSlot`` -> ability letter.
SKILL_SLOTS: dict[int, str] = {1: "Q", 2: "W", 3: "E", 4: "R"}


@dataclass(frozen=True)
class ItemPurchase:
    """An item purchase event extracted from a timeline."""

    participant_id: int
    item_id: int
    timestamp: int
    round_number: int | None = None


@dataclass(frozen=True)
class SkillLevelUp:
    """A skill level-up event extracted from a timeline."""

    participant_id: int
    skill_slot: int
    timestamp: int


def extract_item_purchases(timeline: Timeline) -> list[ItemPurchase]:
    """Return all ``ITEM_PURCHASED`` events in chronological order."""
    purchases: list[ItemPurchase] = []
    for event in timeline.iter_events():
        if (
            event.type == "ITEM_PURCHASED"
            and event.item_id is not None
            and event.participant_id is not None
        ):
            purchases.append(
                ItemPurchase(
                    participant_id=event.participant_id,
                    item_id=event.item_id,
                    timestamp=event.timestamp,
                )
            )
    return purchases


def extract_skill_level_ups(timeline: Timeline) -> list[SkillLevelUp]:
    """Return all ``SKILL_LEVEL_UP`` events in chronological order."""
    level_ups: list[SkillLevelUp] = []
    for event in timeline.iter_events():
        if (
            event.type == "SKILL_LEVEL_UP"
            and event.skill_slot is not None
            and event.participant_id is not None
        ):
            level_ups.append(
                SkillLevelUp(
                    participant_id=event.participant_id,
                    skill_slot=event.skill_slot,
                    timestamp=event.timestamp,
                )
            )
    return level_ups


def round_for_phase(phase_index: int) -> int | None:
    """Map a zero-based shop-phase ordinal to a tracked round number.

    The first five shop phases correspond to rounds ``1, 2, 4, 6, 9``; later
    phases (12, 15, ...) are outside the tracked window and return ``None``.
    """
    if 0 <= phase_index < len(SHOP_ROUNDS):
        return SHOP_ROUNDS[phase_index]
    return None


def cluster_timestamps(
    timestamps: Sequence[int],
    gap_threshold: int = SHOP_GAP_THRESHOLD_MS,
) -> list[list[int]]:
    """Cluster a sorted sequence of timestamps into shop phases by gap."""
    if not timestamps:
        return []
    ordered = sorted(timestamps)
    clusters: list[list[int]] = [[ordered[0]]]
    for timestamp in ordered[1:]:
        if timestamp - clusters[-1][-1] > gap_threshold:
            clusters.append([timestamp])
        else:
            clusters[-1].append(timestamp)
    return clusters


def assign_rounds_to_purchases(
    purchases: Sequence[ItemPurchase],
    gap_threshold: int = SHOP_GAP_THRESHOLD_MS,
) -> list[ItemPurchase]:
    """Assign a shop round to each purchase (by clustering purchase timestamps)."""
    ordered = sorted(purchases, key=lambda purchase: purchase.timestamp)
    result: list[ItemPurchase] = []
    phase_index = -1
    previous: int | None = None
    for purchase in ordered:
        if previous is None or purchase.timestamp - previous > gap_threshold:
            phase_index += 1
        result.append(replace(purchase, round_number=round_for_phase(phase_index)))
        previous = purchase.timestamp
    return result


def reconstruct_skill_priority(level_ups: Sequence[SkillLevelUp], participant_id: int) -> str:
    """Reconstruct a participant's skill-max priority (``Q > W > E``).

    Skills are ordered by number of level-ups (descending) with ties broken by
    the earliest first level-up. The ultimate (``R``) is ignored.
    """
    counts: Counter[str] = Counter()
    first_at: dict[str, int] = {}
    for level_up in sorted(level_ups, key=lambda event: event.timestamp):
        if level_up.participant_id != participant_id:
            continue
        letter = SKILL_SLOTS.get(level_up.skill_slot)
        if letter is None or letter == "R":
            continue
        counts[letter] += 1
        first_at.setdefault(letter, level_up.timestamp)

    ordered = sorted(counts, key=lambda letter: (-counts[letter], first_at[letter]))
    return " > ".join(ordered)


def build_skill_orders(
    level_ups: Sequence[SkillLevelUp],
) -> dict[int, str]:
    """Return ``{participant_id: skill_priority}`` for every participant."""
    participant_ids = {level_up.participant_id for level_up in level_ups}
    return {
        participant_id: reconstruct_skill_priority(level_ups, participant_id)
        for participant_id in participant_ids
    }


def build_skill_progression(level_ups: Sequence[SkillLevelUp], participant_id: int) -> str:
    """Return the ordered skill level-up sequence (e.g. ``"QWEWQR..."``).

    Each character is the ability (``Q``/``W``/``E``/``R``) leveled at that step;
    the frontend reconstructs the level-by-level rank matrix from it.
    """
    letters = [
        SKILL_SLOTS[level_up.skill_slot]
        for level_up in sorted(level_ups, key=lambda event: event.timestamp)
        if level_up.participant_id == participant_id and level_up.skill_slot in SKILL_SLOTS
    ]
    return "".join(letters)
