"""Tests for database helpers."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import asyncpg
import pytest

from src.database.connection_pool_config import ConnectionPoolConfig
from src.database.retry_manager import RetryManager
from src.database.schema_validator import SchemaValidator
from src.database.transaction_manager import TransactionManager


class MockAcquire:
    """Async context manager for mocked pool.acquire calls."""

    def __init__(self, connection: AsyncMock) -> None:
        self.connection = connection

    async def __aenter__(self) -> AsyncMock:
        return self.connection

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None


@pytest.mark.asyncio
async def test_connection_pool_config_defaults() -> None:
    """ConnectionPoolConfig should expose documented defaults."""
    config = ConnectionPoolConfig()
    assert config.host == "localhost"
    assert config.port == 5432
    assert config.database == "advanced_ai"
    assert config.command_timeout == 60.0


@pytest.mark.asyncio
async def test_retry_manager_execute_with_retry_success() -> None:
    """RetryManager should return successful query results."""
    connection = AsyncMock()
    connection.fetch.return_value = [{"id": 1}]
    pool = SimpleNamespace(acquire=lambda: MockAcquire(connection))

    result = await RetryManager.execute_with_retry(pool, "SELECT 1")
    assert result == [{"id": 1}]
    connection.fetch.assert_awaited_once()


@pytest.mark.asyncio
async def test_retry_manager_execute_with_retry_retries_then_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    """RetryManager should retry transient errors."""
    connection = AsyncMock()
    connection.fetch.side_effect = [asyncpg.PostgresConnectionError("boom"), [{"ok": True}]]
    pool = SimpleNamespace(acquire=lambda: MockAcquire(connection))

    sleep_calls: list[float] = []

    async def fake_sleep(delay: float) -> None:
        sleep_calls.append(delay)

    monkeypatch.setattr("src.database.retry_manager.asyncio.sleep", fake_sleep)
    result = await RetryManager.execute_with_retry(pool, "SELECT 1", max_retries=2, base_delay=0.1)
    assert result == [{"ok": True}]
    assert sleep_calls == [0.1]


@pytest.mark.asyncio
async def test_retry_manager_execute_with_retry_max_retries_exceeded() -> None:
    """RetryManager should raise after max retries are exhausted."""
    connection = AsyncMock()
    connection.fetch.side_effect = asyncpg.PostgresConnectionError("boom")
    pool = SimpleNamespace(acquire=lambda: MockAcquire(connection))

    with pytest.raises(asyncpg.PostgresConnectionError):
        await RetryManager.execute_with_retry(pool, "SELECT 1", max_retries=1, base_delay=0)


@pytest.mark.asyncio
async def test_schema_validator_methods() -> None:
    """SchemaValidator should query information_schema helpers."""
    connection = AsyncMock()
    connection.fetchval.side_effect = [True, True]
    connection.fetch.return_value = [{"column_name": "id", "data_type": "integer"}]
    pool = SimpleNamespace(acquire=lambda: MockAcquire(connection))

    assert await SchemaValidator.validate_table_exists(pool, "users") is True
    assert await SchemaValidator.validate_column_exists(pool, "users", "id") is True
    schema = await SchemaValidator.get_table_schema(pool, "users")
    assert schema == [{"column_name": "id", "data_type": "integer"}]


@pytest.mark.asyncio
async def test_transaction_manager_execute_transaction_success() -> None:
    """TransactionManager should commit on success."""
    transaction = AsyncMock()
    connection = AsyncMock()
    connection.transaction.return_value = transaction
    pool = SimpleNamespace(acquire=lambda: MockAcquire(connection))

    result = await TransactionManager.execute_transaction(
        pool,
        [("INSERT INTO users VALUES ($1)", (1,)), ("DELETE FROM users WHERE id = $1", (1,))],
    )
    assert result is True
    transaction.start.assert_awaited_once()
    transaction.commit.assert_awaited_once()
    transaction.rollback.assert_not_called()


@pytest.mark.asyncio
async def test_transaction_manager_execute_transaction_rollback() -> None:
    """TransactionManager should roll back on errors."""
    transaction = AsyncMock()
    connection = AsyncMock()
    connection.transaction.return_value = transaction
    connection.execute.side_effect = RuntimeError("query failed")
    pool = SimpleNamespace(acquire=lambda: MockAcquire(connection))

    with pytest.raises(RuntimeError):
        await TransactionManager.execute_transaction(pool, [("INSERT INTO users VALUES ($1)", (1,))])

    transaction.rollback.assert_awaited_once()
