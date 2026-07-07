"""Database connection pool configuration."""
import logging
from dataclasses import dataclass

import asyncpg

logger = logging.getLogger(__name__)


@dataclass
class ConnectionPoolConfig:
    host: str = "localhost"
    port: int = 5432
    user: str = "postgres"
    password: str = ""
    database: str = "advanced_ai"
    min_size: int = 10
    max_size: int = 50
    command_timeout: float = 60.0
    max_inactive_connection_lifetime: float = 300.0

    async def initialize(self) -> asyncpg.Pool:
        """Initialize and return the connection pool."""
        pool = await asyncpg.create_pool(
            **{
                "host": self.host,
                "port": self.port,
                "user": self.user,
                "password": self.password,
                "database": self.database,
                "min_size": self.min_size,
                "max_size": self.max_size,
                "command_timeout": self.command_timeout,
                "max_inactive_connection_lifetime": self.max_inactive_connection_lifetime,
            }
        )
        logger.info(
            "Connection pool initialized: min=%d, max=%d",
            self.min_size,
            self.max_size,
        )
        return pool
