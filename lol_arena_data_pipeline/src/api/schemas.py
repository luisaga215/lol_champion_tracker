"""Pydantic response schemas for the Arena meta API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

__all__ = [
    "ChampionMeta",
    "ChampionSummary",
    "BuildStyleSummary",
    "BuildStyleInfo",
    "HealthResponse",
    "SeedRequest",
    "SeedResponse",
]


class ChampionSummary(BaseModel):
    """Lightweight champion reference."""

    champion_id: int
    champion_name: str


class BuildStyleSummary(BaseModel):
    """A build style with its sample size and a representative (champion) icon."""

    build_style: str
    total_games: int
    icon: str = ""


class BuildStyleInfo(BaseModel):
    """A build style with its representative icon."""

    build_style: str
    icon: str = ""


class ChampionMeta(BaseModel):
    """Aggregated Arena meta for a champion on a single patch/build style."""

    model_config = ConfigDict(extra="ignore")

    champion_id: int
    patch_version: str
    build_style: str = "Recommended"
    champion_name: str
    total_games: int
    win_count: int
    top4_count: int
    win_rate: float
    top4_rate: float
    avg_placement: float
    tier_rank: str
    skill_priority: str

    skill_order_distribution: list[dict[str, Any]] = Field(default_factory=list)
    skill_progression: str | None = None
    augments_overall: list[dict[str, Any]] = Field(default_factory=list)
    augments_silver: list[dict[str, Any]] = Field(default_factory=list)
    augments_gold: list[dict[str, Any]] = Field(default_factory=list)
    augments_prismatic: list[dict[str, Any]] = Field(default_factory=list)
    boots: list[dict[str, Any]] = Field(default_factory=list)
    prismatic_items: list[dict[str, Any]] = Field(default_factory=list)
    round_items: dict[str, list[dict[str, Any]]] = Field(default_factory=dict)
    elixirs: list[dict[str, Any]] = Field(default_factory=list)
    build_styles: list[dict[str, Any]] = Field(default_factory=list)
    partner_synergies: list[dict[str, Any]] = Field(default_factory=list)
    updated_at: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _coerce_nulls(cls, data: Any) -> Any:
        if isinstance(data, dict):
            for key in (
                "skill_order_distribution",
                "augments_overall",
                "augments_silver",
                "augments_gold",
                "augments_prismatic",
                "boots",
                "prismatic_items",
                "elixirs",
                "build_styles",
                "partner_synergies",
            ):
                if data.get(key) is None:
                    data[key] = []
            if data.get("round_items") is None:
                data["round_items"] = {}
        return data


class HealthResponse(BaseModel):
    """Service health payload."""

    status: str
    riot_configured: bool


class SeedRequest(BaseModel):
    """Request to enqueue PUUIDs into the crawl frontier."""

    puuids: list[str]
    queue_ids: list[int] | None = None


class SeedResponse(BaseModel):
    """Result of a crawl-seed request."""

    queued: int
