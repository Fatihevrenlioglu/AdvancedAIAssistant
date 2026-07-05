import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Optional

from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


class ErrorCode(str, Enum):
    """Standard error codes."""

    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    CONFLICT = "CONFLICT"
    RATE_LIMIT = "RATE_LIMIT"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    DATABASE_ERROR = "DATABASE_ERROR"
    EXTERNAL_SERVICE_ERROR = "EXTERNAL_SERVICE_ERROR"


class StandardError:
    """Standard error response format."""

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        status_code: int,
        details: Optional[Dict] = None,
        request_id: Optional[str] = None,
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        self.request_id = request_id

    def to_response(self) -> JSONResponse:
        """Convert to an HTTP JSON response."""
        return JSONResponse(
            status_code=self.status_code,
            content={
                "error": {
                    "code": self.code.value,
                    "message": self.message,
                    "details": self.details,
                },
                "request_id": self.request_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )


class ErrorHandler:
    """Global error handler."""

    @staticmethod
    async def handle_validation_error(errors: list, request_id: str) -> JSONResponse:
        """Handle validation errors."""
        logger.warning("Validation error: %s", errors)
        error = StandardError(
            code=ErrorCode.VALIDATION_ERROR,
            message="Input validation failed",
            status_code=400,
            details={"errors": errors},
            request_id=request_id,
        )
        return error.to_response()

    @staticmethod
    async def handle_database_error(error: Exception, request_id: str) -> JSONResponse:
        """Handle database errors."""
        logger.error("Database error: %s", error)
        err = StandardError(
            code=ErrorCode.DATABASE_ERROR,
            message="Database operation failed",
            status_code=500,
            details={"error": str(error)[:100]},
            request_id=request_id,
        )
        return err.to_response()
