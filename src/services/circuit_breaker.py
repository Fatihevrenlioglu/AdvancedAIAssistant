"""Circuit breaker implementation for async workloads."""
from __future__ import annotations

import asyncio
import inspect
import time
from enum import Enum
from typing import Any, Callable


class CircuitBreakerOpenError(RuntimeError):
    """Raised when the circuit breaker is open."""


class CircuitState(str, Enum):
    """Circuit breaker states."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Protect services from repeated failing calls."""

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        timeout: float = 60.0,
        success_threshold: int = 2,
    ) -> None:
        """Initialize circuit breaker state."""
        self.name = name
        self.failure_threshold = max(failure_threshold, 1)
        self.timeout = timeout
        self.success_threshold = max(success_threshold, 1)
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = 0.0
        self._lock = asyncio.Lock()

    async def call(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Execute a function through the circuit breaker."""
        async with self._lock:
            self._transition_if_timeout_elapsed()
            if self.state == CircuitState.OPEN:
                raise CircuitBreakerOpenError(f"Circuit '{self.name}' is open.")

        try:
            result = func(*args, **kwargs)
            if inspect.isawaitable(result):
                result = await result
        except Exception:
            await self._record_failure()
            raise

        await self._record_success()
        return result

    def _transition_if_timeout_elapsed(self) -> None:
        """Move from open to half-open after timeout elapses."""
        if self.state == CircuitState.OPEN and (time.monotonic() - self.last_failure_time) >= self.timeout:
            self.state = CircuitState.HALF_OPEN
            self.success_count = 0

    async def _record_failure(self) -> None:
        """Record a failed call and update circuit state."""
        async with self._lock:
            self.failure_count += 1
            self.success_count = 0
            self.last_failure_time = time.monotonic()
            if self.state == CircuitState.HALF_OPEN or self.failure_count >= self.failure_threshold:
                self.state = CircuitState.OPEN
            else:
                self.state = CircuitState.CLOSED

    async def _record_success(self) -> None:
        """Record a successful call and update circuit state."""
        async with self._lock:
            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                if self.success_count >= self.success_threshold:
                    self.state = CircuitState.CLOSED
                    self.failure_count = 0
                    self.success_count = 0
            else:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                self.success_count = 0
