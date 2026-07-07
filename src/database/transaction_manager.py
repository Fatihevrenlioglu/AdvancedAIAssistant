"""Transactional database execution helpers."""
from __future__ import annotations

import inspect
import re
from typing import Any, List, Tuple

import asyncpg

_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class TransactionManager:
    """Execute database work inside transactions and savepoints."""

    @staticmethod
    def _quote_identifier(identifier: str) -> str:
        """Validate and quote a SQL identifier for safe interpolation."""
        if not _IDENTIFIER_RE.match(identifier):
            raise ValueError("Invalid savepoint name.")
        return f'"{identifier}"'

    @staticmethod
    async def execute_transaction(pool: asyncpg.Pool, queries: List[Tuple[str, tuple[Any, ...]]]) -> bool:
        """Execute multiple queries atomically, rolling back on failure."""
        if pool is None:
            raise ValueError("Database pool cannot be None.")
        if not queries:
            return True

        async with pool.acquire() as connection:
            transaction = connection.transaction()
            if inspect.isawaitable(transaction):
                transaction = await transaction
            await transaction.start()
            try:
                for query, args in queries:
                    await connection.execute(query, *(args or ()))
                await transaction.commit()
                return True
            except Exception:
                await transaction.rollback()
                raise
            finally:
                del transaction

    @staticmethod
    async def execute_with_savepoint(
        pool: asyncpg.Pool,
        query: str,
        args: tuple[Any, ...],
        savepoint_name: str = "sp1",
    ) -> Any:
        """Execute a query within a transaction savepoint."""
        if pool is None:
            raise ValueError("Database pool cannot be None.")
        quoted_savepoint = TransactionManager._quote_identifier(savepoint_name)

        async with pool.acquire() as connection:
            transaction = connection.transaction()
            if inspect.isawaitable(transaction):
                transaction = await transaction
            await transaction.start()
            try:
                await connection.execute(f"SAVEPOINT {quoted_savepoint}")
                result = await connection.execute(query, *(args or ()))
                await connection.execute(f"RELEASE SAVEPOINT {quoted_savepoint}")
                await transaction.commit()
                return result
            except Exception:
                try:
                    await connection.execute(f"ROLLBACK TO SAVEPOINT {quoted_savepoint}")
                except Exception:
                    pass
                await transaction.rollback()
                raise
            finally:
                del transaction
