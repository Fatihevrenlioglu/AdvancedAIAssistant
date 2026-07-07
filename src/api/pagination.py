"""Cursor pagination helpers."""
from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import asyncpg


class CursorPagination:
    """Encode and decode cursor payloads."""

    @staticmethod
    def encode_cursor(data: Dict[str, Any]) -> str:
        """Encode cursor data as base64 JSON."""
        payload = json.dumps(data, separators=(",", ":")).encode("utf-8")
        return base64.urlsafe_b64encode(payload).decode("utf-8")

    @staticmethod
    def decode_cursor(cursor: str) -> Dict[str, Any]:
        """Decode a base64 JSON cursor."""
        if not cursor:
            return {}
        padding = "=" * (-len(cursor) % 4)
        decoded = base64.urlsafe_b64decode(f"{cursor}{padding}".encode("utf-8"))
        return json.loads(decoded.decode("utf-8"))


@dataclass
class PaginatedResponse:
    """Simple paginated response payload."""

    items: List[Dict[str, Any]]
    next_cursor: Optional[str]
    prev_cursor: Optional[str]
    total: int
    has_more: bool


async def paginate(
    pool: asyncpg.Pool,
    query: str,
    params: tuple[Any, ...],
    cursor: Optional[str],
    limit: int = 20,
) -> PaginatedResponse:
    """Paginate a caller-supplied SELECT query by using a cursor-backed offset.

    Callers should provide an explicit column list in ``query`` to avoid exposing
    unintended columns from the underlying data source.
    """
    if pool is None:
        raise ValueError("Database pool cannot be None.")

    decoded = CursorPagination.decode_cursor(cursor or "")
    offset = max(int(decoded.get("offset", 0) or 0), 0)
    page_size = max(1, min(limit, 100))
    param_count = len(params)
    paginated_query = f"{query} OFFSET ${param_count + 1} LIMIT ${param_count + 2}"
    count_query = f"SELECT COUNT(*) FROM ({query}) AS count_query"

    async with pool.acquire() as connection:
        rows = await connection.fetch(paginated_query, *params, offset, page_size + 1)
        total = int(await connection.fetchval(count_query, *params))

    records = [dict(row) for row in rows[:page_size]]
    has_more = len(rows) > page_size
    next_cursor = None
    if has_more:
        next_cursor = CursorPagination.encode_cursor({"offset": offset + page_size})
    prev_cursor = None
    if offset > 0:
        prev_cursor = CursorPagination.encode_cursor({"offset": max(offset - page_size, 0)})
    return PaginatedResponse(
        items=records,
        next_cursor=next_cursor,
        prev_cursor=prev_cursor,
        total=total,
        has_more=has_more,
    )
