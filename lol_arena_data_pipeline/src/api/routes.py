"""FastAPI routes for the Arena meta service."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from src.api.schemas import (
    BuildStyleInfo,
    BuildStyleSummary,
    ChampionMeta,
    ChampionSummary,
    HealthResponse,
    SeedRequest,
    SeedResponse,
)
from src.database.repositories import ChampionMetaRepository, CrawlQueueRepository
from src.reference.data import ARCHETYPES, ReferenceData

__all__ = ["router"]

router = APIRouter()


def get_meta_repo(request: Request) -> ChampionMetaRepository:
    return request.app.state.meta_repo


def get_queue_repo(request: Request) -> CrawlQueueRepository:
    return request.app.state.queue_repo


def get_reference(request: Request) -> ReferenceData:
    return getattr(request.app.state, "reference", ReferenceData())


@router.get("/health", response_model=HealthResponse, tags=["system"])
def health(request: Request) -> HealthResponse:
    """Liveness/readiness probe with Riot key configuration status."""
    return HealthResponse(
        status="ok",
        riot_configured=request.app.state.settings.configured,
    )


@router.get("/api/arena/patches", response_model=list[str], tags=["arena"])
def list_patches(meta: ChampionMetaRepository = Depends(get_meta_repo)) -> list[str]:
    """List available patch versions (newest first)."""
    return meta.list_patches()


@router.get("/api/arena/build-styles", response_model=list[BuildStyleInfo], tags=["arena"])
def list_build_styles(
    reference: ReferenceData = Depends(get_reference),
) -> list[BuildStyleInfo]:
    """List every build style with its representative icon (for the dropdown)."""
    return [
        BuildStyleInfo(build_style=archetype, icon=reference.archetype_icon(archetype))
        for archetype in ARCHETYPES
    ]


@router.get("/api/arena/champions", response_model=list[ChampionSummary], tags=["arena"])
def list_champions(
    patch: str | None = Query(default=None),
    meta: ChampionMetaRepository = Depends(get_meta_repo),
) -> list[ChampionSummary]:
    """List champions with aggregated meta (optionally scoped to a patch)."""
    rows = meta.list_champions(patch)
    return [
        ChampionSummary(champion_id=row["champion_id"], champion_name=row["champion_name"])
        for row in rows
    ]


@router.get("/api/arena/meta", response_model=list[ChampionMeta], tags=["arena"])
def list_meta(
    patch: str | None = Query(default=None),
    tier: str | None = Query(default=None, description="Filter by tier (S+, S, A, B, C)"),
    build_style: str = Query(default="Recommended", description="Build archetype"),
    meta: ChampionMetaRepository = Depends(get_meta_repo),
) -> list[ChampionMeta]:
    """List aggregated champion meta, optionally filtered by patch/tier/build."""
    rows = meta.list(patch, build_style=build_style)
    if tier is not None:
        rows = [row for row in rows if row.get("tier_rank") == tier]
    return [ChampionMeta.model_validate(row) for row in rows]


@router.get("/api/arena/meta/{champion_id}", response_model=ChampionMeta, tags=["arena"])
def get_meta(
    champion_id: int,
    patch: str | None = Query(default=None, description="Patch version (defaults to latest)"),
    build_style: str = Query(default="Recommended", description="Build archetype"),
    meta: ChampionMetaRepository = Depends(get_meta_repo),
) -> ChampionMeta:
    """Fetch meta for a single champion on the latest (or specified) patch."""
    patch_version = patch or (meta.list_patches()[0] if meta.list_patches() else None)
    if patch_version is None:
        raise HTTPException(status_code=404, detail="Champion meta not found")
    row = meta.get(champion_id, patch_version, build_style)
    if row is None:
        raise HTTPException(status_code=404, detail="Champion meta not found")
    return ChampionMeta.model_validate(row)


@router.get(
    "/api/arena/meta/{champion_id}/styles",
    response_model=list[BuildStyleSummary],
    tags=["arena"],
)
def list_styles(
    champion_id: int,
    patch: str | None = Query(default=None, description="Patch version (defaults to latest)"),
    meta: ChampionMetaRepository = Depends(get_meta_repo),
) -> list[BuildStyleSummary]:
    """List available build styles for a champion (for the dropdown)."""
    patches = meta.list_patches()
    patch_version = patch or (patches[0] if patches else None)
    if patch_version is None:
        return []
    return [
        BuildStyleSummary(
            build_style=row["build_style"],
            total_games=row["total_games"],
            icon=row.get("icon", ""),
        )
        for row in meta.list_styles(champion_id, patch_version)
    ]


@router.get(
    "/api/arena/meta/{champion_id}/patch/{patch_version}",
    response_model=ChampionMeta,
    tags=["arena"],
)
def get_meta_for_patch(
    champion_id: int,
    patch_version: str,
    build_style: str = Query(default="Recommended", description="Build archetype"),
    meta: ChampionMetaRepository = Depends(get_meta_repo),
) -> ChampionMeta:
    """Fetch meta for a single champion on a specific patch/build style."""
    row = meta.get(champion_id, patch_version, build_style)
    if row is None:
        raise HTTPException(status_code=404, detail="Champion meta not found")
    return ChampionMeta.model_validate(row)


@router.post("/api/arena/crawl/seed", response_model=SeedResponse, tags=["crawler"])
def seed_crawl(
    payload: SeedRequest,
    request: Request,
    queue_repo: CrawlQueueRepository = Depends(get_queue_repo),
) -> SeedResponse:
    """Enqueue PUUIDs so the next crawl cycle expands their Arena match history."""
    settings = request.app.state.settings
    queue_ids = payload.queue_ids or settings.queue_ids
    queued = 0
    for puuid in payload.puuids:
        for queue_id in queue_ids:
            if queue_repo.enqueue(puuid, queue_id):
                queued += 1
    return SeedResponse(queued=queued)
