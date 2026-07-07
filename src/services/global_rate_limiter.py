"""Global in-memory sliding-window rate limiter."""
from __future__ import annotations

import asyncio
import time
from collections import defaultdict, deque
from typing import Any, Deque, Dict

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class GlobalRateLimiter:
    """Track client requests using minute and hour sliding windows."""

    def __init__(self, requests_per_minute: int = 60, requests_per_hour: int = 1000) -> None:
        """Initialize the rate limiter."""
        self.requests_per_minute = max(requests_per_minute, 1)
        self.requests_per_hour = max(requests_per_hour, 1)
        self._minute_windows: Dict[str, Deque[float]] = defaultdict(deque)
        self._hour_windows: Dict[str, Deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    async def is_allowed(self, client_id: str) -> bool:
        """Return whether the client is allowed to make a request."""
        async with self._lock:
            minute_count, hour_count = self._prune_and_count(client_id)
            if minute_count >= self.requests_per_minute or hour_count >= self.requests_per_hour:
                return False
            now = time.time()
            self._minute_windows[client_id].append(now)
            self._hour_windows[client_id].append(now)
            return True

    async def get_remaining(self, client_id: str) -> Dict[str, int]:
        """Return the client's remaining minute and hour quotas."""
        async with self._lock:
            minute_count, hour_count = self._prune_and_count(client_id)
            return {
                "minute": max(self.requests_per_minute - minute_count, 0),
                "hour": max(self.requests_per_hour - hour_count, 0),
            }

    def _prune_and_count(self, client_id: str) -> tuple[int, int]:
        """Prune expired timestamps and return current counts."""
        now = time.time()
        minute_cutoff = now - 60
        hour_cutoff = now - 3600
        minute_window = self._minute_windows[client_id]
        hour_window = self._hour_windows[client_id]
        while minute_window and minute_window[0] <= minute_cutoff:
            minute_window.popleft()
        while hour_window and hour_window[0] <= hour_cutoff:
            hour_window.popleft()
        return len(minute_window), len(hour_window)


def add_rate_limit_middleware(app: FastAPI, limiter: GlobalRateLimiter) -> None:
    """Add FastAPI middleware that enforces global rate limiting."""
    @app.middleware("http")
    async def rate_limit_middleware(request: Request, call_next: Any) -> Any:
        client_id = request.client.host if request.client is not None else "anonymous"
        if not await limiter.is_allowed(client_id):
            return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded."})
        response = await call_next(request)
        remaining = await limiter.get_remaining(client_id)
        response.headers["X-RateLimit-Remaining-Minute"] = str(remaining["minute"])
        response.headers["X-RateLimit-Remaining-Hour"] = str(remaining["hour"])
        return response
