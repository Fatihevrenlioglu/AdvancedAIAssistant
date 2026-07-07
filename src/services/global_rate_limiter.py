import logging
from datetime import datetime  # HATA 3 FIX: added datetime import
from typing import Dict, Tuple

from aioredis import Redis

logger = logging.getLogger(__name__)


class GlobalRateLimiter:
    """Redis-backed global rate limiter with graceful degradation."""

    def __init__(
        self,
        redis_client: Redis,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
    ):
        self.redis = redis_client
        self.rpm_limit = requests_per_minute
        self.rph_limit = requests_per_hour
        self.available = redis_client is not None  # HATA 10 FIX: track availability

    async def check_rate_limit(self, user_id: str) -> Tuple[bool, Dict]:
        """Check if user has exceeded rate limit.

        Returns (allowed, info_dict).
        """

        # If Redis unavailable, allow request  # HATA 10 FIX
        if not self.available or not self.redis:
            logger.warning("Rate limiter unavailable, allowing request")
            return True, {}

        current_time = datetime.now()  # HATA 3 FIX: datetime now available
        minute_key = f"rate:minute:{user_id}:{current_time.strftime('%Y%m%d%H%M')}"
        hour_key = f"rate:hour:{user_id}:{current_time.strftime('%Y%m%d%H')}"

        try:
            # Check minute limit
            minute_count = await self.redis.incr(minute_key)
            if minute_count == 1:
                await self.redis.expire(minute_key, 60)

            if minute_count > self.rpm_limit:
                logger.warning(f"Rate limit exceeded (per minute) for user {user_id}")
                return False, {
                    "error": "Rate limit exceeded",
                    "limit": self.rpm_limit,
                    "window": "minute",
                    "current": minute_count,
                }

            # Check hour limit
            hour_count = await self.redis.incr(hour_key)
            if hour_count == 1:
                await self.redis.expire(hour_key, 3600)

            if hour_count > self.rph_limit:
                logger.warning(f"Rate limit exceeded (per hour) for user {user_id}")
                return False, {
                    "error": "Rate limit exceeded",
                    "limit": self.rph_limit,
                    "window": "hour",
                    "current": hour_count,
                }

            return True, {
                "remaining_minute": self.rpm_limit - minute_count,
                "remaining_hour": self.rph_limit - hour_count,
            }

        except Exception as e:
            logger.error(f"Rate limiter error: {str(e)}")
            return True, {}  # Allow on error
