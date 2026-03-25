"""
Tests for SQL Validator.
"""

import pytest
from app.security.sql_validator import (
    SQLValidator,
    SQLValidationResult,
    SecurityLevel,
    SQLValidationError
)


class TestSQLValidator:
    """Test suite for SQLValidator."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = SQLValidator()

    # ========== Valid Query Tests ==========

    def test_simple_select(self):
        """Test simple SELECT query."""
        sql = "SELECT * FROM pe_ext_procinst LIMIT 10"
        result = self.validator.validate(sql)
        assert result.is_valid
        assert result.table_count == 1
        assert result.estimated_complexity == "low"

    def test_select_with_where(self):
        """Test SELECT with WHERE clause."""
        sql = """
        SELECT id, status, start_time
        FROM pe_ext_procinst
        WHERE status = 'COMPLETED' AND start_time > '2024-01-01'
        """
        result = self.validator.validate(sql)
        assert result.is_valid
        assert result.table_count == 1

    def test_select_with_join(self):
        """Test SELECT with JOIN."""
        sql = """
        SELECT p.id, a.activity_name
        FROM pe_ext_procinst p
        LEFT JOIN pe_ext_actinst a ON p.id = a.proc_inst_id
        WHERE p.status = 'COMPLETED'
        """
        result = self.validator.validate(sql)
        assert result.is_valid
        assert result.table_count == 2

    def test_select_with_aggregation(self):
        """Test SELECT with aggregation."""
        sql = """
        SELECT
            proc_def_id,
            COUNT(*) as count,
            AVG(EXTRACT(EPOCH FROM (end_time - start_time))) as avg_duration
        FROM pe_ext_procinst
        WHERE status = 'COMPLETED'
        GROUP BY proc_def_id
        ORDER BY avg_duration DESC
        LIMIT 10
        """
        result = self.validator.validate(sql)
        assert result.is_valid
        assert result.table_count == 1
        assert result.estimated_complexity in ["low", "medium"]

    def test_select_with_subquery(self):
        """Test SELECT with subquery."""
        sql = """
        SELECT * FROM pe_ext_procinst
        WHERE id IN (
            SELECT proc_inst_id FROM pe_ext_actinst
            WHERE status = 'FAILED'
        )
        """
        result = self.validator.validate(sql)
        assert result.is_valid
        assert result.has_subquery
        assert result.table_count == 2

    def test_select_with_cte(self):
        """Test SELECT with CTE (WITH clause)."""
        sql = """
        WITH slow_processes AS (
            SELECT proc_def_id, AVG(EXTRACT(EPOCH FROM (end_time - start_time))) as avg_duration
            FROM pe_ext_procinst
            WHERE status = 'COMPLETED'
            GROUP BY proc_def_id
        )
        SELECT * FROM slow_processes WHERE avg_duration > 60
        """
        result = self.validator.validate(sql)
        assert result.is_valid
        assert result.has_subquery

    def test_case_insensitive(self):
        """Test case insensitivity."""
        sql = "select id, status from pe_ext_procinst where status = 'completed'"
        result = self.validator.validate(sql)
        assert result.is_valid

    def test_with_line_comments(self):
        """Test query with line comments."""
        sql = """
        -- This is a comment
        SELECT id, status
        FROM pe_ext_procinst
        -- WHERE status = 'FAILED'  -- Commented out
        WHERE status = 'COMPLETED'
        """
        result = self.validator.validate(sql)
        assert result.is_valid
        assert '--' not in result.cleaned_sql

    # ========== Blocked Operations Tests ==========

    def test_block_drop(self):
        """Test blocking DROP statement."""
        sql = "DROP TABLE pe_ext_procinst"
        result = self.validator.validate(sql)
        assert not result.is_valid
        assert result.has_critical_issues
        assert 'DROP' in result.blocked_keywords

    def test_block_delete(self):
        """Test blocking DELETE statement."""
        sql = "DELETE FROM pe_ext_procinst WHERE id = '123'"
        result = self.validator.validate(sql)
        assert not result.is_valid
        assert result.has_critical_issues
        assert 'DELETE' in result.blocked_keywords

    def test_block_update(self):
        """Test blocking UPDATE statement."""
        sql = "UPDATE pe_ext_procinst SET status = 'FAILED' WHERE id = '123'"
        result = self.validator.validate(sql)
        assert not result.is_valid
        assert result.has_critical_issues
        assert 'UPDATE' in result.blocked_keywords

    def test_block_insert(self):
        """Test blocking INSERT statement."""
        sql = "INSERT INTO pe_ext_procinst (id, status) VALUES ('123', 'RUNNING')"
        result = self.validator.validate(sql)
        assert not result.is_valid
        assert result.has_critical_issues
        assert 'INSERT' in result.blocked_keywords

    def test_block_truncate(self):
        """Test blocking TRUNCATE statement."""
        sql = "TRUNCATE TABLE pe_ext_procinst"
        result = self.validator.validate(sql)
        assert not result.is_valid
        assert result.has_critical_issues

    def test_block_alter(self):
        """Test blocking ALTER statement."""
        sql = "ALTER TABLE pe_ext_procinst ADD COLUMN new_col VARCHAR(255)"
        result = self.validator.validate(sql)
        assert not result.is_valid
        assert result.has_critical_issues

    def test_block_create(self):
        """Test blocking CREATE statement."""
        sql = "CREATE TABLE malicious (id VARCHAR(255))"
        result = self.validator.validate(sql)
        assert not result.is_valid
        assert result.has_critical_issues

    def test_block_exec(self):
        """Test blocking EXEC/EXECUTE."""
        sql = "EXECUTE malicious_procedure()"
        result = self.validator.validate(sql)
        assert not result.is_valid
        assert 'EXECUTE' in result.blocked_keywords

    # ========== SQL Injection Tests ==========

    def test_block_union_injection(self):
        """Test blocking UNION-based SQL injection."""
        sql = """
        SELECT * FROM pe_ext_procinst
        WHERE id = '123' UNION SELECT * FROM information_schema.tables
        """
        result = self.validator.validate(sql)
        assert not result.is_valid
        # Should be caught by injection pattern detection

    def test_block_or_injection(self):
        """Test blocking OR-based SQL injection."""
        sql = "SELECT * FROM pe_ext_procinst WHERE id = '123' OR '1'='1'"
        result = self.validator.validate(sql)
        assert not result.is_valid

    def test_block_sleep_dos(self):
        """Test blocking SLEEP DoS attack."""
        sql = "SELECT * FROM pe_ext_procinst WHERE id = PG_SLEEP(10)"
        result = self.validator.validate(sql)
        assert not result.is_valid

    # ========== Table Whitelist Tests ==========

    def test_allowed_tables(self):
        """Test all allowed tables pass validation."""
        for table in ['pe_ext_procinst', 'pe_ext_actinst', 'pe_ext_varinst']:
            sql = f"SELECT * FROM {table}"
            result = self.validator.validate(sql)
            assert result.is_valid, f"Table {table} should be allowed"

    def test_block_unauthorized_table(self):
        """Test blocking unauthorized table."""
        sql = "SELECT * FROM users"
        result = self.validator.validate(sql)
        assert not result.is_valid
        assert result.has_critical_issues

    def test_block_system_table(self):
        """Test blocking system table access."""
        sql = "SELECT * FROM information_schema.tables"
        result = self.validator.validate(sql)
        assert not result.is_valid

    def test_block_pg_catalog(self):
        """Test blocking pg_catalog access."""
        sql = "SELECT * FROM pg_catalog.pg_tables"
        result = self.validator.validate(sql)
        assert not result.is_valid

    # ========== Complexity Tests ==========

    def test_max_tables_limit(self):
        """Test maximum tables limit."""
        # Note: Same table with different aliases counts as 1 unique table
        # This query has 3 unique tables (pe_ext_procinst, pe_ext_actinst, pe_ext_varinst)
        # which does not exceed the default limit of 5
        sql = """
        SELECT * FROM pe_ext_procinst p1
        JOIN pe_ext_procinst p2 ON p1.id = p2.parent_inst_id
        JOIN pe_ext_procinst p3 ON p2.id = p3.parent_inst_id
        JOIN pe_ext_actinst a1 ON p1.id = a1.proc_inst_id
        JOIN pe_ext_actinst a2 ON p2.id = a2.proc_inst_id
        JOIN pe_ext_varinst v ON p1.id = v.proc_inst_id
        """
        result = self.validator.validate(sql)
        # Should be valid (only 3 unique tables)
        assert result.is_valid
        assert result.table_count == 3

        # Test with custom limit that WILL be exceeded
        validator_strict = SQLValidator(max_tables=2)
        result_strict = validator_strict.validate(sql)
        assert any('exceeds limit' in issue.message for issue in result_strict.issues)

    def test_max_subqueries_limit(self):
        """Test maximum subqueries limit."""
        # Create query with 4 subqueries (exceeds default limit of 3)
        sql = """
        SELECT * FROM pe_ext_procinst WHERE id IN (
            SELECT proc_inst_id FROM pe_ext_actinst WHERE activity_id IN (
                SELECT activity_id FROM pe_ext_actinst WHERE status = 'FAILED' AND id IN (
                    SELECT id FROM pe_ext_actinst WHERE start_time > NOW() - INTERVAL '7 days' AND id IN (
                        SELECT id FROM pe_ext_actinst LIMIT 1
                    )
                )
            )
        )
        """
        result = self.validator.validate(sql)
        # Should have warning about too many subqueries
        assert any('subqueries' in issue.message.lower() for issue in result.issues)

    def test_complexity_estimation_low(self):
        """Test low complexity estimation."""
        sql = "SELECT id FROM pe_ext_procinst WHERE status = 'COMPLETED' LIMIT 10"
        result = self.validator.validate(sql)
        assert result.estimated_complexity == "low"

    def test_complexity_estimation_high(self):
        """Test high complexity estimation."""
        sql = """
        SELECT
            p.proc_def_id,
            COUNT(*) as total,
            AVG(EXTRACT(EPOCH FROM (p.end_time - p.start_time))) as avg_duration,
            COUNT(CASE WHEN a.status = 'FAILED' THEN 1 END) as failed_activities
        FROM pe_ext_procinst p
        LEFT JOIN pe_ext_actinst a ON p.id = a.proc_inst_id
        LEFT JOIN pe_ext_varinst v ON p.id = v.proc_inst_id
        WHERE p.start_time > NOW() - INTERVAL '30 days'
        GROUP BY p.proc_def_id
        HAVING COUNT(*) > 10
        ORDER BY avg_duration DESC
        """
        result = self.validator.validate(sql)
        assert result.estimated_complexity in ["medium", "high"]

    # ========== Edge Cases ==========

    def test_empty_query(self):
        """Test empty query."""
        result = self.validator.validate("")
        assert not result.is_valid

    def test_whitespace_only(self):
        """Test whitespace-only query."""
        result = self.validator.validate("   \n\t  ")
        assert not result.is_valid

    def test_trailing_semicolon(self):
        """Test query with trailing semicolon."""
        sql = "SELECT * FROM pe_ext_procinst;"
        result = self.validator.validate(sql)
        assert result.is_valid
        assert not result.cleaned_sql.endswith(';')

    def test_multiple_statements(self):
        """Test blocking multiple statements."""
        sql = "SELECT * FROM pe_ext_procinst; DROP TABLE pe_ext_procinst;"
        result = self.validator.validate(sql)
        assert not result.is_valid
        assert 'DROP' in result.blocked_keywords

    # ========== Utility Methods Tests ==========

    def test_explain_validation_success(self):
        """Test explain_validation for successful validation."""
        sql = "SELECT * FROM pe_ext_procinst LIMIT 10"
        result = self.validator.validate(sql)
        explanation = self.validator.explain_validation(result)
        assert "Successfully" in explanation
        assert "✓" in explanation

    def test_explain_validation_failure(self):
        """Test explain_validation for failed validation."""
        sql = "DROP TABLE pe_ext_procinst"
        result = self.validator.validate(sql)
        explanation = self.validator.explain_validation(result)
        assert "Failed" in explanation
        assert "✗" in explanation
        assert "DROP" in explanation

    # ========== Custom Configuration Tests ==========

    def test_custom_max_tables(self):
        """Test custom max_tables configuration."""
        validator = SQLValidator(max_tables=2)
        sql = """
        SELECT * FROM pe_ext_procinst p
        JOIN pe_ext_actinst a ON p.id = a.proc_inst_id
        JOIN pe_ext_varinst v ON p.id = v.proc_inst_id
        """
        result = validator.validate(sql)
        # 3 tables exceeds limit of 2
        assert any('exceeds limit' in issue.message for issue in result.issues)

    def test_validation_result_properties(self):
        """Test ValidationResult properties."""
        sql = "DROP TABLE pe_ext_procinst"
        result = self.validator.validate(sql)

        assert len(result.errors) > 0
        assert len(result.critical_issues) > 0
        assert result.has_critical_issues
        assert 'DROP' in result.blocked_keywords


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
