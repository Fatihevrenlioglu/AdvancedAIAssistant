"""Helpers for validating database schema state."""
from __future__ import annotations

from typing import Any, Dict, List

import asyncpg


class SchemaValidator:
    """Validate database tables and columns through information_schema."""

    @staticmethod
    async def validate_table_exists(pool: asyncpg.Pool, table_name: str) -> bool:
        """Return whether a table exists in the public schema."""
        if pool is None or not table_name:
            return False

        query = """
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = $1 AND table_name = $2
            )
        """
        async with pool.acquire() as connection:
            return bool(await connection.fetchval(query, "public", table_name))

    @staticmethod
    async def validate_column_exists(pool: asyncpg.Pool, table_name: str, column_name: str) -> bool:
        """Return whether a column exists on a table in the public schema."""
        if pool is None or not table_name or not column_name:
            return False

        query = """
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema = $1
                  AND table_name = $2
                  AND column_name = $3
            )
        """
        async with pool.acquire() as connection:
            return bool(await connection.fetchval(query, "public", table_name, column_name))

    @staticmethod
    async def get_table_schema(pool: asyncpg.Pool, table_name: str) -> List[Dict[str, Any]]:
        """Return column metadata for a table in the public schema."""
        if pool is None or not table_name:
            return []

        query = """
            SELECT
                column_name,
                data_type,
                is_nullable,
                column_default,
                ordinal_position
            FROM information_schema.columns
            WHERE table_schema = $1 AND table_name = $2
            ORDER BY ordinal_position
        """
        async with pool.acquire() as connection:
            rows = await connection.fetch(query, "public", table_name)
        return [dict(row) for row in rows]
