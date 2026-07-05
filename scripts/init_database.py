"""Database initialization script - HATA 12 FIX: added finally block for safe cleanup."""
import asyncio
import logging
import sys
import os

# Allow running from project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.database.connection_pool_config import ConnectionPoolConfig
from src.database.indexing_strategy import IndexingStrategy

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def initialize_database():
    """Initialize database with schema and indices."""

    config = ConnectionPoolConfig(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "postgres"),
        database=os.getenv("DB_NAME", "advanced_ai"),
        min_size=int(os.getenv("DB_POOL_MIN", "10")),
        max_size=int(os.getenv("DB_POOL_MAX", "50")),
    )

    pool = None  # HATA 12 FIX: track pool separately so finally can close it
    try:
        # Initialize pool
        pool = await config.initialize()

        # Create indices
        indexing = IndexingStrategy()
        results = await indexing.create_all_indices(pool)

        success_count = sum(1 for v in results.values() if v)
        logger.info("✅ Database initialized successfully")
        logger.info(f"✅ Indices created: {success_count}/{len(results)}")

        return True

    except Exception as e:
        logger.error(f"❌ Database initialization failed: {str(e)}")
        raise

    finally:
        # Ensure pool is closed even when an exception occurs  # HATA 12 FIX
        if pool:
            try:
                await config.close()
            except Exception as e:
                logger.warning(f"Error closing pool: {str(e)}")


if __name__ == "__main__":
    asyncio.run(initialize_database())
