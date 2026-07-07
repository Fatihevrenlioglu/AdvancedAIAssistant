"""Initialize application database tables."""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Dict

import asyncpg

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TABLE_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        email VARCHAR UNIQUE NOT NULL,
        username VARCHAR NOT NULL,
        password_hash VARCHAR NOT NULL,
        created_at TIMESTAMP DEFAULT NOW(),
        is_active BOOLEAN DEFAULT TRUE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS sessions (
        id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES users(id),
        token_hash VARCHAR NOT NULL,
        created_at TIMESTAMP DEFAULT NOW(),
        expires_at TIMESTAMP NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS audit_logs (
        id SERIAL PRIMARY KEY,
        event_type VARCHAR NOT NULL,
        user_id INTEGER,
        resource VARCHAR,
        action VARCHAR,
        success BOOLEAN,
        details JSONB,
        created_at TIMESTAMP DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS api_requests (
        id SERIAL PRIMARY KEY,
        method VARCHAR,
        path VARCHAR,
        status_code INTEGER,
        duration_ms FLOAT,
        created_at TIMESTAMP DEFAULT NOW(),
        request_id VARCHAR
    )
    """,
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


async def initialize_database() -> None:
    """Create required application tables when they do not already exist."""
    connection: asyncpg.Connection | None = None
    try:
        connection = await asyncpg.connect(**_db_config())
        for statement in TABLE_STATEMENTS:
            await connection.execute(statement)
        logger.info("Database initialization completed successfully.")
    except Exception as exc:
        logger.exception("Database initialization failed: %s", exc)
        raise
    finally:
        if connection is not None:
            await connection.close()


if __name__ == "__main__":
    asyncio.run(initialize_database())
