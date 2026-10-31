"""Application configuration loaded from environment variables.

All settings are defined with sane defaults so the service can boot without any
environment preparation, while still allowing full override via environment
variables or a local ``.env`` file.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

#: Arena standard queue id.
ARENA_STANDARD_QUEUE = 1700
#: Arena 16-player custom lobby queue id.
ARENA_CUSTOM_QUEUE = 1710


class Settings(BaseSettings):
    """Runtime configuration for the Arena data pipeline service."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    riot_api_key: str = Field(default="", description="Riot Developer API key (X-Riot-Token).")
    riot_base_url: str = Field(
        default="https://americas.api.riotgames.com",
        description="Base URL for the Riot match-v5 regional routing endpoint.",
    )
    request_timeout: float = Field(default=30.0, description="HTTP request timeout in seconds.")

    database_path: str = Field(
        default="data/arena_pipeline.db",
        description="Filesystem path to the SQLite database file.",
    )

    queue_ids: list[int] = Field(
        default_factory=lambda: [ARENA_STANDARD_QUEUE, ARENA_CUSTOM_QUEUE],
        description="Arena queue ids targeted by the crawler.",
    )
    crawler_concurrency: int = Field(default=5, ge=1, le=100, description="Crawler worker count.")
    crawler_max_matches_per_seed: int = Field(
        default=100, ge=1, description="Max match-history pages per seed PUUID."
    )
    crawler_match_history_count: int = Field(
        default=100, ge=1, le=100, description="match list page size."
    )
    crawler_seed_puuids: list[str] = Field(
        default_factory=list,
        description="Bootstrap PUUIDs used to seed the crawl frontier.",
    )

    scheduler_enabled: bool = Field(
        default=False,
        description="Run the crawl/aggregate loop in the background of the API process.",
    )
    crawler_interval_seconds: int = Field(
        default=900, ge=60, description="Seconds between scheduled crawl+aggregate cycles."
    )
    reference_fetch_enabled: bool = Field(
        default=True,
        description="Fetch CommunityDragon item/augment reference data at startup.",
    )

    api_host: str = Field(default="0.0.0.0", description="API bind host.")
    api_port: int = Field(default=8000, ge=1, le=65535, description="API bind port.")

    @property
    def configured(self) -> bool:
        """Whether a Riot API key has been provided."""
        return bool(self.riot_api_key)


@lru_cache
def get_settings() -> Settings:
    """Return a cached :class:`Settings` instance."""
    return Settings()
