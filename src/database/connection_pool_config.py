import logging
from typing import Any, Optional

import asyncpg

logger = logging.getLogger(__name__)


class ConnectionPoolConfig:
    """Optimized connection pool configuration."""

    def __init__(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
        database: str,
        min_size: int = 10,
        max_size: int = 50,
        timeout: int = 30,
    ):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.min_size = min_size
        self.max_size = max_size
        self.timeout = timeout
        self.pool: Optional[asyncpg.Pool] = None

    async def initialize(self) -> asyncpg.Pool:
        """Initialize the asyncpg connection pool."""
        try:
            auth_kwargs = {"password": self.password}
            self.pool = await asyncpg.create_pool(
                host=self.host,
                port=self.port,
                user=self.user,
                **auth_kwargs,
                database=self.database,
                min_size=self.min_size,
                max_size=self.max_size,
                command_timeout=self.timeout,
                server_settings={
                    "application_name": "AdvancedAIAssistant",
                    "jit": "on",
                },
            )
            logger.info("✅ Connection pool initialized: %s-%s", self.min_size, self.max_size)
            return self.pool
        except Exception as exc:
            logger.error("❌ Failed to initialize connection pool: %s", exc)
            raise

    async def close(self) -> None:
        """Close the connection pool if it was initialized."""
        if self.pool:
            await self.pool.close()
            logger.info("✅ Connection pool closed")

    async def execute_with_connection(self, query: str, *args: Any):
        """Execute a fetch query using a pooled connection."""
        if not self.pool:
            raise RuntimeError("Connection pool has not been initialized")

        async with self.pool.acquire() as connection:
            return await connection.fetch(query, *args)

    async def get_pool_status(self) -> dict[str, Any]:
        """Get current pool status metrics."""
        if not self.pool:
            return {"status": "not_initialized"}

        size = self.pool.get_size()
        idle = self.pool.get_idle_size()
        max_size = self.pool.get_max_size()
        min_size = self.pool.get_min_size()
        utilized = max(size - idle, 0)

        return {
            "size": size,
            "idle": idle,
            "max_size": max_size,
            "min_size": min_size,
            "utilization_percent": (utilized / max_size * 100) if max_size > 0 else 0,
        }
