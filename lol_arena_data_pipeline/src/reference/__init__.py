"""CommunityDragon reference data (items, augments, build archetypes)."""

from src.reference.data import (
    ARCHETYPE_CATEGORIES,
    ARCHETYPES,
    AugmentRef,
    ItemRef,
    ReferenceData,
    classify_build,
    strip_html,
)
from src.reference.loader import load_reference_data

__all__ = [
    "ARCHETYPE_CATEGORIES",
    "ARCHETYPES",
    "AugmentRef",
    "ItemRef",
    "ReferenceData",
    "classify_build",
    "load_reference_data",
    "strip_html",
]
