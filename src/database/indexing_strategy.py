import logging
import re
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class IndexingStrategy:
    """Database indexing for performance optimization."""

    INDICES = {
        "tasks": [
            {"columns": ["user_id"], "unique": False, "name": "idx_tasks_user_id"},
            {"columns": ["status"], "unique": False, "name": "idx_tasks_status"},
            {"columns": ["created_at"], "unique": False, "name": "idx_tasks_created_at"},
            {"columns": ["user_id", "status"], "unique": False, "name": "idx_tasks_user_status"},
            {"columns": ["updated_at"], "unique": False, "name": "idx_tasks_updated_at"},
        ],
        "decisions": [
            {"columns": ["task_id"], "unique": False, "name": "idx_decisions_task_id"},
            {"columns": ["user_id"], "unique": False, "name": "idx_decisions_user_id"},
            {"columns": ["created_at"], "unique": False, "name": "idx_decisions_created_at"},
            {"columns": ["task_id", "user_id"], "unique": False, "name": "idx_decisions_task_user"},
        ],
        "errors": [
            {"columns": ["task_id"], "unique": False, "name": "idx_errors_task_id"},
            {"columns": ["error_type"], "unique": False, "name": "idx_errors_type"},
            {"columns": ["created_at"], "unique": False, "name": "idx_errors_created_at"},
            {"columns": ["recovered"], "unique": False, "name": "idx_errors_recovered"},
        ],
        "audit_logs": [
            {"columns": ["user_id"], "unique": False, "name": "idx_audit_user_id"},
            {"columns": ["action"], "unique": False, "name": "idx_audit_action"},
            {"columns": ["timestamp"], "unique": False, "name": "idx_audit_timestamp"},
            {"columns": ["user_id", "timestamp"], "unique": False, "name": "idx_audit_user_time"},
        ],
        "sessions": [
            {"columns": ["user_id"], "unique": False, "name": "idx_sessions_user_id"},
            {"columns": ["expires_at"], "unique": False, "name": "idx_sessions_expires_at"},
        ],
    }

    @staticmethod
    def _quote_identifier(identifier: str) -> str:
        if not _IDENTIFIER_RE.match(identifier):
            raise ValueError(f"Invalid SQL identifier: {identifier}")
        return f'"{identifier}"'

    async def create_all_indices(self, db_pool: Any) -> Dict[str, bool]:
        """Create all configured indices."""
        results: Dict[str, bool] = {}

        for table_name, indices in self.INDICES.items():
            quoted_table = self._quote_identifier(table_name)
            for index_def in indices:
                index_name = index_def["name"]
                try:
                    columns = ", ".join(self._quote_identifier(column) for column in index_def["columns"])
                    unique = "UNIQUE " if index_def["unique"] else ""
                    query = (
                        f"CREATE {unique}INDEX IF NOT EXISTS {self._quote_identifier(index_name)} "
                        f"ON {quoted_table} ({columns})"
                    )
                    async with db_pool.acquire() as connection:
                        await connection.execute(query)
                    results[index_name] = True
                    logger.info("✅ Index created: %s", index_name)
                except Exception as exc:  # pragma: no cover - defensive logging path
                    results[index_name] = False
                    logger.error("❌ Failed to create index %s: %s", index_name, exc)

        return results

    async def analyze_table_performance(self, db_pool: Any, table_name: str) -> Dict[str, Any]:
        """Analyze table size, row count, and index coverage."""
        if table_name not in self.INDICES:
            raise ValueError(f"Unsupported table for analysis: {table_name}")

        try:
            async with db_pool.acquire() as connection:
                size_result = await connection.fetchrow(
                    """
                    SELECT
                        pg_size_pretty(pg_total_relation_size($1::regclass)) AS size,
                        COALESCE(reltuples::bigint, 0) AS row_count
                    FROM pg_class
                    WHERE relname = $1
                    """,
                    table_name,
                )
                index_result = await connection.fetch(
                    """
                    SELECT indexname, indexdef
                    FROM pg_indexes
                    WHERE tablename = $1
                    ORDER BY indexname
                    """,
                    table_name,
                )
        except Exception as exc:  # pragma: no cover - defensive logging path
            logger.error("Failed to analyze table %s: %s", table_name, exc)
            return {}

        return {
            "table": table_name,
            "size": size_result["size"] if size_result else "N/A",
            "row_count": size_result["row_count"] if size_result else 0,
            "indices": [index["indexname"] for index in index_result],
        }

    async def get_slow_queries_from_logs(self, db_pool: Any) -> List[Dict[str, Any]]:
        """Get the slowest recorded queries from query_logs."""
        try:
            async with db_pool.acquire() as connection:
                rows = await connection.fetch(
                    """
                    SELECT query, duration_ms, row_count, timestamp
                    FROM query_logs
                    WHERE duration_ms > 1000
                    ORDER BY duration_ms DESC
                    LIMIT 20
                    """
                )
        except Exception as exc:  # pragma: no cover - defensive logging path
            logger.error("Failed to get slow queries: %s", exc)
            return []

        return [dict(row) for row in rows]
