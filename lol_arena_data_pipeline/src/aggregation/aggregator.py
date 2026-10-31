"""Aggregation of per-match participant stats into per-champion Arena meta.

The module exposes pure, testable functions that turn raw participant rows and
timeline-derived item purchases into :class:`ChampionMetaRecord` instances keyed
by build archetype, plus a thin :class:`Aggregator` that wires them to the
repositories and the CommunityDragon reference data.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Mapping, Sequence

from src.database.repositories import (
    ChampionMetaRecord,
    ChampionMetaRepository,
    ItemPurchaseRepository,
    ParticipantRepository,
)
from src.reference.data import ARCHETYPES, ReferenceData

__all__ = [
    "WIN_PLACEMENT",
    "TOP4_PLACEMENT",
    "BUILD_ROUNDS",
    "tier_score",
    "tier_from_score",
    "perf_tier_from_win_rate",
    "mode",
    "build_champion_meta",
    "classify_rows",
    "Aggregator",
]

WIN_PLACEMENT = 1
TOP4_PLACEMENT = 4
#: Shop rounds used to derive core build archetypes.
BUILD_ROUNDS = (1, 2)

MAX_AUGMENTS = 12
MAX_ITEMS = 12
MAX_BUILD_STYLES = 5
MAX_PARTNERS = 10

#: Generic "random gift" consumables that pollute the Items-by-Round panels.
EXCLUDED_ROUND_ITEM_IDS: frozenset[int] = frozenset(
    {
        220000,  # Stat Bonus
        220001,  # Legendary Fighter Item
        220002,  # Legendary Marksman Item
        220003,  # Legendary Assassin Item
        220004,  # Legendary Mage Item
        220005,  # Legendary Tank Item
        220006,  # Legendary Support Item
        220007,  # Prismatic Item
        220008,  # Anvil Voucher
        220009,  # Gold Stat Anvil Voucher
        220010,  # Prismatic Stat Voucher
        220011,  # Bravery Voucher
    }
)

_ITEM_COLS = ("item0", "item1", "item2", "item3", "item4", "item5", "item6")
_AUGMENT_COLS = ("player_augment1", "player_augment2", "player_augment3", "player_augment4")


def mode(values: Sequence[Any]) -> Any:
    """Return the most common (non-empty) value, or ``None``."""
    filtered = [value for value in values if value not in (None, "")]
    if not filtered:
        return None
    return Counter(filtered).most_common(1)[0][0]


def tier_score(win_rate: float, top4_rate: float, avg_placement: float) -> float:
    """Blend win rate, top-4 rate, and placement into a 0..1 tier score."""
    placement_score = 1.0 - (avg_placement - 1.0) / 7.0
    placement_score = max(0.0, min(1.0, placement_score))
    return 0.6 * win_rate + 0.25 * top4_rate + 0.15 * placement_score


def tier_from_score(score: float) -> str:
    """Map a tier score to a display tier."""
    if score >= 0.68:
        return "S+"
    if score >= 0.55:
        return "S"
    if score >= 0.42:
        return "A"
    if score >= 0.30:
        return "B"
    return "C"


def perf_tier_from_win_rate(win_rate: float) -> str:
    """Map a win rate to a performance tier (for items/augments)."""
    if win_rate >= 0.55:
        return "S+"
    if win_rate >= 0.50:
        return "S"
    if win_rate >= 0.45:
        return "A"
    if win_rate >= 0.40:
        return "B"
    return "C"


def _row_items(row: Mapping[str, Any]) -> list[int]:
    return [int(row[key]) for key in _ITEM_COLS if row.get(key)]


def _row_augments(row: Mapping[str, Any]) -> list[int]:
    return [int(row[key]) for key in _AUGMENT_COLS if row.get(key)]


def classify_rows(
    rows: Sequence[Mapping[str, Any]], reference: ReferenceData
) -> dict[tuple[str, str], str]:
    """Classify each game (``(match_id, puuid)``) into a build archetype."""
    return {(row["match_id"], row["puuid"]): reference.classify(_row_items(row)) for row in rows}


def _pick_sort_key(entry: Mapping[str, Any]) -> tuple[float, int]:
    # Order by pick rate first, then by item id for determinism.
    return (
        -float(entry.get("pick_rate") or 0.0),
        int(entry.get("item_id") or entry.get("augment_id") or 0),
    )


def _item_json(
    counter: Mapping[int, int],
    total: int,
    reference: ReferenceData,
    wins: Mapping[int, int] | None = None,
) -> list[dict[str, Any]]:
    win_map = wins or {}
    result: list[dict[str, Any]] = []
    for item_id, count in counter.items():
        win_rate = win_map.get(item_id, 0) / count if count else 0.0
        result.append(
            {
                "item_id": item_id,
                "name": reference.item_name(item_id),
                "description": reference.item_description(item_id),
                "desc_html": reference.item_description_html(item_id),
                "icon": reference.item_icon(item_id),
                "price": reference.item_price(item_id),
                "performance_tier": perf_tier_from_win_rate(win_rate),
                "count": count,
                "pick_rate": round(count / total, 4) if total else 0.0,
                "win_rate": round(win_rate, 4),
            }
        )
    result.sort(key=_pick_sort_key)
    return result[:MAX_ITEMS]


def build_augments(
    rows: Sequence[Mapping[str, Any]], total: int, reference: ReferenceData
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Return ``(overall, silver, gold, prismatic)`` augment panels."""
    counts: Counter[int] = Counter()
    wins: Counter[int] = Counter()
    for row in rows:
        for augment_id in _row_augments(row):
            if reference.augment_tier(augment_id) == "special":
                continue
            counts[augment_id] += 1
            if int(row.get("placement", 0)) == WIN_PLACEMENT:
                wins[augment_id] += 1

    overall: list[dict[str, Any]] = []
    for augment_id, count in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])):
        win_rate = wins[augment_id] / count if count else 0.0
        overall.append(
            {
                "augment_id": augment_id,
                "name": reference.augment_name(augment_id),
                "description": reference.augment_description(augment_id),
                "desc_html": reference.augment_description_html(augment_id),
                "icon": reference.augment_icon(augment_id),
                "tier": reference.augment_tier(augment_id),
                "performance_tier": perf_tier_from_win_rate(win_rate),
                "count": count,
                "pick_rate": round(count / total, 4) if total else 0.0,
                "win_rate": round(win_rate, 4),
            }
        )
    overall.sort(key=_pick_sort_key)
    overall = overall[:MAX_AUGMENTS]

    def _by_tier(tier: str) -> list[dict[str, Any]]:
        return [entry for entry in overall if entry.get("tier") == tier]

    return overall, _by_tier("silver"), _by_tier("gold"), _by_tier("prismatic")


def build_skill_order_distribution(
    rows: Sequence[Mapping[str, Any]], total: int
) -> list[dict[str, Any]]:
    """Return skill-order strings with pick percentages."""
    counts: Counter[str] = Counter(
        row.get("skill_order_str", "") for row in rows if row.get("skill_order_str")
    )
    return [
        {"order": order, "count": count, "pick_rate": round(count / total, 4) if total else 0.0}
        for order, count in counts.most_common()
    ]


def build_round_items(
    purchases: Sequence[Mapping[str, Any]],
    placements: Mapping[tuple[str, str], int],
    total: int,
    reference: ReferenceData,
) -> dict[str, list[dict[str, Any]]]:
    """Group item purchases by Arena shop round, with performance tiers."""
    counts: dict[int, Counter[int]] = defaultdict(Counter)
    wins: dict[int, Counter[int]] = defaultdict(Counter)
    for purchase in purchases:
        round_number = purchase.get("round_number")
        if round_number is None:
            continue
        item_id = int(purchase["item_id"])
        if item_id in EXCLUDED_ROUND_ITEM_IDS:
            continue
        key = (purchase["match_id"], purchase["puuid"])
        counts[int(round_number)][item_id] += 1
        if placements.get(key) == WIN_PLACEMENT:
            wins[int(round_number)][item_id] += 1

    return {
        str(round_number): _item_json(counts[round_number], total, reference, wins[round_number])
        for round_number in sorted(counts)
    }


def build_prismatic_items(
    rows: Sequence[Mapping[str, Any]], total: int, reference: ReferenceData
) -> list[dict[str, Any]]:
    """Aggregate prismatic item choices with performance tiers."""
    counts: Counter[int] = Counter()
    wins: Counter[int] = Counter()
    for row in rows:
        for item_id in _row_items(row):
            if item_id in reference.prismatic:
                counts[item_id] += 1
                if int(row.get("placement", 0)) == WIN_PLACEMENT:
                    wins[item_id] += 1

    result: list[dict[str, Any]] = []
    for item_id, count in counts.items():
        win_rate = wins[item_id] / count if count else 0.0
        result.append(
            {
                "item_id": item_id,
                "name": reference.item_name(item_id),
                "description": reference.item_description(item_id),
                "desc_html": reference.item_description_html(item_id),
                "icon": reference.item_icon(item_id),
                "price": reference.item_price(item_id),
                "performance_tier": perf_tier_from_win_rate(win_rate),
                "count": count,
                "pick_rate": round(count / total, 4) if total else 0.0,
                "win_rate": round(win_rate, 4),
            }
        )
    result.sort(key=_pick_sort_key)
    return result[:MAX_ITEMS]


def build_full_build(
    rows: Sequence[Mapping[str, Any]],
    purchases: Sequence[Mapping[str, Any]],
    reference: ReferenceData,
) -> list[dict[str, Any]]:
    """Return a 6-item full build: 1 boots, 1 prismatic, then core by acquisition."""
    counts: Counter[int] = Counter()
    for row in rows:
        for item_id in _row_items(row):
            if item_id == 0 or item_id in EXCLUDED_ROUND_ITEM_IDS:
                continue
            if "Trinket" in reference.item_categories(item_id):
                continue
            counts[item_id] += 1

    boot = max(
        (item_id for item_id in counts if item_id in reference.boots),
        key=counts.get,
        default=None,
    )
    prismatic = max(
        (item_id for item_id in counts if item_id in reference.prismatic),
        key=counts.get,
        default=None,
    )

    core = [
        item_id
        for item_id in sorted(counts, key=lambda value: -counts[value])
        if item_id != boot
        and item_id != prismatic
        and item_id not in reference.boots
        and item_id not in reference.prismatic
    ]

    selected: list[int] = []
    if boot is not None:
        selected.append(boot)
    if prismatic is not None:
        selected.append(prismatic)
    selected.extend(core[: 6 - len(selected)])

    timestamps: dict[int, list[int]] = defaultdict(list)
    for purchase in purchases:
        item_id = int(purchase["item_id"])
        if item_id in selected:
            timestamps[item_id].append(int(purchase["timestamp"]))

    def median_timestamp(item_id: int) -> int:
        values = sorted(timestamps.get(item_id, []))
        return values[len(values) // 2] if values else 2**31

    core_ids = [item_id for item_id in selected if item_id not in (boot, prismatic)]
    core_ids.sort(key=median_timestamp)

    ordered: list[int] = []
    if boot is not None:
        ordered.append(boot)
    if prismatic is not None:
        ordered.append(prismatic)
    ordered.extend(core_ids)

    total = len(rows)
    result: list[dict[str, Any]] = []
    for item_id in ordered:
        result.append(
            {
                "item_id": item_id,
                "name": reference.item_name(item_id),
                "description": reference.item_description(item_id),
                "desc_html": reference.item_description_html(item_id),
                "icon": reference.item_icon(item_id),
                "price": reference.item_price(item_id),
                "pick_rate": round(counts[item_id] / total, 4) if total else 0.0,
            }
        )
    return result


def build_build_styles(
    rows: Sequence[Mapping[str, Any]],
    purchases: Sequence[Mapping[str, Any]],
    reference: ReferenceData,
) -> list[dict[str, Any]]:
    """Derive top core-build item combos from early-round purchases."""
    placements: dict[tuple[str, str], int] = {
        (row["match_id"], row["puuid"]): int(row["placement"]) for row in rows
    }
    by_game: dict[tuple[str, str], list[int]] = defaultdict(list)
    for purchase in purchases:
        if purchase.get("round_number") not in BUILD_ROUNDS:
            continue
        item_id = int(purchase["item_id"])
        if item_id in reference.boots or item_id in reference.elixirs:
            continue
        by_game[(purchase["match_id"], purchase["puuid"])].append(item_id)

    styles: dict[tuple[int, ...], dict[str, int]] = defaultdict(lambda: {"count": 0, "wins": 0})
    for game_key, items in by_game.items():
        core = tuple(sorted(set(items)))
        if not core:
            continue
        styles[core]["count"] += 1
        if placements.get(game_key, 0) == WIN_PLACEMENT:
            styles[core]["wins"] += 1

    result: list[dict[str, Any]] = []
    for core, stats in sorted(styles.items(), key=lambda kv: (-kv[1]["count"], kv[0])):
        result.append(
            {
                "items": [
                    {
                        "item_id": item_id,
                        "name": reference.item_name(item_id),
                        "icon": reference.item_icon(item_id),
                    }
                    for item_id in core
                ],
                "count": stats["count"],
                "win_rate": round(stats["wins"] / stats["count"], 4),
            }
        )
        if len(result) >= MAX_BUILD_STYLES:
            break
    return result


def build_partner_synergies(
    rows: Sequence[Mapping[str, Any]], names: Mapping[int, str] | None = None
) -> list[dict[str, Any]]:
    """Aggregate duo partner performance."""
    partners: dict[int, dict[str, int]] = defaultdict(lambda: {"count": 0, "wins": 0})
    for row in rows:
        partner_id = row.get("partner_champion_id")
        if not partner_id:
            continue
        partners[int(partner_id)]["count"] += 1
        if int(row.get("placement", 0)) == WIN_PLACEMENT:
            partners[int(partner_id)]["wins"] += 1

    result: list[dict[str, Any]] = []
    for partner_id, stats in sorted(partners.items(), key=lambda kv: (-kv[1]["count"], kv[0])):
        result.append(
            {
                "champion_id": partner_id,
                "champion_name": (names or {}).get(partner_id),
                "games": stats["count"],
                "win_rate": round(stats["wins"] / stats["count"], 4),
            }
        )
        if len(result) >= MAX_PARTNERS:
            break
    return result


def build_champion_meta(
    champion_id: int,
    patch_version: str,
    rows: Sequence[Mapping[str, Any]],
    purchases: Sequence[Mapping[str, Any]],
    reference: ReferenceData,
    names: Mapping[int, str] | None = None,
    build_style: str = "Recommended",
) -> ChampionMetaRecord:
    """Compute a :class:`ChampionMetaRecord` for one champion/build style."""
    total = len(rows)
    placements = [int(row.get("placement", 1)) for row in rows]
    win_count = sum(1 for placement in placements if placement == WIN_PLACEMENT)
    top4_count = sum(1 for placement in placements if placement <= TOP4_PLACEMENT)
    avg_placement = sum(placements) / total if total else 0.0
    win_rate = win_count / total if total else 0.0
    top4_rate = top4_count / total if total else 0.0

    champion_name = str(rows[0].get("champion_name", "")) if rows else ""
    skill_priority = mode([row.get("skill_order_str", "") for row in rows]) or ""
    skill_progression = mode([row.get("skill_progression", "") for row in rows]) or None

    score = tier_score(win_rate, top4_rate, avg_placement)
    tier_rank = tier_from_score(score)

    overall, silver, gold, prismatic = build_augments(rows, total, reference)

    placement_by_game: dict[tuple[str, str], int] = {
        (row["match_id"], row["puuid"]): int(row.get("placement", 0)) for row in rows
    }
    boots_counter: Counter[int] = Counter()
    boots_wins: Counter[int] = Counter()
    elixir_counter: Counter[int] = Counter()
    elixir_wins: Counter[int] = Counter()
    for purchase in purchases:
        item_id = int(purchase["item_id"])
        won = placement_by_game.get((purchase["match_id"], purchase["puuid"])) == WIN_PLACEMENT
        if item_id in reference.boots:
            boots_counter[item_id] += 1
            if won:
                boots_wins[item_id] += 1
        if item_id in reference.elixirs:
            elixir_counter[item_id] += 1
            if won:
                elixir_wins[item_id] += 1

    return ChampionMetaRecord(
        champion_id=champion_id,
        patch_version=patch_version,
        build_style=build_style,
        champion_name=champion_name,
        total_games=total,
        win_count=win_count,
        top4_count=top4_count,
        win_rate=round(win_rate, 4),
        top4_rate=round(top4_rate, 4),
        avg_placement=round(avg_placement, 4),
        tier_rank=tier_rank,
        skill_priority=skill_priority,
        skill_order_distribution=build_skill_order_distribution(rows, total),
        skill_progression=skill_progression,
        augments_overall=overall,
        augments_silver=silver,
        augments_gold=gold,
        augments_prismatic=prismatic,
        boots=_item_json(boots_counter, total, reference, boots_wins),
        prismatic_items=build_prismatic_items(rows, total, reference),
        full_build=build_full_build(rows, purchases, reference),
        round_items=build_round_items(purchases, placement_by_game, total, reference),
        elixirs=_item_json(elixir_counter, total, reference, elixir_wins),
        build_styles=build_build_styles(rows, purchases, reference),
        partner_synergies=build_partner_synergies(rows, names),
    )


class Aggregator:
    """Orchestrates aggregation of participant stats into champion meta."""

    def __init__(
        self,
        participants: ParticipantRepository,
        purchases: ItemPurchaseRepository,
        meta: ChampionMetaRepository,
        reference: ReferenceData | None = None,
    ) -> None:
        self._participants = participants
        self._purchases = purchases
        self._meta = meta
        self._reference = reference or ReferenceData()

    def aggregate_champion(self, champion_id: int, patch_minor: str) -> int:
        """Aggregate every build style for one champion; return style count."""
        names = self._participants.champion_names(patch_minor)
        rows = self._participants.for_champion(champion_id, patch_minor)
        purchases = self._purchases.for_champion(champion_id, patch_minor)
        if not rows:
            return 0

        style_by_game = classify_rows(rows, self._reference)
        styles = [
            style
            for style in ARCHETYPES
            if style in style_by_game.values() or style == "Recommended"
        ]

        for style in styles:
            style_rows = [
                row
                for row in rows
                if style == "Recommended" or style_by_game[(row["match_id"], row["puuid"])] == style
            ]
            style_games = {(row["match_id"], row["puuid"]) for row in style_rows}
            style_purchases = [
                purchase
                for purchase in purchases
                if (purchase["match_id"], purchase["puuid"]) in style_games
            ]
            record = build_champion_meta(
                champion_id,
                patch_minor,
                style_rows,
                style_purchases,
                self._reference,
                names,
                build_style=style,
            )
            self._meta.upsert(record)
        return len(styles)

    def aggregate_patch(self, patch_minor: str) -> int:
        """Aggregate every champion for a single patch; return champion count."""
        champions = self._participants.distinct_champions(patch_minor)
        for champion in champions:
            self.aggregate_champion(int(champion["champion_id"]), patch_minor)
        return len(champions)

    def aggregate_all(self) -> int:
        """Aggregate every patch present in the database."""
        total = 0
        for patch_minor in self._participants.distinct_patches():
            total += self.aggregate_patch(patch_minor)
        return total
