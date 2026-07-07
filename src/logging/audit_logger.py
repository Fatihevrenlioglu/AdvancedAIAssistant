"""Security audit logging utilities."""
from __future__ import annotations

import contextvars
import json
import logging
from collections import deque
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.logging.request_id import RequestIDManager

logger = logging.getLogger(__name__)
REQUEST_IP_CTX_VAR: contextvars.ContextVar[str] = contextvars.ContextVar("request_ip", default="unknown")


class AuditLogger:
    """Capture audit events in memory and standard logs."""

    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    ACCESS_DENIED = "ACCESS_DENIED"
    RATE_LIMITED = "RATE_LIMITED"

    def __init__(self, max_events: int = 1000) -> None:
        """Initialize audit event storage."""
        self._events: deque[Dict[str, Any]] = deque(maxlen=max_events)

    async def log_event(
        self,
        event_type: str,
        user_id: Optional[str],
        resource: str,
        action: str,
        success: bool,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log a security-relevant audit event."""
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "request_id": RequestIDManager.get_request_id(),
            "ip_address": REQUEST_IP_CTX_VAR.get("unknown"),
            "event_type": event_type,
            "user_id": user_id,
            "resource": resource,
            "action": action,
            "success": success,
            "details": details or {},
        }
        self._events.appendleft(event)
        logger.info("AUDIT %s", json.dumps(event, sort_keys=True))

    async def get_user_events(self, user_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Return recent audit events for a user."""
        return [event for event in list(self._events) if event.get("user_id") == user_id][:limit]
