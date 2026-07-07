"""Connection pool metrics collection utilities."""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict

import asyncpg

logger = logging.getLogger(__name__)


class PoolMetrics:
    """Collect and periodically log asyncpg pool metrics."""

    @staticmethod
    def get_metrics(pool: asyncpg.Pool) -> Dict[str, Any]:
        """Return a defensive snapshot of pool metrics."""
        if pool is None:
            return {"size": 0, "free_connections": 0, "used_connections": 0, "max_size": 0}

        holders = getattr(pool, "_holders", []) or []
        queue = getattr(pool, "_queue", None)
        max_size = int(getattr(pool, "_maxsize", len(holders) or 0) or 0)
        size = len(holders)
        free_connections = int(queue.qsize()) if queue is not None and hasattr(queue, "qsize") else 0
        used_connections = max(size - free_connections, 0)
        return {
            "size": size,
            "free_connections": free_connections,
            "used_connections": used_connections,
            "max_size": max_size,
        }

    @staticmethod
    async def log_metrics(pool: asyncpg.Pool, interval_seconds: int = 60) -> None:
        """Log pool metrics forever until cancelled."""
        try:
            while True:
                logger.info("Database pool metrics: %s", PoolMetrics.get_metrics(pool))
                await asyncio.sleep(max(interval_seconds, 1))
        except asyncio.CancelledError:
            logger.info("Database pool metrics logger cancelled.")
            raise
