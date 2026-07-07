"""Index creation utilities for common database tables."""
from __future__ import annotations

import re
from typing import List, Optional

import asyncpg

_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class IndexingStrategy:
    """Create standard indexes safely for supported tables."""

    STANDARD_INDEXES = (
        ("users", ["email"], True, "idx_users_email"),
        ("users", ["created_at"], False, "idx_users_created_at"),
        ("sessions", ["user_id"], False, "idx_sessions_user_id"),
        ("sessions", ["created_at"], False, "idx_sessions_created_at"),
        ("audit_logs", ["user_id"], False, "idx_audit_logs_user_id"),
        ("audit_logs", ["created_at"], False, "idx_audit_logs_created_at"),
        ("api_requests", ["created_at"], False, "idx_api_requests_created_at"),
    )

    @staticmethod
    def _quote_identifier(identifier: str) -> str:
        """Validate and quote a SQL identifier."""
        if not _IDENTIFIER_RE.match(identifier):
            raise ValueError(f"Invalid SQL identifier: {identifier!r}")
        return f'"{identifier}"'

    @classmethod
    async def create_index(
        cls,
        pool: asyncpg.Pool,
        table: str,
        columns: List[str],
        unique: bool = False,
        index_name: Optional[str] = None,
    ) -> bool:
        """Create a validated index if it does not already exist."""
        if pool is None:
            return False
        if not columns:
            raise ValueError("At least one column is required to create an index.")

        quoted_table = cls._quote_identifier(table)
        quoted_columns = ", ".join(cls._quote_identifier(column) for column in columns)
        resolved_name = index_name or f"idx_{table}_{'_'.join(columns)}"
        quoted_index_name = cls._quote_identifier(resolved_name)
        unique_sql = "UNIQUE " if unique else ""
        query = (
            f"CREATE {unique_sql}INDEX IF NOT EXISTS {quoted_index_name} "
            f"ON {quoted_table} ({quoted_columns})"
        )
        async with pool.acquire() as connection:
            await connection.execute(query)
        return True

    @classmethod
    async def create_indexes(cls, pool: asyncpg.Pool) -> bool:
        """Create the standard application indexes."""
        for table, columns, unique, index_name in cls.STANDARD_INDEXES:
            await cls.create_index(pool, table, columns, unique=unique, index_name=index_name)
        return True
