"""Load and cache CommunityDragon reference data (items + augments)."""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from src.database.db import Database
from src.reference.data import AugmentRef, ItemRef, ReferenceData, build_archetype_icons, cdn_icon

logger = logging.getLogger(__name__)

__all__ = [
    "CDRAGON_ITEMS_URL",
    "CDRAGON_AUGMENTS_URL",
    "DEFAULT_PRISMATIC_ITEM_IDS",
    "REFERENCE_VERSION",
    "build_reference_data",
    "load_reference_data",
]

CDRAGON_ITEMS_URL = (
    "https://raw.communitydragon.org/latest/plugins/"
    "rcp-be-lol-game-data/global/default/v1/items.json"
)
CDRAGON_AUGMENTS_URL = "https://raw.communitydragon.org/latest/cdragon/arena/en_us.json"

#: Bump when the stored reference format changes (forces a re-fetch).
REFERENCE_VERSION = "5"

#: Arena prismatic/mythic items live in this id range (verified against CDragon).
PRISMATIC_ID_RANGE = (400000, 700000)
PRISMATIC_MIN_PRICE = 2500

#: Known Arena prismatic item ids (curated; extendable). CommunityDragon does not
#: expose a "prismatic" marker, so this set is maintained manually.
DEFAULT_PRISMATIC_ITEM_IDS: frozenset[int] = frozenset({4017, 443069, 447101, 667101})


def build_reference_data(
    items_raw: list[dict[str, Any]],
    augments_raw: list[dict[str, Any]],
    prismatic_ids: frozenset[int] = DEFAULT_PRISMATIC_ITEM_IDS,
) -> ReferenceData:
    """Build :class:`ReferenceData` from raw CDragon JSON lists."""
    items: dict[int, ItemRef] = {}
    for raw in items_raw:
        item_id = raw.get("id")
        if not isinstance(item_id, int):
            continue
        items[item_id] = ItemRef(
            id=item_id,
            name=raw.get("name") or "",
            categories=tuple(raw.get("categories") or ()),
            description=raw.get("description") or "",
            icon=cdn_icon(raw.get("iconPath")),
            price=int(raw.get("priceTotal") or raw.get("price") or 0),
        )

    augments: dict[int, AugmentRef] = {}
    for raw in augments_raw:
        augment_id = raw.get("id")
        if not isinstance(augment_id, int):
            continue
        augments[augment_id] = AugmentRef(
            id=augment_id,
            name=raw.get("name") or "",
            rarity=int(raw.get("rarity", 0)),
            description=raw.get("desc") or raw.get("tooltip") or "",
            icon=cdn_icon(raw.get("iconSmall")),
        )

    boots = frozenset(item_id for item_id, item in items.items() if "Boots" in item.categories)
    elixirs = frozenset(
        item_id
        for item_id, item in items.items()
        if "Consumable" in item.categories and 2140 <= item_id <= 2147
    )
    prismatic = frozenset(
        raw["id"]
        for raw in items_raw
        if isinstance(raw.get("id"), int)
        and (
            (
                PRISMATIC_ID_RANGE[0] <= raw["id"] <= PRISMATIC_ID_RANGE[1]
                and raw.get("price", 0) >= PRISMATIC_MIN_PRICE
            )
            or raw["id"] in prismatic_ids
        )
    )

    return ReferenceData(
        items=items,
        augments=augments,
        boots=boots,
        elixirs=elixirs,
        prismatic=prismatic,
        archetype_icons=build_archetype_icons(items),
    )


async def _fetch_json(client: httpx.AsyncClient, url: str) -> list[dict[str, Any]]:
    response = await client.get(url)
    response.raise_for_status()
    payload = response.json()
    if isinstance(payload, dict) and "augments" in payload:
        return list(payload["augments"])
    if isinstance(payload, list):
        return payload
    return []


def _cached_version(db: Database) -> str | None:
    try:
        row = db.fetch_one("SELECT value FROM reference_meta WHERE key = 'version'")
    except Exception:  # noqa: BLE001 - table may not exist on very old DBs
        return None
    return row["value"] if row else None


def _load_cached(db: Database) -> ReferenceData | None:
    if _cached_version(db) != REFERENCE_VERSION:
        return None
    item_rows = db.fetch_all("SELECT * FROM reference_items")
    if not item_rows:
        return None
    items = {
        int(row["item_id"]): ItemRef(
            id=int(row["item_id"]),
            name=row["name"] or "",
            categories=tuple(json.loads(row["categories"])) if row["categories"] else (),
            description=row["description"] or "",
            icon=row["icon"] or "",
            price=int(row["price"] or 0),
        )
        for row in item_rows
    }
    augments: dict[int, AugmentRef] = {}
    for row in db.fetch_all("SELECT * FROM reference_augments"):
        augment_id = int(row["augment_id"])
        augments[augment_id] = AugmentRef(
            id=augment_id,
            name=row["name"] or "",
            rarity=int(row["rarity"] or 0),
            description=row["description"] or "",
            icon=row["icon"] or "",
        )
    boots = frozenset(i for i, item in items.items() if "Boots" in item.categories)
    elixirs = frozenset(
        i for i, item in items.items() if "Consumable" in item.categories and 2140 <= i <= 2147
    )
    return ReferenceData(
        items=items,
        augments=augments,
        boots=boots,
        elixirs=elixirs,
        prismatic=_load_prismatic(db),
        archetype_icons=build_archetype_icons(items),
    )


def _load_prismatic(db: Database) -> frozenset[int]:
    row = db.fetch_one("SELECT value FROM reference_meta WHERE key = 'prismatic'")
    if row and row["value"]:
        try:
            return frozenset(json.loads(row["value"]))
        except (TypeError, ValueError):
            pass
    return DEFAULT_PRISMATIC_ITEM_IDS


def _store(db: Database, reference: ReferenceData) -> None:
    db.execute("DELETE FROM reference_items")
    db.execute("DELETE FROM reference_augments")
    db.executemany(
        "INSERT OR REPLACE INTO reference_items "
        "(item_id, name, categories, description, icon, price) VALUES (?, ?, ?, ?, ?, ?)",
        [
            (
                item.id,
                item.name,
                json.dumps(item.categories),
                item.description,
                item.icon,
                item.price,
            )
            for item in reference.items.values()
        ],
    )
    db.executemany(
        "INSERT OR REPLACE INTO reference_augments "
        "(augment_id, name, rarity, description, icon) VALUES (?, ?, ?, ?, ?)",
        [
            (augment.id, augment.name, augment.rarity, augment.description, augment.icon)
            for augment in reference.augments.values()
        ],
    )
    db.execute(
        "INSERT OR REPLACE INTO reference_meta (key, value) VALUES ('version', ?)",
        (REFERENCE_VERSION,),
    )
    db.execute(
        "INSERT OR REPLACE INTO reference_meta (key, value) VALUES ('prismatic', ?)",
        (json.dumps(sorted(reference.prismatic)),),
    )


async def load_reference_data(db: Database, *, force_refresh: bool = False) -> ReferenceData:
    """Return reference data, fetching from CommunityDragon if not cached."""
    cached = _load_cached(db)
    if cached is not None and not force_refresh:
        return cached

    try:
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            items_raw, augments_raw = await _fetch_json(
                client, CDRAGON_ITEMS_URL
            ), await _fetch_json(client, CDRAGON_AUGMENTS_URL)
        reference = build_reference_data(items_raw, augments_raw)
        _store(db, reference)
        logger.info(
            "Loaded reference data: %d items, %d augments",
            len(reference.items),
            len(reference.augments),
        )
        return reference
    except Exception as exc:  # noqa: BLE001 - degrade gracefully on any fetch failure
        logger.warning("Failed to load CommunityDragon reference data: %s", exc)
        return cached or ReferenceData()
