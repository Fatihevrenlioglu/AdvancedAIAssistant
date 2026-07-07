"""Basic API router for placeholder endpoints."""
from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel, Field

from src.api.batch_validator import BatchValidator
from src.api.pagination import CursorPagination, PaginatedResponse

router = APIRouter()

_SAMPLE_ITEMS: List[Dict[str, Any]] = [
    {"id": index, "name": f"item-{index}"} for index in range(1, 101)
]


class ItemPayload(BaseModel):
    """Placeholder item creation schema."""

    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=1000)


@router.get("/items")
async def list_items(cursor: Optional[str] = Query(default=None), limit: int = Query(default=20, ge=1, le=100)) -> Dict[str, Any]:
    """Return a paginated list of placeholder items."""
    decoded = CursorPagination.decode_cursor(cursor or "")
    offset = max(int(decoded.get("offset", 0) or 0), 0)
    sliced = _SAMPLE_ITEMS[offset:offset + limit + 1]
    items = sliced[:limit]
    has_more = len(sliced) > limit
    response = PaginatedResponse(
        items=items,
        next_cursor=CursorPagination.encode_cursor({"offset": offset + limit}) if has_more else None,
        prev_cursor=CursorPagination.encode_cursor({"offset": max(offset - limit, 0)}) if offset > 0 else None,
        total=len(_SAMPLE_ITEMS),
        has_more=has_more,
    )
    return asdict(response)


@router.post("/items/batch")
async def create_items_batch(payload: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
    """Validate and process a batch of placeholder items."""
    items = payload.get("items", [])

    async def processor(item: BaseModel) -> Dict[str, Any]:
        model = ItemPayload.model_validate(item.model_dump())
        return {"created": True, **model.model_dump()}

    return await BatchValidator.process_batch(items, processor, ItemPayload)


@router.get("/metrics")
async def get_metrics(request: Request) -> Dict[str, Any]:
    """Return basic application metrics."""
    cache = getattr(request.app.state, "cache", None)
    cache_stats = await cache.get_stats() if cache is not None and hasattr(cache, "get_stats") else {}
    return {
        "status": "ok",
        "items_available": len(_SAMPLE_ITEMS),
        "cache": cache_stats,
    }
