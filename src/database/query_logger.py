"""Structured query execution logging."""
from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Optional

logger = logging.getLogger(__name__)


class QueryLogger:
    """Log database query execution details."""

    @classmethod
    async def log_query(
        cls,
        query: str,
        args: tuple[Any, ...],
        duration: float,
        success: bool,
        error: Optional[BaseException] = None,
    ) -> None:
        """Log a completed query with duration and status."""
        payload = {
            "query": query,
            "args_count": len(args),
            "duration_ms": round(duration * 1000, 3),
            "success": success,
        }
        if error is not None:
            logger.error("Database query failed: %s error=%s", payload, error)
        else:
            logger.info("Database query executed: %s", payload)

    @classmethod
    @asynccontextmanager
    async def track(cls, query: str, args: tuple[Any, ...]) -> AsyncIterator[None]:
        """Track and log query execution inside an async context manager."""
        started = time.perf_counter()
        try:
            yield
        except Exception as exc:
            await cls.log_query(query, args, time.perf_counter() - started, False, exc)
            raise
        else:
            await cls.log_query(query, args, time.perf_counter() - started, True)
