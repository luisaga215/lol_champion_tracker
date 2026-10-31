"""Reference (static) data model: items, augments, and build archetypes.

This module defines the domain types and lookups used to enrich raw numeric ids
(item ids and augment ids) with names, descriptions, rarity tiers, and build
archetype classifications. The actual data is populated by
:mod:`src.reference.loader` from CommunityDragon.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Mapping, Sequence

__all__ = [
    "ARCHETYPES",
    "ARCHETYPE_CATEGORIES",
    "ARCHETYPE_ICON_ITEMS",
    "RARITY_TO_TIER",
    "CDRAGON_ASSET_BASE",
    "ItemRef",
    "AugmentRef",
    "ReferenceData",
    "classify_build",
    "build_archetype_icons",
    "cdn_icon",
    "strip_html",
]

#: Build-style dropdown order (matches Metasrc).
ARCHETYPES: tuple[str, ...] = (
    "Recommended",
    "AD",
    "Crit",
    "MS",
    "CDR",
    "HP",
    "On-Hit",
    "Lethality",
    "MR",
    "AP",
    "AR",
    "LS",
    "Mana",
    "SV",
)

#: Archetype -> CommunityDragon item categories that signal that playstyle.
ARCHETYPE_CATEGORIES: dict[str, frozenset[str]] = {
    "Recommended": frozenset(),
    "AD": frozenset({"Damage"}),
    "Crit": frozenset({"CriticalStrike"}),
    "MS": frozenset({"NonbootsMovement"}),
    "CDR": frozenset({"CooldownReduction", "AbilityHaste"}),
    "HP": frozenset({"Health"}),
    "On-Hit": frozenset({"AttackSpeed"}),
    "Lethality": frozenset({"ArmorPenetration", "Lethality"}),
    "MR": frozenset({"MagicResist", "SpellBlock"}),
    "AP": frozenset({"SpellDamage"}),
    "AR": frozenset({"Armor"}),
    "LS": frozenset({"LifeSteal", "Lifesteal"}),
    "Mana": frozenset({"Mana"}),
    "SV": frozenset({"SpellVamp"}),
}

#: CommunityDragon augment ``rarity`` -> tier name.
RARITY_TO_TIER: dict[int, str] = {
    0: "silver",
    1: "gold",
    2: "prismatic",
    4: "special",
}

#: Base URL for CommunityDragon game assets (icons).
CDRAGON_ASSET_BASE = (
    "https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default"
)

#: Representative icon item (by name) for each build-style dropdown entry.
ARCHETYPE_ICON_ITEMS: dict[str, str] = {
    "Recommended": "Berserker's Greaves",
    "AD": "Serrated Dirk",
    "Crit": "Infinity Edge",
    "MS": "Boots of Swiftness",
    "CDR": "Ionian Boots of Lucidity",
    "HP": "Warmog's Armor",
    "On-Hit": "Recurve Bow",
    "Lethality": "Serrated Dirk",
    "MR": "Negatron Cloak",
    "AP": "Needlessly Large Rod",
    "AR": "Chain Vest",
    "LS": "Vampiric Scepter",
    "Mana": "Sapphire Crystal",
    "SV": "Hextech Revolver",
}

_TAG_RE = re.compile(r"<[^>]+>")


def strip_html(text: str | None) -> str:
    """Strip HTML tags and collapse whitespace for display."""
    if not text:
        return ""
    cleaned = _TAG_RE.sub(" ", text)
    return " ".join(cleaned.split())


def cdn_icon(icon_path: str | None) -> str:
    """Convert a CommunityDragon asset path into a loadable absolute URL."""
    if not icon_path:
        return ""
    path = icon_path.lower().lstrip("/")
    if path.startswith("lol-game-data/"):
        path = path[len("lol-game-data/") :]
    while path.startswith("assets/assets/"):
        path = path[len("assets/") :]
    return f"{CDRAGON_ASSET_BASE}/{path}"


def build_archetype_icons(items: Mapping[int, "ItemRef"]) -> dict[str, str]:
    """Resolve a representative icon URL for each build archetype."""
    by_name = {item.name: item for item in items.values()}
    icons: dict[str, str] = {}
    for archetype, name in ARCHETYPE_ICON_ITEMS.items():
        item = by_name.get(name)
        if item and item.icon:
            icons[archetype] = item.icon
            continue
        categories = ARCHETYPE_CATEGORIES.get(archetype, frozenset())
        for candidate in items.values():
            if candidate.icon and categories & set(candidate.categories):
                icons[archetype] = candidate.icon
                break
    return icons


@dataclass(frozen=True)
class ItemRef:
    """Static metadata for a single item."""

    id: int
    name: str
    categories: tuple[str, ...] = ()
    description: str = ""
    icon: str = ""
    price: int = 0

    @property
    def plain_description(self) -> str:
        return strip_html(self.description)


@dataclass(frozen=True)
class AugmentRef:
    """Static metadata for a single augment."""

    id: int
    name: str
    rarity: int
    description: str = ""
    icon: str = ""

    @property
    def tier(self) -> str | None:
        return RARITY_TO_TIER.get(self.rarity)

    @property
    def plain_description(self) -> str:
        return strip_html(self.description)


@dataclass
class ReferenceData:
    """In-memory reference lookups over items and augments."""

    items: dict[int, ItemRef] = field(default_factory=dict)
    augments: dict[int, AugmentRef] = field(default_factory=dict)
    boots: frozenset[int] = frozenset()
    elixirs: frozenset[int] = frozenset()
    prismatic: frozenset[int] = frozenset()
    archetype_icons: dict[str, str] = field(default_factory=dict)

    def item_name(self, item_id: int) -> str | None:
        item = self.items.get(item_id)
        return item.name if item else None

    def item_categories(self, item_id: int) -> tuple[str, ...]:
        item = self.items.get(item_id)
        return item.categories if item else ()

    def item_description(self, item_id: int) -> str:
        item = self.items.get(item_id)
        return item.plain_description if item else ""

    def item_icon(self, item_id: int) -> str:
        item = self.items.get(item_id)
        return item.icon if item else ""

    def item_price(self, item_id: int) -> int:
        item = self.items.get(item_id)
        return item.price if item else 0

    def item_description_html(self, item_id: int) -> str:
        item = self.items.get(item_id)
        return item.description if item else ""

    def augment_name(self, augment_id: int) -> str | None:
        augment = self.augments.get(augment_id)
        return augment.name if augment else None

    def augment_tier(self, augment_id: int) -> str | None:
        augment = self.augments.get(augment_id)
        return augment.tier if augment else None

    def augment_description(self, augment_id: int) -> str:
        augment = self.augments.get(augment_id)
        return augment.plain_description if augment else ""

    def augment_icon(self, augment_id: int) -> str:
        augment = self.augments.get(augment_id)
        return augment.icon if augment else ""

    def augment_description_html(self, augment_id: int) -> str:
        augment = self.augments.get(augment_id)
        return augment.description if augment else ""

    def archetype_icon(self, archetype: str) -> str:
        return self.archetype_icons.get(archetype, "")

    def classify(self, item_ids: Sequence[int]) -> str:
        """Classify a set of equipped item ids into a build archetype."""
        return classify_build(item_ids, self)


def classify_build(item_ids: Sequence[int], reference: ReferenceData) -> str:
    """Return the dominant build archetype for a set of items.

    Each non-Recommended archetype scores +1 per equipped item that carries one
    of its categories. The highest-scoring archetype wins (ties resolve in
    ``ARCHETYPES`` order); a zero score falls back to ``"Recommended"``.
    """
    best = "Recommended"
    best_score = 0
    for archetype in ARCHETYPES[1:]:
        categories = ARCHETYPE_CATEGORIES[archetype]
        score = sum(
            1 for item_id in item_ids if categories & set(reference.item_categories(item_id))
        )
        if score > best_score:
            best_score = score
            best = archetype
    return best
