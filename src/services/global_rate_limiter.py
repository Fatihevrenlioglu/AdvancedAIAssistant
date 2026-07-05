import logging
from datetime import datetime, timezone
from typing import Dict, Tuple

from redis.asyncio import Redis

logger = logging.getLogger(__name__)


class GlobalRateLimiter:
    """Global rate limiting with per-minute and per-hour windows."""

    def __init__(
        self,
        redis_client: Redis,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
    ):
        self.redis = redis_client
        self.rpm_limit = requests_per_minute
        self.rph_limit = requests_per_hour

    async def check_rate_limit(self, user_id: str) -> Tuple[bool, Dict[str, int | str]]:
        """Check whether a user is still within the configured limits."""
        current_time = datetime.now(timezone.utc)
        minute_key = f"rate:minute:{user_id}:{current_time.strftime('%Y%m%d%H%M')}"
        hour_key = f"rate:hour:{user_id}:{current_time.strftime('%Y%m%d%H')}"

        try:
            minute_count = await self.redis.incr(minute_key)
            if minute_count == 1:
                await self.redis.expire(minute_key, 60)
            if minute_count > self.rpm_limit:
                logger.warning("Rate limit exceeded (per minute) for user %s", user_id)
                return False, {
                    "error": "Rate limit exceeded",
                    "limit": self.rpm_limit,
                    "window": "minute",
                    "current": minute_count,
                }

            hour_count = await self.redis.incr(hour_key)
            if hour_count == 1:
                await self.redis.expire(hour_key, 3600)
            if hour_count > self.rph_limit:
                logger.warning("Rate limit exceeded (per hour) for user %s", user_id)
                return False, {
                    "error": "Rate limit exceeded",
                    "limit": self.rph_limit,
                    "window": "hour",
                    "current": hour_count,
                }

            return True, {
                "remaining_minute": max(self.rpm_limit - minute_count, 0),
                "remaining_hour": max(self.rph_limit - hour_count, 0),
            }
        except Exception as exc:  # pragma: no cover - defensive logging path
            logger.error("Rate limiter error: %s", exc)
            return True, {}
