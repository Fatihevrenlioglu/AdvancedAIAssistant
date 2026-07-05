import json
import logging
from typing import Any, Optional

from redis.asyncio import Redis

logger = logging.getLogger(__name__)


class RedisCache:
    """Redis caching layer with async support."""

    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        self.stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
            "errors": 0,
        }

    async def get(self, key: str, default: Optional[Any] = None) -> Optional[Any]:
        """Get value from cache."""
        try:
            value = await self.redis.get(key)
            if value is None:
                self.stats["misses"] += 1
                logger.debug("Cache MISS: %s", key)
                return default

            self.stats["hits"] += 1
            logger.debug("Cache HIT: %s", key)
            if isinstance(value, bytes):
                value = value.decode("utf-8")
            return json.loads(value)
        except Exception as exc:
            self.stats["errors"] += 1
            logger.error("Cache error on GET %s: %s", key, exc)
            return default

    async def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """Set value in cache."""
        try:
            serialized = json.dumps(value, default=str)
            await self.redis.setex(key, ttl, serialized)
            self.stats["sets"] += 1
            logger.debug("Cache SET: %s (ttl: %ss)", key, ttl)
            return True
        except Exception as exc:
            self.stats["errors"] += 1
            logger.error("Cache error on SET %s: %s", key, exc)
            return False

    async def delete(self, key: str) -> bool:
        """Delete value from cache."""
        try:
            await self.redis.delete(key)
            self.stats["deletes"] += 1
            logger.debug("Cache DELETE: %s", key)
            return True
        except Exception as exc:
            self.stats["errors"] += 1
            logger.error("Cache error on DELETE %s: %s", key, exc)
            return False

    async def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching pattern."""
        removed = 0
        try:
            async for key in self.redis.scan_iter(match=pattern):
                await self.redis.delete(key)
                removed += 1
            logger.info("Cache CLEAR: %s keys matching '%s'", removed, pattern)
            return removed
        except Exception as exc:
            self.stats["errors"] += 1
            logger.error("Cache error on CLEAR %s: %s", pattern, exc)
            return 0

    def get_statistics(self) -> dict[str, Any]:
        """Get cache statistics."""
        total = self.stats["hits"] + self.stats["misses"]
        hit_rate = (self.stats["hits"] / total * 100) if total > 0 else 0
        return {
            "hits": self.stats["hits"],
            "misses": self.stats["misses"],
            "hit_rate_percent": hit_rate,
            "sets": self.stats["sets"],
            "deletes": self.stats["deletes"],
            "errors": self.stats["errors"],
        }
