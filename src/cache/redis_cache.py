import json
import logging
from datetime import datetime
from typing import Any, Optional

from redis.asyncio import Redis

logger = logging.getLogger(__name__)


class RedisCache:
    """Redis-backed cache with graceful degradation and custom JSON serialization."""

    def __init__(self, redis_client: Optional[Redis]):
        self.redis = redis_client
        self.available = redis_client is not None  # HATA 9 FIX: track availability
        self.stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
            "errors": 0,
        }

    @staticmethod
    def _json_serializer(obj):  # HATA 2 FIX: custom JSON serializer for complex types
        """Custom JSON serializer for complex types."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        if hasattr(obj, "__dict__"):
            return obj.__dict__
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

    async def get(self, key: str, default: Optional[Any] = None) -> Optional[Any]:
        """Get value from cache."""

        if not self.available or not self.redis:  # HATA 9 FIX
            logger.debug(f"Cache unavailable, returning default for {key}")
            return default

        try:
            value = await self.redis.get(key)
            if value:
                self.stats["hits"] += 1
                return json.loads(value)
            else:
                self.stats["misses"] += 1
                return default
        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"Cache error on GET {key}: {str(e)}")
            return default

    async def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """Set value in cache with TTL."""

        if not self.available or not self.redis:  # HATA 9 FIX
            logger.debug(f"Cache unavailable, skipping SET for {key}")
            return False

        try:
            serialized = json.dumps(value, default=self._json_serializer)  # HATA 2 FIX
            await self.redis.setex(key, ttl, serialized)
            self.stats["sets"] += 1
            logger.debug(f"Cache SET: {key} (ttl: {ttl}s)")
            return True
        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"Cache error on SET {key}: {str(e)}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete a key from cache."""

        if not self.available or not self.redis:
            return False

        try:
            await self.redis.delete(key)
            self.stats["deletes"] += 1
            logger.debug(f"Cache DELETE: {key}")
            return True
        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"Cache error on DELETE {key}: {str(e)}")
            return False

    def get_stats(self) -> dict:
        """Return cache statistics."""
        return dict(self.stats)
