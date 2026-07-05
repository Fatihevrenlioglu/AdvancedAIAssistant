import logging
from typing import List, Dict, Optional  # HATA 1 FIX: added List, Dict, Optional imports

logger = logging.getLogger(__name__)


class IndexingStrategy:
    """Manages database indexing strategies for performance optimization."""

    INDICES: Dict[str, List[str]] = {
        "users": [
            "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)",
            "CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at)",
        ],
        "conversations": [
            "CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_conversations_created_at ON conversations(created_at)",
        ],
        "messages": [
            "CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id)",
            "CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at)",
        ],
        "code_generations": [
            "CREATE INDEX IF NOT EXISTS idx_code_gen_user_id ON code_generations(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_code_gen_created_at ON code_generations(created_at)",
        ],
    }

    async def create_index(self, db_pool, index_sql: str) -> bool:
        """Execute a single CREATE INDEX statement."""
        try:
            async with db_pool.acquire() as connection:
                await connection.execute(index_sql)
                logger.info(f"✅ Index created: {index_sql[:60]}...")
                return True
        except Exception as e:
            logger.error(f"❌ Failed to create index: {str(e)}")
            return False

    async def create_all_indices(self, db_pool) -> Dict[str, bool]:
        """Create all defined indices and return a result map."""
        results: Dict[str, bool] = {}
        for table, index_list in self.INDICES.items():
            for sql in index_list:
                try:
                    key = sql.split("idx_")[1].split(" ")[0] if "idx_" in sql else sql[:40]
                except IndexError:
                    key = sql[:40]
                results[key] = await self.create_index(db_pool, sql)
        return results

    async def analyze_table_performance(self, db_pool, table_name: str) -> Dict:
        """Analyze table performance.

        HATA 7 FIX: validate table_name against whitelist before use to prevent
        SQL injection; use parameterized query for the WHERE clause.
        """
        # Validate table name (prevent SQL injection)  # HATA 7 FIX
        valid_tables = list(self.INDICES.keys())
        if table_name not in valid_tables:
            raise ValueError(f"Invalid table name: {table_name}")

        try:
            async with db_pool.acquire() as connection:
                # Use parameterized query for WHERE clause  # HATA 7 FIX
                size_result = await connection.fetch(
                    """
                    SELECT
                        pg_size_pretty(pg_total_relation_size($1)) as size,
                        reltuples::bigint as row_count
                    FROM pg_class
                    WHERE relname = $1
                    """,
                    table_name,
                )

                return {
                    "table": table_name,
                    "size": size_result[0]["size"] if size_result else "N/A",
                    "row_count": size_result[0]["row_count"] if size_result else 0,
                }
        except Exception as e:
            logger.error(f"Failed to analyze table {table_name}: {str(e)}")
            return {}

    async def get_slow_queries_from_logs(self, db_pool) -> List[Dict]:
        """Retrieve slow queries from pg_stat_statements."""
        try:
            async with db_pool.acquire() as connection:
                rows = await connection.fetch(
                    """
                    SELECT
                        query,
                        calls,
                        total_exec_time,
                        mean_exec_time,
                        rows
                    FROM pg_stat_statements
                    ORDER BY mean_exec_time DESC
                    LIMIT 20
                    """
                )
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to fetch slow queries: {str(e)}")
            return []
