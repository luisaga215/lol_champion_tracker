"""Tests for the token-bucket rate limiter and Riot HTTP client."""

from __future__ import annotations

import asyncio
import time

import httpx
import pytest

from src.riot.client import (
    TokenBucket,
    TokenBucketRateLimiter,
    RiotClient,
    parse_retry_after,
    exponential_backoff,
)


class _NoopRateLimiter:
    async def acquire(self) -> None:
        return None


async def test_token_bucket_allows_burst_within_capacity() -> None:
    bucket = TokenBucket(capacity=3, window_seconds=1.0)
    start = time.monotonic()
    for _ in range(3):
        await bucket.acquire()
    assert time.monotonic() - start < 0.1


async def test_token_bucket_throttles_beyond_capacity() -> None:
    bucket = TokenBucket(capacity=2, window_seconds=1.0)
    start = time.monotonic()
    for _ in range(3):
        await bucket.acquire()
    elapsed = time.monotonic() - start
    assert elapsed >= 0.4


async def test_token_bucket_refills_over_time() -> None:
    bucket = TokenBucket(capacity=1, window_seconds=1.0)
    await bucket.acquire()
    await asyncio.sleep(1.1)
    start = time.monotonic()
    await bucket.acquire()
    assert time.monotonic() - start < 0.1


async def test_composite_rate_limiter_acquires() -> None:
    limiter = TokenBucketRateLimiter(
        short_limit=20,
        short_window=1.0,
        long_limit=100,
        long_window=120.0,
        long_initial_burst=5,
    )
    start = time.monotonic()
    await limiter.acquire()
    assert time.monotonic() - start < 0.1


def test_parse_retry_after_integer() -> None:
    assert parse_retry_after("5") == 5.0


def test_parse_retry_after_missing_or_invalid() -> None:
    assert parse_retry_after(None) is None
    assert parse_retry_after("") is None
    assert parse_retry_after("not-a-date") is None


def test_exponential_backoff_bounds() -> None:
    for attempt in range(10):
        delay = exponential_backoff(attempt)
        assert 0.0 <= delay <= 30.0


async def test_client_retries_on_429_and_sends_token() -> None:
    calls: dict[str, int] = {"count": 0}

    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["X-Riot-Token"] == "test-key"
        calls["count"] += 1
        if calls["count"] == 1:
            return httpx.Response(429, headers={"Retry-After": "0"})
        return httpx.Response(200, json={"ok": True})

    client = RiotClient(
        "test-key",
        "https://americas.api.riotgames.com",
        rate_limiter=_NoopRateLimiter(),
        transport=httpx.MockTransport(handler),
    )
    try:
        response = await client.request("GET", "/lol/test")
        assert response.status_code == 200
        assert calls["count"] == 2
    finally:
        await client.close()


async def test_client_raises_after_max_retries() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, headers={"Retry-After": "0"})

    client = RiotClient(
        "test-key",
        "https://americas.api.riotgames.com",
        rate_limiter=_NoopRateLimiter(),
        max_retries=2,
        transport=httpx.MockTransport(handler),
    )
    try:
        with pytest.raises(Exception):
            await client.request("GET", "/lol/test")
    finally:
        await client.close()
