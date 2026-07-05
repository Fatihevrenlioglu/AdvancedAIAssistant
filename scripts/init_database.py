import asyncio
import logging
import os

from src.database.connection_pool_config import ConnectionPoolConfig
from src.database.indexing_strategy import IndexingStrategy
from src.database.schema_validator import SchemaValidator

logger = logging.getLogger(__name__)


async def initialize_database() -> None:
    """Initialize database schema and indices."""
    config = ConnectionPoolConfig(
        os.getenv("DB_HOST", "localhost"),
        int(os.getenv("DB_PORT", "5432")),
        os.getenv("DB_USER", "postgres"),
        os.getenv("DB_PASSWORD", "postgres"),
        os.getenv("DB_NAME", "advanced_ai"),
        min_size=int(os.getenv("DB_POOL_MIN", "10")),
        max_size=int(os.getenv("DB_POOL_MAX", "50")),
    )

    try:
        pool = await config.initialize()
        validator = SchemaValidator()
        await validator.validate_schema(pool)
        indexing = IndexingStrategy()
        results = await indexing.create_all_indices(pool)
        logger.info("✅ Database initialized successfully")
        logger.info("✅ Indices created: %s/%s", sum(1 for value in results.values() if value), len(results))
    except Exception as exc:
        logger.error("❌ Database initialization failed: %s", exc)
        raise
    finally:
        await config.close()


if __name__ == "__main__":
    asyncio.run(initialize_database())
