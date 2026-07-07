"""Standardized application error handlers."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class ErrorHandler:
    """Register uniform JSON error responses."""

    @staticmethod
    def _payload(status_code: int, message: str, error_type: str) -> dict[str, Any]:
        """Build an error response payload."""
        return {"error": {"code": status_code, "message": message, "type": error_type}}

    @staticmethod
    def register(app: FastAPI) -> None:
        """Register application-wide exception handlers."""
        @app.exception_handler(ValueError)
        async def value_error_handler(_: Request, exc: ValueError) -> JSONResponse:
            logger.warning("Value error: %s", exc)
            return JSONResponse(status_code=400, content=ErrorHandler._payload(400, str(exc), "ValueError"))

        @app.exception_handler(KeyError)
        async def key_error_handler(_: Request, exc: KeyError) -> JSONResponse:
            logger.warning("Key error: %s", exc)
            return JSONResponse(status_code=404, content=ErrorHandler._payload(404, str(exc), "KeyError"))

        @app.exception_handler(PermissionError)
        async def permission_error_handler(_: Request, exc: PermissionError) -> JSONResponse:
            logger.warning("Permission error: %s", exc)
            return JSONResponse(status_code=403, content=ErrorHandler._payload(403, str(exc), "PermissionError"))

        @app.exception_handler(asyncio.TimeoutError)
        async def timeout_error_handler(_: Request, exc: asyncio.TimeoutError) -> JSONResponse:
            logger.error("Timeout error: %s", exc)
            return JSONResponse(status_code=504, content=ErrorHandler._payload(504, str(exc) or "Request timed out.", "TimeoutError"))

        @app.exception_handler(Exception)
        async def generic_exception_handler(_: Request, exc: Exception) -> JSONResponse:
            logger.exception("Unhandled exception")
            return JSONResponse(status_code=500, content=ErrorHandler._payload(500, str(exc) or "Internal server error.", type(exc).__name__))
