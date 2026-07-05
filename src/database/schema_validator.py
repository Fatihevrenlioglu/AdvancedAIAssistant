import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


class SchemaValidator:
    """Ensure the core database schema exists before runtime operations."""

    TABLE_SCHEMAS = {
        "tasks": """
            CREATE TABLE IF NOT EXISTS tasks (
                id BIGSERIAL PRIMARY KEY,
                user_id TEXT NOT NULL,
                status TEXT NOT NULL,
                payload JSONB DEFAULT '{}'::jsonb,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """,
        "decisions": """
            CREATE TABLE IF NOT EXISTS decisions (
                id BIGSERIAL PRIMARY KEY,
                task_id BIGINT REFERENCES tasks(id) ON DELETE CASCADE,
                user_id TEXT NOT NULL,
                decision TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """,
        "errors": """
            CREATE TABLE IF NOT EXISTS errors (
                id BIGSERIAL PRIMARY KEY,
                task_id BIGINT REFERENCES tasks(id) ON DELETE SET NULL,
                error_type TEXT NOT NULL,
                message TEXT NOT NULL,
                recovered BOOLEAN NOT NULL DEFAULT FALSE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """,
        "audit_logs": """
            CREATE TABLE IF NOT EXISTS audit_logs (
                id BIGSERIAL PRIMARY KEY,
                user_id TEXT NOT NULL,
                action TEXT NOT NULL,
                metadata JSONB DEFAULT '{}'::jsonb,
                timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """,
        "sessions": """
            CREATE TABLE IF NOT EXISTS sessions (
                id BIGSERIAL PRIMARY KEY,
                user_id TEXT NOT NULL,
                session_token TEXT NOT NULL UNIQUE,
                expires_at TIMESTAMPTZ NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """,
        "query_logs": """
            CREATE TABLE IF NOT EXISTS query_logs (
                id BIGSERIAL PRIMARY KEY,
                query TEXT NOT NULL,
                duration_ms DOUBLE PRECISION NOT NULL,
                row_count INTEGER NOT NULL DEFAULT 0,
                timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """,
    }

    async def validate_schema(self, db_pool: Any) -> Dict[str, bool]:
        """Create core tables when they do not exist yet."""
        results: Dict[str, bool] = {}

        for table_name, statement in self.TABLE_SCHEMAS.items():
            try:
                async with db_pool.acquire() as connection:
                    await connection.execute(statement)
                results[table_name] = True
                logger.info("✅ Schema ready: %s", table_name)
            except Exception as exc:  # pragma: no cover - defensive logging path
                results[table_name] = False
                logger.error("❌ Failed to validate schema for %s: %s", table_name, exc)

        return results
