"""Simple database migration runner."""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Dict, List

import asyncpg

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

migrations: List[Dict[str, str]] = [
    {
        "version": "001_create_users_index",
        "description": "Create supporting users created_at index",
        "sql": "CREATE INDEX IF NOT EXISTS idx_users_created_at ON users (created_at)",
    },
    {
        "version": "002_create_sessions_user_index",
        "description": "Create sessions user_id index",
        "sql": "CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions (user_id)",
    },
]


def _db_config() -> Dict[str, Any]:
    """Build database connection settings from environment variables."""
    config: Dict[str, Any] = {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": int(os.getenv("DB_PORT", "5432")),
        "user": os.getenv("DB_USER", "postgres"),
        "database": os.getenv("DB_NAME", "advanced_ai"),
    }
    config["password"] = os.getenv("DB_PASSWORD", "postgres")
    return config


async def run_migrations() -> None:
    """Run any unapplied migrations and record their execution."""
    connection: asyncpg.Connection | None = None
    try:
        connection = await asyncpg.connect(**_db_config())
        await connection.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version VARCHAR PRIMARY KEY,
                description VARCHAR NOT NULL,
                applied_at TIMESTAMP DEFAULT NOW()
            )
            """
        )
        applied_rows = await connection.fetch("SELECT version FROM schema_migrations")
        applied_versions = {row["version"] for row in applied_rows}
        for migration in migrations:
            if migration["version"] in applied_versions:
                continue
            async with connection.transaction():
                await connection.execute(migration["sql"])
                await connection.execute(
                    "INSERT INTO schema_migrations (version, description) VALUES ($1, $2)",
                    migration["version"],
                    migration["description"],
                )
                logger.info("Applied migration %s", migration["version"])
    except Exception as exc:
        logger.exception("Migration execution failed: %s", exc)
        raise
    finally:
        if connection is not None:
            await connection.close()


if __name__ == "__main__":
    asyncio.run(run_migrations())
