"""Retry helpers for transient database connection failures."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import asyncpg

logger = logging.getLogger(__name__)


class RetryManager:
    """Execute database queries with exponential backoff retries."""

    RETRYABLE_ERRORS = (
        asyncpg.PostgresConnectionError,
        asyncpg.TooManyConnectionsError,
    )

    @staticmethod
    async def execute_with_retry(
        pool: asyncpg.Pool,
        query: str,
        *args: Any,
        max_retries: int = 3,
        base_delay: float = 0.5,
    ) -> Any:
        """Execute a query against a pool with retry support."""
        if pool is None:
            raise ValueError("Database pool cannot be None.")

        attempt = 0
        while True:
            try:
                async with pool.acquire() as connection:
                    return await RetryManager._execute(connection, query, *args)
            except RetryManager.RETRYABLE_ERRORS as exc:
                attempt += 1
                if attempt > max_retries:
                    logger.error("Database query failed after %d retries: %s", max_retries, exc)
                    raise
                delay = base_delay * (2 ** (attempt - 1))
                logger.warning(
                    "Retrying database query after transient error (attempt %d/%d, delay %.2fs): %s",
                    attempt,
                    max_retries,
                    delay,
                    exc,
                )
                await asyncio.sleep(delay)

    @staticmethod
    async def _execute(connection: asyncpg.Connection, query: str, *args: Any) -> Any:
        """Execute a query using an appropriate asyncpg method."""
        statement = query.strip().lower()
        if statement.startswith(("select", "with", "show")):
            return await connection.fetch(query, *args)
        if "returning" in statement:
            return await connection.fetch(query, *args)
        return await connection.execute(query, *args)
