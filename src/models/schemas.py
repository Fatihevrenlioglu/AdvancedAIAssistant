"""Shared Pydantic schemas for API responses and requests."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


class UserCreate(BaseModel):
    """User creation payload."""

    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8, repr=False, json_schema_extra={"writeOnly": True})


class UserResponse(BaseModel):
    """Public user response payload."""

    id: int
    email: EmailStr
    username: str
    created_at: datetime
    is_active: bool


class TokenResponse(BaseModel):
    """Authentication token response."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int


class BatchRequest(BaseModel):
    """Batch request payload."""

    items: List[Dict[str, Any]]

    @field_validator("items")
    @classmethod
    def validate_max_size(cls, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Ensure no more than 100 items are submitted."""
        if len(items) > 100:
            raise ValueError("Batch request cannot exceed 100 items.")
        return items


class PaginationParams(BaseModel):
    """Query parameters for cursor pagination."""

    cursor: Optional[str] = None
    limit: int = Field(default=20, ge=1, le=100)


class ErrorResponse(BaseModel):
    """Standard error response model."""

    error: Dict[str, Any]


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str
    service: str
    version: str
