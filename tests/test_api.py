"""Tests for API helpers."""
from __future__ import annotations

import os

from fastapi import FastAPI, Response
from fastapi.testclient import TestClient

os.environ.setdefault("APP_SKIP_STARTUP_RESOURCES", "1")

from src.api.batch_validator import BatchValidator
from src.api.deprecation import DeprecationManager
from src.api.pagination import CursorPagination
from src.main import app


def test_health_endpoint_returns_expected_payload() -> None:
    """Health endpoint should return 200 and service metadata."""
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    assert response.json()["service"] == "AdvancedAIAssistant"


def test_root_endpoint_returns_expected_payload() -> None:
    """Root endpoint should expose docs metadata."""
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["docs"] == "/docs"


def test_cursor_pagination_round_trip() -> None:
    """Cursor encoding and decoding should be lossless."""
    data = {"offset": 40, "sort": "created_at"}
    cursor = CursorPagination.encode_cursor(data)
    assert CursorPagination.decode_cursor(cursor) == data


def test_batch_validator_validate_batch_size() -> None:
    """Batch size validation should accept small payloads and reject large ones."""
    BatchValidator.validate_batch_size([1, 2, 3], max_size=3)
    try:
        BatchValidator.validate_batch_size(list(range(101)), max_size=100)
        assert False, "Expected ValueError for oversized batch"
    except ValueError:
        assert True


def test_deprecation_decorator_adds_headers() -> None:
    """Deprecated endpoints should include RFC 8594 headers."""
    local_app = FastAPI()
    DeprecationManager.add_deprecation_middleware(local_app)

    @local_app.get("/deprecated")
    @DeprecationManager.deprecated("v1", "Wed, 01 Jan 2031 00:00:00 GMT", "/v2/deprecated")
    async def deprecated_route(response: Response) -> dict[str, str]:
        return {"status": "ok"}

    client = TestClient(local_app)
    response = client.get("/deprecated")
    assert response.status_code == 200
    assert response.headers["Deprecation"] == 'version="v1"'
    assert response.headers["Sunset"] == "Wed, 01 Jan 2031 00:00:00 GMT"
