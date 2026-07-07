"""Database query timeout and slow query monitoring."""
from __future__ import annotations

import asyncio
import logging
import time
from collections import deque
from typing import Any, Deque, Dict

import asyncpg

logger = logging.getLogger(__name__)


class QueryMonitor:
    """Execute queries with timeout handling and slow-query tracking."""

    def __init__(self, slow_query_threshold: float = 1.0, history_size: int = 100) -> None:
        """Initialize monitor settings."""
        self.slow_query_threshold = slow_query_threshold
        self.slow_queries: Deque[Dict[str, Any]] = deque(maxlen=history_size)

    async def execute_with_timeout(
        self,
        pool: asyncpg.Pool,
        query: str,
        *args: Any,
        timeout: float = 30.0,
    ) -> Any:
        """Execute a query and raise TimeoutError when it exceeds the timeout."""
        if pool is None:
            raise ValueError("Database pool cannot be None.")

        started = time.perf_counter()
        timed_out = False
        try:
            result = await asyncio.wait_for(self._execute(pool, query, *args), timeout=timeout)
            return result
        except asyncio.TimeoutError:
            timed_out = True
            duration = time.perf_counter() - started
            logger.error("Database query timed out after %.3fs: %s", duration, query)
            raise
        finally:
            duration = time.perf_counter() - started
            if duration > self.slow_query_threshold:
                payload = {
                    "query": query,
                    "duration": duration,
                    "args_count": len(args),
                    "timed_out": timed_out,
                }
                self.slow_queries.append(payload)
                logger.warning("Slow query detected: %s", payload)

    async def _execute(self, pool: asyncpg.Pool, query: str, *args: Any) -> Any:
        """Execute the query using a pooled connection."""
        async with pool.acquire() as connection:
            statement = query.strip().lower()
            if statement.startswith(("select", "with", "show")) or "returning" in statement:
                return await connection.fetch(query, *args)
            return await connection.execute(query, *args)
