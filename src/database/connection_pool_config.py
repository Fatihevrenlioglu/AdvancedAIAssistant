import logging
from typing import Optional, List, Any, Dict  # HATA 5 FIX: added type hint imports

logger = logging.getLogger(__name__)


class ConnectionPoolConfig:
    """Manages an asyncpg connection pool with safe lifecycle methods."""

    def __init__(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
        database: str,
        min_size: int = 10,
        max_size: int = 50,
    ):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.min_size = min_size
        self.max_size = max_size
        self.pool = None

    async def initialize(self):
        """Initialize and return the connection pool."""
        try:
            import asyncpg

            self.pool = await asyncpg.create_pool(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database,
                min_size=self.min_size,
                max_size=self.max_size,
            )
            logger.info("\u2705 Connection pool initialized")
            return self.pool
        except Exception as e:
            logger.error(f"\u274c Failed to initialize pool: {str(e)}")
            raise

    async def execute_with_connection(self, query: str, *args) -> List:  # HATA 5 FIX: return type
        """Execute a query and return all matching rows."""
        async with self.pool.acquire() as connection:
            return await connection.fetch(query, *args)

    async def execute_single(self, query: str, *args) -> Optional[Any]:  # HATA 5 FIX: new method
        """Execute query and return a single scalar value."""
        async with self.pool.acquire() as connection:
            result = await connection.fetchval(query, *args)
            return result

    async def close(self):
        """Close connection pool safely."""  # HATA 8 FIX: wrapped in try/except

        if self.pool:
            try:
                await self.pool.close()
                logger.info("\u2705 Connection pool closed")
            except Exception as e:
                logger.warning(f"Error closing pool: {str(e)}")
