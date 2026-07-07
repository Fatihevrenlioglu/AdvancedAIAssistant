"""Request ID middleware and helpers."""
from __future__ import annotations

import contextvars
import uuid
from typing import Any

from fastapi import FastAPI, Request


class RequestIDManager:
    """Track request IDs in a context variable."""

    REQUEST_ID_CTX_VAR: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="")

    @staticmethod
    def add_request_id_middleware(app: FastAPI) -> None:
        """Add middleware that attaches request IDs to requests and responses."""
        @app.middleware("http")
        async def request_id_middleware(request: Request, call_next: Any) -> Any:
            request_id = str(uuid.uuid4())
            token = RequestIDManager.REQUEST_ID_CTX_VAR.set(request_id)
            ip_token = None
            try:
                existing_headers = list(request.scope.get("headers", []))
                request.scope["headers"] = [
                    *existing_headers,
                    (b"x-request-id", request_id.encode("utf-8")),
                ]
                request.state.request_id = request_id
                try:
                    from src.logging.audit_logger import REQUEST_IP_CTX_VAR

                    client_ip = request.client.host if request.client is not None else "unknown"
                    ip_token = REQUEST_IP_CTX_VAR.set(client_ip)
                except Exception:
                    ip_token = None
                response = await call_next(request)
                response.headers["X-Request-ID"] = request_id
                return response
            finally:
                if ip_token is not None:
                    try:
                        from src.logging.audit_logger import REQUEST_IP_CTX_VAR

                        REQUEST_IP_CTX_VAR.reset(ip_token)
                    except Exception:
                        pass
                RequestIDManager.REQUEST_ID_CTX_VAR.reset(token)

    @staticmethod
    def get_request_id() -> str:
        """Return the current request ID, generating one if absent."""
        current = RequestIDManager.REQUEST_ID_CTX_VAR.get("")
        if current:
            return current
        generated = str(uuid.uuid4())
        RequestIDManager.REQUEST_ID_CTX_VAR.set(generated)
        return generated
