"""
Tests for Dynamic Query Service.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime, date
from decimal import Decimal

from app.services.dynamic_query_service import DynamicQueryService, QueryResult


class TestDynamicQueryService:
    """Test suite for DynamicQueryService."""

    @pytest.fixture
    def database_url(self):
        """Mock database URL."""
        return "postgresql://user:pass@localhost:5432/testdb"

    @pytest.fixture
    def service(self, database_url):
        """Create service instance."""
        return DynamicQueryService(
            database_url=database_url,
            min_pool_size=1,
            max_pool_size=2,
            query_timeout=5.0,
            max_rows=100
        )

    def _create_mock_pool(self, mock_conn):
        """Helper to create properly mocked pool and connection."""
        mock_pool = MagicMock()
        mock_acquire = MagicMock()
        mock_acquire.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_acquire.__aexit__ = AsyncMock(return_value=None)
        mock_pool.acquire = MagicMock(return_value=mock_acquire)
        return mock_pool

    def test_initialization(self, service):
        """Test service initialization."""
        assert service.database_url is not None
        assert service.min_pool_size == 1
        assert service.max_pool_size == 2
        assert service.query_timeout == 5.0
        assert service.max_rows == 100
        assert service.pool is None  # Not initialized yet

    @pytest.mark.asyncio
    async def test_format_row_with_datetime(self, service):
        """Test row formatting with datetime."""
        row = {
            "id": 1,
            "created_at": datetime(2024, 1, 15, 10, 30, 45),
            "date_field": date(2024, 1, 15)
        }

        formatted = service._format_row(row)

        assert formatted["id"] == 1
        assert formatted["created_at"] == "2024-01-15T10:30:45"
        assert formatted["date_field"] == "2024-01-15"

    @pytest.mark.asyncio
    async def test_format_row_with_decimal(self, service):
        """Test row formatting with Decimal."""
        row = {
            "id": 1,
            "amount": Decimal("123.45")
        }

        formatted = service._format_row(row)

        assert formatted["id"] == 1
        assert formatted["amount"] == 123.45
        assert isinstance(formatted["amount"], float)

    @pytest.mark.asyncio
    async def test_format_row_with_null(self, service):
        """Test row formatting with NULL values."""
        row = {
            "id": 1,
            "optional_field": None
        }

        formatted = service._format_row(row)

        assert formatted["id"] == 1
        assert formatted["optional_field"] is None

    @pytest.mark.asyncio
    async def test_format_row_with_binary(self, service):
        """Test row formatting with binary data."""
        row = {
            "id": 1,
            "binary_data": b"binary content"
        }

        formatted = service._format_row(row)

        assert formatted["id"] == 1
        assert formatted["binary_data"] == "<binary data>"

    @pytest.mark.asyncio
    async def test_format_row_with_json(self, service):
        """Test row formatting with JSON data."""
        row = {
            "id": 1,
            "json_data": {"key": "value"},
            "array_data": [1, 2, 3]
        }

        formatted = service._format_row(row)

        assert formatted["id"] == 1
        assert formatted["json_data"] == {"key": "value"}
        assert formatted["array_data"] == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_execute_query_without_pool(self, service):
        """Test query execution without initialized pool."""
        result = await service.execute_query("SELECT 1")

        assert not result.success
        assert "not initialized" in result.error_message

    @pytest.mark.asyncio
    async def test_execute_query_success(self, service):
        """Test successful query execution."""
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value=None)
        mock_conn.fetch = AsyncMock(return_value=[{"id": 1, "name": "test"}])

        service.pool = self._create_mock_pool(mock_conn)

        result = await service.execute_query("SELECT * FROM test")

        assert result.success
        assert result.row_count == 1
        assert len(result.rows) == 1
        assert result.rows[0]["id"] == 1
        assert result.columns == ["id", "name"]
        assert result.execution_time_ms > 0

    @pytest.mark.asyncio
    async def test_execute_query_empty_result(self, service):
        """Test query execution with empty result."""
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value=None)
        mock_conn.fetch = AsyncMock(return_value=[])

        service.pool = self._create_mock_pool(mock_conn)

        result = await service.execute_query("SELECT * FROM test WHERE 1=0")

        assert result.success
        assert result.row_count == 0
        assert result.rows == []
        assert result.columns == []

    @pytest.mark.asyncio
    async def test_execute_query_max_rows_limit(self, service):
        """Test query execution with max rows limit."""
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value=None)
        # Return more rows than max_rows limit
        mock_rows = [{"id": i, "name": f"test{i}"} for i in range(150)]
        mock_conn.fetch = AsyncMock(return_value=mock_rows)

        service.pool = self._create_mock_pool(mock_conn)
        service.max_rows = 100

        result = await service.execute_query("SELECT * FROM test")

        assert result.success
        assert result.row_count == 100  # Truncated
        assert len(result.rows) == 100

    @pytest.mark.asyncio
    async def test_execute_query_timeout(self, service):
        """Test query execution timeout."""
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value=None)

        # Simulate slow query
        async def slow_fetch(*args):
            await asyncio.sleep(10)
            return []

        mock_conn.fetch = slow_fetch

        service.pool = self._create_mock_pool(mock_conn)
        service.query_timeout = 0.1  # Very short timeout

        result = await service.execute_query("SELECT * FROM test")

        assert not result.success
        assert "timeout" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_execute_query_database_error(self, service):
        """Test query execution with database error."""
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value=None)

        # Simulate database error
        import asyncpg
        mock_conn.fetch = AsyncMock(side_effect=asyncpg.PostgresError("Syntax error"))

        service.pool = self._create_mock_pool(mock_conn)

        result = await service.execute_query("SELECT * FORM test")  # Typo

        assert not result.success
        assert "Database error" in result.error_message

    @pytest.mark.asyncio
    async def test_execute_query_with_custom_timeout(self, service):
        """Test query execution with custom timeout."""
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value=None)
        mock_conn.fetch = AsyncMock(return_value=[])

        service.pool = self._create_mock_pool(mock_conn)

        # Execute with custom timeout
        result = await service.execute_query("SELECT * FROM test", timeout=10.0)

        assert result.success

    @pytest.mark.asyncio
    async def test_query_result_to_dict(self):
        """Test QueryResult to_dict conversion."""
        result = QueryResult(
            success=True,
            rows=[{"id": 1, "name": "test"}],
            row_count=1,
            columns=["id", "name"],
            execution_time_ms=123.45
        )

        result_dict = result.to_dict()

        assert result_dict["success"] is True
        assert result_dict["data"] == [{"id": 1, "name": "test"}]
        assert result_dict["row_count"] == 1
        assert result_dict["columns"] == ["id", "name"]
        assert result_dict["execution_time_ms"] == 123.45
        assert result_dict["error"] is None

    @pytest.mark.asyncio
    async def test_query_result_to_dict_with_error(self):
        """Test QueryResult to_dict with error."""
        result = QueryResult(
            success=False,
            error_message="Query failed"
        )

        result_dict = result.to_dict()

        assert result_dict["success"] is False
        assert result_dict["error"] == "Query failed"

    @pytest.mark.asyncio
    async def test_test_connection_success(self, service):
        """Test successful connection test."""
        mock_conn = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value=1)

        service.pool = self._create_mock_pool(mock_conn)

        is_connected = await service.test_connection()

        assert is_connected is True

    @pytest.mark.asyncio
    async def test_test_connection_failure(self, service):
        """Test failed connection test."""
        mock_conn = AsyncMock()
        mock_conn.fetchval = AsyncMock(side_effect=Exception("Connection failed"))

        service.pool = self._create_mock_pool(mock_conn)

        is_connected = await service.test_connection()

        assert is_connected is False

    @pytest.mark.asyncio
    async def test_get_table_info_success(self, service):
        """Test getting table info."""
        mock_conn = AsyncMock()

        # Mock table info query result
        mock_conn.fetch = AsyncMock(return_value=[
            {
                "column_name": "id",
                "data_type": "integer",
                "is_nullable": "NO",
                "column_default": "nextval('test_id_seq'::regclass)"
            },
            {
                "column_name": "name",
                "data_type": "character varying",
                "is_nullable": "YES",
                "column_default": None
            }
        ])

        service.pool = self._create_mock_pool(mock_conn)

        table_info = await service.get_table_info("test_table")

        assert table_info is not None
        assert table_info["table_name"] == "test_table"
        assert table_info["column_count"] == 2
        assert len(table_info["columns"]) == 2
        assert table_info["columns"][0]["name"] == "id"
        assert table_info["columns"][0]["nullable"] is False
        assert table_info["columns"][1]["name"] == "name"
        assert table_info["columns"][1]["nullable"] is True

    @pytest.mark.asyncio
    async def test_get_table_info_failure(self, service):
        """Test getting table info failure."""
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(side_effect=Exception("Table not found"))

        service.pool = self._create_mock_pool(mock_conn)

        table_info = await service.get_table_info("nonexistent")

        assert table_info is None

    @pytest.mark.asyncio
    async def test_context_manager(self, database_url):
        """Test async context manager."""
        with patch('asyncpg.create_pool', new_callable=AsyncMock) as mock_create_pool:
            mock_pool = AsyncMock()
            mock_create_pool.return_value = mock_pool

            async with DynamicQueryService(database_url) as service:
                assert service.pool is not None

            # Pool should be closed after exiting context
            mock_pool.close.assert_called_once()


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
