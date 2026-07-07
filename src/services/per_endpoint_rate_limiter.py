"""Per-endpoint sliding-window rate limiter."""
from __future__ import annotations

import asyncio
import functools
import inspect
import time
from collections import defaultdict, deque
from typing import Any, Callable, Deque, Dict

from fastapi import Request
from fastapi.responses import JSONResponse


class PerEndpointRateLimiter:
    """Limit requests per client and endpoint."""

    def __init__(self, default_limit: int = 60) -> None:
        """Initialize limiter state."""
        self.default_limit = max(default_limit, 1)
        self._windows: Dict[tuple[str, str], Deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    def limit(self, requests_per_minute: int) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Decorate a FastAPI route with a per-endpoint rate limit."""
        limit_value = max(requests_per_minute, 1)

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            @functools.wraps(func)
            async def wrapper(*args: Any, **kwargs: Any) -> Any:
                request = kwargs.get("request")
                if request is None:
                    request = next((arg for arg in args if isinstance(arg, Request)), None)
                if isinstance(request, Request) and request.client is not None:
                    client_id = request.client.host
                else:
                    client_id = "anonymous"
                endpoint = self._resolve_endpoint_name(request, func)
                if not await self.check_limit(client_id, endpoint, limit_value):
                    return JSONResponse(status_code=429, content={"detail": "Endpoint rate limit exceeded."})
                result = func(*args, **kwargs)
                if inspect.isawaitable(result):
                    return await result
                return result

            return wrapper

        return decorator

    async def check_limit(self, client_id: str, endpoint: str, limit: int) -> bool:
        """Return whether the client can access the endpoint."""
        async with self._lock:
            key = (client_id, endpoint)
            now = time.time()
            cutoff = now - 60
            window = self._windows[key]
            while window and window[0] <= cutoff:
                window.popleft()
            if len(window) >= limit:
                return False
            window.append(now)
            return True

    @staticmethod
    def _resolve_endpoint_name(request: Any, func: Callable[..., Any]) -> str:
        """Resolve a stable endpoint name for rate-limit tracking."""
        if isinstance(request, Request):
            return request.url.path
        return getattr(func, "__name__", "endpoint")
