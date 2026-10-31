"""Asynchronous Riot Games API client with a token-bucket rate limiter.

Implements strict compliance with Riot Developer API rate limits:

* 20 requests per 1 second (short window).
* 100 requests per 2 minutes (long window).

The client transparently handles ``HTTP 429`` responses by honouring the
``Retry-After`` header, applies exponential backoff with jitter for transient
server errors, and automatically retries.
"""

from __future__ import annotations

import asyncio
import logging
import random
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.parse import quote

import httpx

from src.riot.models import Match, Timeline

logger = logging.getLogger(__name__)

DEFAULT_SHORT_LIMIT = 20
DEFAULT_SHORT_WINDOW = 1.0
DEFAULT_LONG_LIMIT = 100
DEFAULT_LONG_WINDOW = 120.0

RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})
DEFAULT_MAX_RETRIES = 8
DEFAULT_BACKOFF_BASE = 1.0
DEFAULT_BACKOFF_MAX = 30.0


class RiotAPIError(Exception):
    """Raised when a Riot API request ultimately fails after retries."""


class TokenBucket:
    """A refilling token bucket used to rate-limit requests."""

    def __init__(
        self, capacity: int, window_seconds: float, initial_tokens: float | None = None
    ) -> None:
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        if window_seconds <= 0:
            raise ValueError("window_seconds must be positive")
        self.capacity = float(capacity)
        self.window_seconds = float(window_seconds)
        self._refill_rate = self.capacity / self.window_seconds
        # Starting full permits a burst up to ``capacity``. For Riot's long window
        # a full bucket would allow ~2x the limit inside the rolling window, which
        # triggers 429 storms, so callers can start it near-empty.
        self._tokens = (
            self.capacity
            if initial_tokens is None
            else min(self.capacity, max(0.0, float(initial_tokens)))
        )
        self._updated_at = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self, tokens: float = 1.0) -> None:
        """Block until ``tokens`` tokens are available, then consume them."""
        while True:
            async with self._lock:
                self._refill()
                if self._tokens >= tokens:
                    self._tokens -= tokens
                    return
                missing = tokens - self._tokens
                wait = missing / self._refill_rate
            await asyncio.sleep(wait)

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self._updated_at
        self._tokens = min(self.capacity, self._tokens + elapsed * self._refill_rate)
        self._updated_at = now


class TokenBucketRateLimiter:
    """Composite rate limiter enforcing both the short and long windows."""

    def __init__(
        self,
        short_limit: int = DEFAULT_SHORT_LIMIT,
        short_window: float = DEFAULT_SHORT_WINDOW,
        long_limit: int = DEFAULT_LONG_LIMIT,
        long_window: float = DEFAULT_LONG_WINDOW,
        long_initial_burst: float = 0.0,
    ) -> None:
        self._buckets = (
            TokenBucket(short_limit, short_window),
            TokenBucket(long_limit, long_window, initial_tokens=long_initial_burst),
        )

    async def acquire(self) -> None:
        """Acquire a single request slot across all configured windows."""
        await asyncio.gather(*(bucket.acquire() for bucket in self._buckets))


def parse_retry_after(value: str | None) -> float | None:
    """Parse a ``Retry-After`` header value into a delay in seconds.

    Supports both an integer number of seconds and an HTTP-date value. Returns
    ``None`` when the header is missing or malformed so callers can fall back to
    their own backoff strategy.
    """
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    if value.isdigit():
        return float(value)
    try:
        when = parsedate_to_datetime(value)
        if when is None:
            return None
        delay = (when - datetime.now(timezone.utc)).total_seconds()
        return max(0.0, delay)
    except (TypeError, ValueError, OverflowError):
        return None


def exponential_backoff(
    attempt: int,
    base: float = DEFAULT_BACKOFF_BASE,
    cap: float = DEFAULT_BACKOFF_MAX,
) -> float:
    """Return a jittered exponential backoff delay for a given attempt."""
    exponential = base * (2 ** max(0, attempt))
    delay = min(exponential, cap)
    jitter = random.uniform(0.0, delay)
    return jitter


class RiotClient:
    """Async HTTP client for the Riot match-v5 API with automatic throttling."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://americas.api.riotgames.com",
        *,
        rate_limiter: TokenBucketRateLimiter | None = None,
        timeout: float = 30.0,
        max_retries: int = DEFAULT_MAX_RETRIES,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._rate_limiter = rate_limiter or TokenBucketRateLimiter()
        self._max_retries = max_retries
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers={"X-Riot-Token": api_key},
            timeout=httpx.Timeout(timeout),
            transport=transport,
        )

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()

    async def __aenter__(self) -> "RiotClient":
        return self

    async def __aexit__(self, *exc_info: Any) -> None:
        await self.close()

    async def request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        """Perform a throttled, retrying HTTP request against the Riot API."""
        for attempt in range(self._max_retries + 1):
            await self._rate_limiter.acquire()
            try:
                response = await self._client.request(method, path, **kwargs)
            except httpx.TimeoutException as exc:
                if attempt >= self._max_retries:
                    raise RiotAPIError(f"Request timed out: {method} {path}") from exc
                await asyncio.sleep(exponential_backoff(attempt))
                continue
            except httpx.TransportError as exc:
                if attempt >= self._max_retries:
                    raise RiotAPIError(f"Transport error for {method} {path}: {exc}") from exc
                await asyncio.sleep(exponential_backoff(attempt))
                continue

            if response.status_code == 429:
                retry_after = parse_retry_after(response.headers.get("Retry-After"))
                delay = retry_after if retry_after is not None else exponential_backoff(attempt)
                logger.warning("Riot API rate limited (429); retrying in %.2fs", delay)
                await asyncio.sleep(delay)
                continue
            if response.status_code in {500, 502, 503, 504}:
                await asyncio.sleep(exponential_backoff(attempt))
                continue

            if response.is_error:
                response.raise_for_status()
            return response

        raise RiotAPIError(f"Max retries exceeded for {method} {path}")

    async def get_match_history(
        self, puuid: str, queue_id: int, count: int = 100, start: int = 0
    ) -> list[str]:
        """Fetch match ids for a PUUID in the given queue."""
        path = f"/lol/match/v5/matches/by-puuid/{quote(puuid, safe='')}/ids"
        params = {"queue": queue_id, "count": count, "start": start}
        response = await self.request("GET", path, params=params)
        payload = response.json()
        return list(payload) if isinstance(payload, list) else []

    async def get_match(self, match_id: str) -> Match:
        """Fetch and validate a single match."""
        path = f"/lol/match/v5/matches/{quote(match_id, safe='')}"
        response = await self.request("GET", path)
        return Match.model_validate(response.json())

    async def get_timeline(self, match_id: str) -> Timeline:
        """Fetch and validate a match timeline."""
        path = f"/lol/match/v5/matches/{quote(match_id, safe='')}/timeline"
        response = await self.request("GET", path)
        return Timeline.model_validate(response.json())
