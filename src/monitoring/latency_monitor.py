"""Request latency tracking middleware."""
from __future__ import annotations

import time
from collections import deque
from statistics import mean
from typing import Any, Deque, Dict, List

from fastapi import FastAPI, Request


class LatencyMonitor:
    """Track recent HTTP response times."""

    _durations_ms: Deque[float] = deque(maxlen=1000)

    @staticmethod
    def add_latency_middleware(app: FastAPI) -> None:
        """Add middleware that measures request latency."""
        @app.middleware("http")
        async def latency_middleware(request: Request, call_next: Any) -> Any:
            started = time.perf_counter()
            response = await call_next(request)
            duration_ms = (time.perf_counter() - started) * 1000
            LatencyMonitor._durations_ms.append(duration_ms)
            response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"
            return response

    @classmethod
    def get_metrics(cls) -> Dict[str, Any]:
        """Return average and percentile latency metrics."""
        data: List[float] = list(cls._durations_ms)
        if not data:
            return {"count": 0, "avg": 0.0, "min": 0.0, "max": 0.0, "p95": 0.0, "p99": 0.0}

        sorted_data = sorted(data)

        def percentile(values: List[float], value: float) -> float:
            index = min(max(int(round((len(values) - 1) * value)), 0), len(values) - 1)
            return values[index]

        return {
            "count": len(sorted_data),
            "avg": round(mean(sorted_data), 3),
            "min": round(sorted_data[0], 3),
            "max": round(sorted_data[-1], 3),
            "p95": round(percentile(sorted_data, 0.95), 3),
            "p99": round(percentile(sorted_data, 0.99), 3),
        }
