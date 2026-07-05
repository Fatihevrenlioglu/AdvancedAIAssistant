import json
import unittest

from src.cache.redis_cache import RedisCache
from src.core.error_handler import ErrorCode, StandardError
from src.database.connection_pool_config import ConnectionPoolConfig
from src.database.indexing_strategy import IndexingStrategy
from src.services.global_rate_limiter import GlobalRateLimiter


class FakePoolContext:
    def __init__(self, connection):
        self.connection = connection

    async def __aenter__(self):
        return self.connection

    async def __aexit__(self, exc_type, exc, tb):
        return False


class FakeConnection:
    def __init__(self):
        self.executed = []
        self.fetch_calls = []

    async def execute(self, query):
        self.executed.append(query)

    async def fetchrow(self, query, *args):
        self.fetch_calls.append((query, args))
        return {"size": "42 kB", "row_count": 7}

    async def fetch(self, query, *args):
        self.fetch_calls.append((query, args))
        if "FROM pg_indexes" in query:
            return [{"indexname": "idx_tasks_user_id"}]
        return [{"query": "SELECT 1", "duration_ms": 1200, "row_count": 1, "timestamp": "2026-01-01T00:00:00Z"}]


class FakePool:
    def __init__(self, connection):
        self.connection = connection

    def acquire(self):
        return FakePoolContext(self.connection)


class FakeMetricsPool(FakePool):
    def get_size(self):
        return 8

    def get_idle_size(self):
        return 3

    def get_max_size(self):
        return 10

    def get_min_size(self):
        return 2


class FakeRedis:
    def __init__(self):
        self.values = {}
        self.expirations = {}

    async def get(self, key):
        return self.values.get(key)

    async def setex(self, key, ttl, value):
        self.values[key] = value
        self.expirations[key] = ttl

    async def delete(self, *keys):
        for key in keys:
            self.values.pop(key, None)
        return len(keys)

    async def scan_iter(self, match=None):
        prefix = match.rstrip("*") if match else ""
        for key in list(self.values.keys()):
            if not match or key.startswith(prefix):
                yield key

    async def incr(self, key):
        self.values[key] = int(self.values.get(key, 0)) + 1
        return self.values[key]

    async def expire(self, key, ttl):
        self.expirations[key] = ttl


class Phase1InfrastructureTests(unittest.IsolatedAsyncioTestCase):
    async def test_indexing_strategy_creates_and_analyzes_indices(self):
        connection = FakeConnection()
        strategy = IndexingStrategy()
        pool = FakePool(connection)

        results = await strategy.create_all_indices(pool)
        analysis = await strategy.analyze_table_performance(pool, "tasks")
        slow_queries = await strategy.get_slow_queries_from_logs(pool)

        self.assertTrue(all(results.values()))
        self.assertEqual(len(connection.executed), sum(len(indices) for indices in strategy.INDICES.values()))
        self.assertEqual(analysis["table"], "tasks")
        self.assertEqual(analysis["indices"], ["idx_tasks_user_id"])
        self.assertEqual(slow_queries[0]["duration_ms"], 1200)

    async def test_connection_pool_status_reports_utilization(self):
        config = ConnectionPoolConfig("localhost", 5432, "postgres", "postgres", "advanced_ai")
        config.pool = FakeMetricsPool(FakeConnection())

        status = await config.get_pool_status()

        self.assertEqual(status["size"], 8)
        self.assertEqual(status["idle"], 3)
        self.assertEqual(status["utilization_percent"], 50.0)

    async def test_redis_cache_and_rate_limiter_track_state(self):
        redis = FakeRedis()
        cache = RedisCache(redis)
        limiter = GlobalRateLimiter(redis, requests_per_minute=2, requests_per_hour=3)

        self.assertTrue(await cache.set("user:1", {"name": "Ada"}, ttl=30))
        self.assertEqual(await cache.get("user:1"), {"name": "Ada"})
        self.assertEqual(await cache.get("missing", default={}), {})
        self.assertEqual(await cache.clear_pattern("user:*"), 1)
        self.assertEqual(cache.get_statistics()["hit_rate_percent"], 50.0)

        allowed, details = await limiter.check_rate_limit("42")
        self.assertTrue(allowed)
        self.assertEqual(details["remaining_minute"], 1)

        await limiter.check_rate_limit("42")
        blocked, details = await limiter.check_rate_limit("42")
        self.assertFalse(blocked)
        self.assertEqual(details["window"], "minute")

    async def test_standard_error_serializes_response(self):
        response = StandardError(
            code=ErrorCode.DATABASE_ERROR,
            message="Database operation failed",
            status_code=500,
            details={"error": "boom"},
            request_id="req-1",
        ).to_response()

        body = json.loads(response.body)

        self.assertEqual(response.status_code, 500)
        self.assertEqual(body["error"]["code"], ErrorCode.DATABASE_ERROR.value)
        self.assertEqual(body["request_id"], "req-1")
        self.assertIn("timestamp", body)
