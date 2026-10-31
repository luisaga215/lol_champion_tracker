"""FastAPI application factory for the Arena data pipeline service."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from src.api.routes import router
from src.config import Settings, get_settings
from src.database.db import Database
from src.database.repositories import ChampionMetaRepository, CrawlQueueRepository
from src.reference.data import ReferenceData
from src.reference.loader import load_reference_data
from src.services.pipeline import PipelineService

__all__ = ["create_app", "app"]

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "database" / "schema.sql"


def create_app(
    settings: Settings | None = None,
    db: Database | None = None,
) -> FastAPI:
    """Build and wire the FastAPI application (with an injectable database)."""
    settings = settings or get_settings()
    owns_db = db is None
    if db is None:
        db = Database(settings.database_path, schema_path=SCHEMA_PATH)

    service = PipelineService(settings, db)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        reference = (
            await load_reference_data(db) if settings.reference_fetch_enabled else ReferenceData()
        )
        service.reference = reference
        application.state.reference = reference
        scheduler: asyncio.Task | None = None
        if settings.scheduler_enabled and settings.configured:
            scheduler = asyncio.create_task(service.run_forever())
        yield
        if scheduler is not None:
            scheduler.cancel()
            await asyncio.gather(scheduler, return_exceptions=True)
        if owns_db:
            db.close()

    application = FastAPI(
        title="LoL Arena Data Pipeline API",
        description="Aggregated League of Legends Arena meta statistics microservice.",
        version="1.0.0",
        lifespan=lifespan,
    )

    application.state.settings = settings
    application.state.db = db
    application.state.meta_repo = ChampionMetaRepository(db)
    application.state.queue_repo = CrawlQueueRepository(db)
    application.include_router(router)

    return application


app = create_app()
