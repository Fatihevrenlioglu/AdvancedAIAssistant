"""In-memory fallback cache implementation."""
from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, Optional


class FallbackCache:
    """A small in-memory cache with TTL support."""

    def __init__(self) -> None:
        """Initialize cache state."""
        self._store: dict[str, tuple[Any, float | None]] = {}
        self._lock = asyncio.Lock()
        self._hits = 0
        self._misses = 0

    async def get(self, key: str) -> Optional[Any]:
        """Return a cached value when present and unexpired."""
        async with self._lock:
            self._purge_expired_locked()
            record = self._store.get(key)
            if record is None:
                self._misses += 1
                return None
            self._hits += 1
            return record[0]

    async def set(self, key: str, value: Any, ttl: int = 300) -> None:
        """Store a value with an optional TTL.

        A non-positive TTL means the entry should not expire automatically.
        """
        expires_at = time.time() + ttl if ttl > 0 else None
        async with self._lock:
            self._store[key] = (value, expires_at)
            self._purge_expired_locked()

    async def delete(self, key: str) -> None:
        """Delete a cached value if present."""
        async with self._lock:
            self._store.pop(key, None)

    async def clear(self) -> None:
        """Clear all cached data."""
        async with self._lock:
            self._store.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Return cache hit, miss, and size statistics."""
        now = time.time()
        size = sum(1 for _, expires_at in self._store.values() if expires_at is None or expires_at > now)
        return {"hits": self._hits, "misses": self._misses, "size": size}

    def _purge_expired_locked(self) -> None:
        """Remove expired keys while the lock is held."""
        now = time.time()
        expired = [key for key, (_, expires_at) in self._store.items() if expires_at is not None and expires_at <= now]
        for key in expired:
            self._store.pop(key, None)
