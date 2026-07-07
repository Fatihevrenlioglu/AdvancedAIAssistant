"""Redis-backed cache with automatic in-memory fallback."""
from __future__ import annotations

import json
import logging
from datetime import date, datetime
from typing import Any, Dict, Optional

from src.cache.fallback_cache import FallbackCache

logger = logging.getLogger(__name__)


class RedisCache:
    """Cache abstraction that prefers Redis and falls back to memory."""

    def __init__(self, redis: Optional[Any]) -> None:
        """Initialize the cache backend."""
        self.redis = redis
        self.fallback = FallbackCache()

    async def get(self, key: str) -> Optional[Any]:
        """Get a value from Redis or fallback cache."""
        if self.redis is None:
            return await self.fallback.get(key)

        try:
            payload = await self.redis.get(key)
            if payload is None:
                return await self.fallback.get(key)
            if isinstance(payload, bytes):
                payload = payload.decode("utf-8")
            return json.loads(payload)
        except Exception as exc:
            logger.warning("Redis get failed for key=%s: %s", key, exc)
            return await self.fallback.get(key)

    async def set(self, key: str, value: Any, ttl: int = 300) -> None:
        """Set a value in Redis and mirror it to the fallback cache."""
        serialized = json.dumps(value, default=self._json_default)
        await self.fallback.set(key, value, ttl=ttl)
        if self.redis is None:
            return

        try:
            await self.redis.set(key, serialized, ex=max(ttl, 1))
        except Exception as exc:
            logger.warning("Redis set failed for key=%s: %s", key, exc)

    async def delete(self, key: str) -> None:
        """Delete a key from both Redis and fallback cache."""
        await self.fallback.delete(key)
        if self.redis is None:
            return

        try:
            await self.redis.delete(key)
        except Exception as exc:
            logger.warning("Redis delete failed for key=%s: %s", key, exc)

    async def exists(self, key: str) -> bool:
        """Return whether a key exists in either cache layer."""
        if self.redis is not None:
            try:
                return bool(await self.redis.exists(key))
            except Exception as exc:
                logger.warning("Redis exists failed for key=%s: %s", key, exc)
        return await self.fallback.get(key) is not None

    async def get_stats(self) -> Dict[str, Any]:
        """Return Redis and fallback cache statistics."""
        stats: Dict[str, Any] = {"backend": "fallback" if self.redis is None else "redis"}
        stats["fallback"] = self.fallback.get_stats()
        if self.redis is None:
            return stats

        try:
            info = await self.redis.info("memory")
            stats["redis"] = {
                "used_memory": info.get("used_memory"),
                "used_memory_human": info.get("used_memory_human"),
            }
        except Exception as exc:
            logger.warning("Redis stats failed: %s", exc)
            stats["redis"] = {"available": False}
        return stats

    @staticmethod
    def _json_default(value: Any) -> str:
        """Serialize datetime-like objects for JSON storage."""
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")
