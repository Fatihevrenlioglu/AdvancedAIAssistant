"""API deprecation management utilities."""
from __future__ import annotations

import functools
import inspect
import logging
from typing import Any, Awaitable, Callable, TypeVar, cast

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)
F = TypeVar("F", bound=Callable[..., Any])


class DeprecationManager:
    """Helpers for deprecating API endpoints."""

    @staticmethod
    def deprecated(version: str, sunset_date: str, replacement: str = "") -> Callable[[F], F]:
        """Decorate an endpoint to add RFC 8594 deprecation headers."""
        def decorator(func: F) -> F:
            setattr(func, "_deprecated_metadata", {
                "version": version,
                "sunset_date": sunset_date,
                "replacement": replacement,
            })

            async def _apply(result: Any, response: Response | None) -> Any:
                headers = {
                    "Deprecation": f'version="{version}"',
                    "Sunset": sunset_date,
                }
                if replacement:
                    headers["Link"] = f'<{replacement}>; rel="successor-version"'
                if isinstance(result, Response):
                    result.headers.update(headers)
                    return result
                if response is not None:
                    response.headers.update(headers)
                    return result
                return JSONResponse(content=result, headers=headers)

            if inspect.iscoroutinefunction(func):
                @functools.wraps(func)
                async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                    result = await cast(Callable[..., Awaitable[Any]], func)(*args, **kwargs)
                    return await _apply(result, kwargs.get("response"))

                setattr(async_wrapper, "_deprecated_metadata", getattr(func, "_deprecated_metadata"))
                return cast(F, async_wrapper)

            @functools.wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                result = func(*args, **kwargs)
                headers = {
                    "Deprecation": f'version="{version}"',
                    "Sunset": sunset_date,
                    **({"Link": f'<{replacement}>; rel="successor-version"'} if replacement else {}),
                }
                if isinstance(result, Response):
                    result.headers.update(headers)
                    return result
                return JSONResponse(
                    content=result,
                    headers=headers,
                )

            setattr(sync_wrapper, "_deprecated_metadata", getattr(func, "_deprecated_metadata"))
            return cast(F, sync_wrapper)

        return decorator

    @staticmethod
    def add_deprecation_middleware(app: FastAPI) -> None:
        """Add middleware that logs deprecated endpoint usage."""
        @app.middleware("http")
        async def deprecation_middleware(request: Request, call_next: Callable[..., Any]) -> Response:
            endpoint = request.scope.get("endpoint")
            metadata = getattr(endpoint, "_deprecated_metadata", None)
            response = await call_next(request)
            if metadata is not None:
                logger.warning(
                    "Deprecated endpoint used path=%s version=%s replacement=%s",
                    request.url.path,
                    metadata.get("version"),
                    metadata.get("replacement") or "n/a",
                )
            return response
