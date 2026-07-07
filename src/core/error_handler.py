import logging
from datetime import datetime  # HATA 4 FIX: added datetime import
from enum import Enum
from typing import Dict, Optional

from fastapi import HTTPException
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


class ErrorCode(Enum):
    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    RATE_LIMITED = "RATE_LIMITED"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"


class AppError(Exception):
    """Structured application error with HTTP response support."""

    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.INTERNAL_ERROR,
        status_code: int = 500,
        details: Optional[Dict] = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}

    def to_response(self) -> JSONResponse:
        """Convert error to a JSONResponse."""  # HATA 4 FIX: datetime.now() works with import above
        return JSONResponse(
            status_code=self.status_code,
            content={
                "error": self.code.value,
                "message": self.message,
                "details": self.details,
                "timestamp": datetime.now().isoformat(),
            },
        )


def create_error_handler():
    """Return a FastAPI exception handler for AppError."""

    async def handle_app_error(request, exc: AppError):
        logger.error(f"AppError [{exc.code.value}]: {exc.message}")
        return exc.to_response()

    return handle_app_error


def create_http_exception_handler():
    """Return a FastAPI exception handler for HTTPException."""

    async def handle_http_error(request, exc: HTTPException):
        logger.warning(f"HTTPException [{exc.status_code}]: {exc.detail}")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": "HTTP_ERROR",
                "message": exc.detail,
                "timestamp": datetime.now().isoformat(),
            },
        )

    return handle_http_error
