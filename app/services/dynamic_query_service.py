"""
Dynamic Query Service for executing validated SQL queries.

This service handles:
- Executing SQL queries against PostgreSQL database
- Connection pooling with asyncpg
- Query timeout handling
- Result formatting and serialization
- Error handling
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, date
from decimal import Decimal
from dataclasses import dataclass

import asyncpg


logger = logging.getLogger(__name__)


@dataclass
class QueryResult:
    """Result of a database query execution."""
    success: bool
    rows: Optional[List[Dict[str, Any]]] = None
    row_count: int = 0
    columns: Optional[List[str]] = None
    execution_time_ms: float = 0
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "success": self.success,
            "data": self.rows,
            "row_count": self.row_count,
            "columns": self.columns,
            "execution_time_ms": round(self.execution_time_ms, 2),
            "error": self.error_message
        }


class DynamicQueryService:
    """
    Service for executing dynamic SQL queries.

    This service provides safe query execution with:
    - Connection pooling for performance
    - Query timeouts to prevent long-running queries
    - Automatic result formatting and JSON serialization
    - Comprehensive error handling
    """

    def __init__(
        self,
        database_url: str,
        min_pool_size: int = 2,
        max_pool_size: int = 10,
        query_timeout: float = 30.0,
        max_rows: int = 10000
    ):
        """
        Initialize dynamic query service.

        Args:
            database_url: PostgreSQL connection URL
            min_pool_size: Minimum number of connections in pool
            max_pool_size: Maximum number of connections in pool
            query_timeout: Query timeout in seconds
            max_rows: Maximum number of rows to return
        """
        self.database_url = database_url
        self.min_pool_size = min_pool_size
        self.max_pool_size = max_pool_size
        self.query_timeout = query_timeout
        self.max_rows = max_rows
        self.pool: Optional[asyncpg.Pool] = None

        logger.info(
            f"DynamicQueryService initialized: "
            f"pool_size={min_pool_size}-{max_pool_size}, "
            f"timeout={query_timeout}s, max_rows={max_rows}"
        )

    async def initialize(self):
        """Initialize database connection pool."""
        if self.pool is not None:
            logger.warning("Connection pool already initialized")
            return

        try:
            self.pool = await asyncpg.create_pool(
                self.database_url,
                min_size=self.min_pool_size,
                max_size=self.max_pool_size,
                command_timeout=self.query_timeout
            )
            logger.info("Database connection pool created successfully")
        except Exception as e:
            logger.error(f"Failed to create connection pool: {str(e)}", exc_info=True)
            raise

    async def close(self):
        """Close database connection pool."""
        if self.pool is not None:
            await self.pool.close()
            self.pool = None
            logger.info("Database connection pool closed")

    async def execute_query(
        self,
        sql: str,
        timeout: Optional[float] = None
    ) -> QueryResult:
        """
        Execute a SQL query and return formatted results.

        Args:
            sql: SQL query to execute (must be SELECT only)
            timeout: Optional query timeout override (seconds)

        Returns:
            QueryResult with query results or error
        """
        if self.pool is None:
            return QueryResult(
                success=False,
                error_message="Database connection pool not initialized"
            )

        # Fix PostgreSQL 9.6 ROUND syntax compatibility issue
        # Claude sometimes forgets to add ::numeric cast
        sql = self._fix_postgresql_round_syntax(sql)

        # Fix PostgreSQL 9.6 UNION ORDER BY compatibility issue
        # PG 9.6 doesn't allow expressions in ORDER BY after UNION
        sql = self._fix_union_order_by_syntax(sql)

        timeout = timeout or self.query_timeout
        start_time = asyncio.get_event_loop().time()

        try:
            logger.debug(f"Executing query: {sql[:200]}...")

            # Execute query with timeout
            async with asyncio.timeout(timeout):
                async with self.pool.acquire() as conn:
                    # Set transaction to read-only for safety
                    await conn.execute("SET TRANSACTION READ ONLY")

                    # Execute query
                    rows = await conn.fetch(sql)

            # Calculate execution time
            execution_time_ms = (asyncio.get_event_loop().time() - start_time) * 1000

            # Check row count limit
            if len(rows) > self.max_rows:
                logger.warning(
                    f"Query returned {len(rows)} rows, "
                    f"truncating to {self.max_rows}"
                )
                rows = rows[:self.max_rows]

            # Format results
            formatted_rows = [self._format_row(dict(row)) for row in rows]
            columns = list(rows[0].keys()) if rows else []

            logger.info(
                f"Query executed successfully: "
                f"{len(formatted_rows)} rows in {execution_time_ms:.2f}ms"
            )

            return QueryResult(
                success=True,
                rows=formatted_rows,
                row_count=len(formatted_rows),
                columns=columns,
                execution_time_ms=execution_time_ms
            )

        except asyncio.TimeoutError:
            execution_time_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            logger.error(f"Query timeout after {timeout}s")
            return QueryResult(
                success=False,
                execution_time_ms=execution_time_ms,
                error_message=f"Query timeout after {timeout} seconds"
            )

        except asyncpg.PostgresError as e:
            execution_time_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            logger.error(f"PostgreSQL error: {str(e)}", exc_info=True)
            return QueryResult(
                success=False,
                execution_time_ms=execution_time_ms,
                error_message=f"Database error: {str(e)}"
            )

        except Exception as e:
            execution_time_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            logger.error(f"Query execution error: {str(e)}", exc_info=True)
            return QueryResult(
                success=False,
                execution_time_ms=execution_time_ms,
                error_message=f"Internal error: {str(e)}"
            )

    def _fix_postgresql_round_syntax(self, sql: str) -> str:
        """
        Fix PostgreSQL 9.6 ROUND function syntax compatibility.

        PostgreSQL 9.6 requires explicit type casting for ROUND with precision:
        - Wrong: ROUND(EXTRACT(EPOCH FROM ...), 2)
        - Correct: ROUND(EXTRACT(EPOCH FROM ...)::numeric, 2)

        Also handles cases like ROUND(AVG(EXTRACT(EPOCH FROM ...)), 2)

        Args:
            sql: Original SQL query

        Returns:
            Fixed SQL query
        """
        import re

        # Strategy: Find all EXTRACT(EPOCH FROM ...) and add ::numeric if not present
        # This works regardless of whether it's inside AVG, MAX, ROUND, etc.

        def add_numeric_cast(match):
            """Add ::numeric cast to EXTRACT(EPOCH FROM ...) if not present"""
            full_match = match.group(0)

            # Check if already has cast
            if '::numeric' in full_match.lower():
                return full_match

            # Add ::numeric before the closing parenthesis of EXTRACT
            # Pattern: EXTRACT(EPOCH FROM (...)) -> EXTRACT(EPOCH FROM (...))::numeric
            return full_match + '::numeric'

        # Pattern to match: EXTRACT(EPOCH FROM (...))
        # Handles nested parentheses using a simple approach
        pattern = r'EXTRACT\s*\(\s*EPOCH\s+FROM\s+\([^()]+(?:\([^()]*\))*[^()]*\)\s*\)'

        fixed_sql = re.sub(pattern, add_numeric_cast, sql, flags=re.IGNORECASE)

        if fixed_sql != sql:
            logger.info("Fixed PostgreSQL ROUND syntax in SQL query")
            logger.debug(f"Original: {sql[:200]}...")
            logger.debug(f"Fixed: {fixed_sql[:200]}...")

        return fixed_sql

    def _fix_union_order_by_syntax(self, sql: str) -> str:
        """
        Fix PostgreSQL 9.6 UNION ORDER BY compatibility.

        PostgreSQL 9.6 doesn't allow expressions (CASE, functions) in ORDER BY
        after UNION/UNION ALL. Only column names or column numbers are allowed.

        This method detects problematic patterns and wraps the query in a subquery.

        Args:
            sql: Original SQL query

        Returns:
            Fixed SQL query
        """
        import re

        sql_upper = sql.upper()

        # Check if query has UNION and ORDER BY
        has_union = 'UNION' in sql_upper
        has_order_by = 'ORDER BY' in sql_upper

        if not (has_union and has_order_by):
            return sql  # No issue

        # Check if ORDER BY comes after UNION (not within a CTE or subquery)
        # Find position of last UNION (outside of parentheses)
        union_positions = []
        order_by_positions = []

        # Simple heuristic: if ORDER BY contains CASE, CAST, or function calls, it's problematic
        order_by_pattern = r'ORDER\s+BY\s+.*?(CASE\s+WHEN|CAST\(|\w+\()'

        if re.search(order_by_pattern, sql, re.IGNORECASE | re.DOTALL):
            logger.info("Detected UNION with complex ORDER BY expression - wrapping in subquery")

            # Extract the ORDER BY clause
            order_by_match = re.search(r'ORDER\s+BY\s+(.+?)(?:LIMIT|OFFSET|$)', sql, re.IGNORECASE | re.DOTALL)

            if order_by_match:
                order_by_clause = order_by_match.group(0).strip()

                # Remove the ORDER BY from original query
                sql_without_order = re.sub(r'ORDER\s+BY\s+.+?(?=LIMIT|OFFSET|$)', '', sql, flags=re.IGNORECASE | re.DOTALL).strip()

                # Check if there's a LIMIT clause
                limit_match = re.search(r'(LIMIT\s+\d+(?:\s+OFFSET\s+\d+)?)\s*$', sql_without_order, re.IGNORECASE)

                if limit_match:
                    limit_clause = limit_match.group(1)
                    sql_without_order = re.sub(r'LIMIT\s+\d+(?:\s+OFFSET\s+\d+)?\s*$', '', sql_without_order, flags=re.IGNORECASE).strip()
                else:
                    limit_clause = ""

                # Wrap in subquery
                fixed_sql = f"SELECT * FROM (\n{sql_without_order}\n) AS union_query\n{order_by_clause}"

                if limit_clause:
                    fixed_sql += f"\n{limit_clause}"

                logger.info("Fixed UNION ORDER BY syntax for PostgreSQL 9.6 compatibility")
                logger.debug(f"Original SQL: {sql[:200]}...")
                logger.debug(f"Fixed SQL: {fixed_sql[:200]}...")

                return fixed_sql

        return sql

    def _format_row(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format a database row for JSON serialization.

        Handles:
        - datetime/date conversion to ISO format
        - Decimal conversion to float
        - None/NULL values
        - Binary data exclusion

        Args:
            row: Raw database row as dictionary

        Returns:
            Formatted row dictionary
        """
        formatted = {}

        for key, value in row.items():
            if value is None:
                formatted[key] = None
            elif isinstance(value, datetime):
                formatted[key] = value.isoformat()
            elif isinstance(value, date):
                formatted[key] = value.isoformat()
            elif isinstance(value, Decimal):
                formatted[key] = float(value)
            elif isinstance(value, bytes):
                # Exclude binary data from JSON response
                formatted[key] = "<binary data>"
            elif isinstance(value, (list, dict)):
                # Already JSON-serializable
                formatted[key] = value
            else:
                formatted[key] = value

        return formatted

    async def test_connection(self) -> bool:
        """
        Test database connection.

        Returns:
            True if connection is working, False otherwise
        """
        try:
            if self.pool is None:
                await self.initialize()

            async with self.pool.acquire() as conn:
                result = await conn.fetchval("SELECT 1")
                return result == 1

        except Exception as e:
            logger.error(f"Connection test failed: {str(e)}")
            return False

    async def get_table_info(self, table_name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a table.

        Args:
            table_name: Name of the table

        Returns:
            Dictionary with table info or None if failed
        """
        sql = """
        SELECT
            column_name,
            data_type,
            is_nullable,
            column_default
        FROM information_schema.columns
        WHERE table_name = $1
        ORDER BY ordinal_position
        """

        try:
            if self.pool is None:
                await self.initialize()

            async with self.pool.acquire() as conn:
                rows = await conn.fetch(sql, table_name)

            columns = [
                {
                    "name": row["column_name"],
                    "type": row["data_type"],
                    "nullable": row["is_nullable"] == "YES",
                    "default": row["column_default"]
                }
                for row in rows
            ]

            return {
                "table_name": table_name,
                "columns": columns,
                "column_count": len(columns)
            }

        except Exception as e:
            logger.error(f"Failed to get table info for {table_name}: {str(e)}")
            return None

    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
