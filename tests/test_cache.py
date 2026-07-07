"""Tests for cache helpers."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

import pytest

from src.cache.fallback_cache import FallbackCache
from src.cache.redis_cache import RedisCache


@pytest.mark.asyncio
async def test_fallback_cache_get_set_delete() -> None:
    """FallbackCache should store and remove values."""
    cache = FallbackCache()
    await cache.set("key", {"value": 1})
    assert await cache.get("key") == {"value": 1}
    await cache.delete("key")
    assert await cache.get("key") is None


@pytest.mark.asyncio
async def test_fallback_cache_ttl_expiry() -> None:
    """FallbackCache should expire TTL-bound entries."""
    cache = FallbackCache()
    await cache.set("key", "value", ttl=1)
    await asyncio.sleep(1.1)
    assert await cache.get("key") is None


@pytest.mark.asyncio
async def test_redis_cache_with_mock_redis() -> None:
    """RedisCache should use Redis when available."""
    redis = AsyncMock()
    redis.get.return_value = b'{"name":"test"}'
    redis.exists.return_value = 1
    redis.info.return_value = {"used_memory": 1, "used_memory_human": "1B"}
    cache = RedisCache(redis)

    await cache.set("key", {"name": "test"})
    assert await cache.get("key") == {"name": "test"}
    assert await cache.exists("key") is True
    stats = await cache.get_stats()
    assert stats["backend"] == "redis"


@pytest.mark.asyncio
async def test_redis_cache_fallback_to_memory_on_none() -> None:
    """RedisCache should read from fallback when Redis misses."""
    redis = AsyncMock()
    redis.get.return_value = None
    cache = RedisCache(redis)
    await cache.fallback.set("key", "fallback")
    assert await cache.get("key") == "fallback"


@pytest.mark.asyncio
async def test_cache_stats() -> None:
    """Fallback cache stats should track hits and misses."""
    cache = FallbackCache()
    await cache.set("key", "value")
    await cache.get("key")
    await cache.get("missing")
    stats = cache.get_stats()
    assert stats["hits"] == 1
    assert stats["misses"] == 1
    assert stats["size"] == 1
