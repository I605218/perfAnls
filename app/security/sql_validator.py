"""
SQL Validator for Text-to-SQL security.

This module provides SQL validation to ensure AI-generated SQL queries are safe:
- Only allows SELECT statements
- Blocks destructive operations (DROP, DELETE, UPDATE, INSERT, etc.)
- Validates query structure and limits
- Provides detailed validation results

Usage:
    validator = SQLValidator()
    result = validator.validate(sql_string)
    if result.is_valid:
        # Safe to execute
        execute_query(result.cleaned_sql)
    else:
        # Handle validation errors
        print(result.errors)
"""

import re
from typing import List, Optional
from dataclasses import dataclass
from enum import Enum


class SQLValidationError(Exception):
    """Exception raised when SQL validation fails."""
    pass


class SecurityLevel(Enum):
    """Security violation severity levels."""
    CRITICAL = "critical"  # Destructive operations
    HIGH = "high"          # Risky patterns
    MEDIUM = "medium"      # Suspicious patterns
    LOW = "low"            # Best practice violations


@dataclass
class ValidationIssue:
    """Represents a single validation issue."""
    level: SecurityLevel
    message: str
    line_number: Optional[int] = None
    column: Optional[int] = None


@dataclass
class SQLValidationResult:
    """Result of SQL validation."""
    is_valid: bool
    cleaned_sql: Optional[str] = None
    issues: List[ValidationIssue] = None
    blocked_keywords: List[str] = None
    table_count: int = 0
    has_subquery: bool = False
    estimated_complexity: str = "low"  # low, medium, high

    def __post_init__(self):
        if self.issues is None:
            self.issues = []
        if self.blocked_keywords is None:
            self.blocked_keywords = []

    @property
    def errors(self) -> List[str]:
        """Get all error messages."""
        return [issue.message for issue in self.issues]

    @property
    def critical_issues(self) -> List[ValidationIssue]:
        """Get critical security issues."""
        return [i for i in self.issues if i.level == SecurityLevel.CRITICAL]

    @property
    def has_critical_issues(self) -> bool:
        """Check if there are critical security issues."""
        return len(self.critical_issues) > 0


class SQLValidator:
    """
    SQL validator for Text-to-SQL security.

    Ensures AI-generated SQL queries are safe to execute by:
    1. Allowing only SELECT statements
    2. Blocking destructive operations
    3. Validating query structure
    4. Enforcing limits on complexity
    """

    # Blocked keywords (case-insensitive)
    DESTRUCTIVE_KEYWORDS = {
        'DROP', 'DELETE', 'TRUNCATE', 'ALTER', 'CREATE', 'INSERT',
        'UPDATE', 'REPLACE', 'GRANT', 'REVOKE', 'RENAME'
    }

    RISKY_KEYWORDS = {
        'EXECUTE', 'EXEC', 'CALL', 'PROCEDURE', 'FUNCTION',
        'TRIGGER', 'CURSOR', 'DECLARE', 'PREPARE'
    }

    # Allowed tables (whitelist approach)
    ALLOWED_TABLES = {
        'pe_ext_procinst',
        'pe_ext_actinst',
        'pe_ext_varinst'
    }

    # Default limits
    DEFAULT_MAX_TABLES = 5
    DEFAULT_MAX_SUBQUERIES = 3
    DEFAULT_MAX_UNIONS = 2

    def __init__(
        self,
        max_tables: int = DEFAULT_MAX_TABLES,
        max_subqueries: int = DEFAULT_MAX_SUBQUERIES,
        max_unions: int = DEFAULT_MAX_UNIONS,
        strict_mode: bool = True
    ):
        """
        Initialize SQL validator.

        Args:
            max_tables: Maximum number of tables allowed in query
            max_subqueries: Maximum number of subqueries allowed
            max_unions: Maximum number of UNION operations allowed
            strict_mode: If True, enforce stricter validation rules
        """
        self.max_tables = max_tables
        self.max_subqueries = max_subqueries
        self.max_unions = max_unions
        self.strict_mode = strict_mode

    def validate(self, sql: str) -> SQLValidationResult:
        """
        Validate SQL query for safety.

        Args:
            sql: SQL query string to validate

        Returns:
            SQLValidationResult with validation details
        """
        issues = []
        blocked_keywords = []

        # Basic checks
        if not sql or not sql.strip():
            issues.append(ValidationIssue(
                level=SecurityLevel.CRITICAL,
                message="SQL query is empty"
            ))
            return SQLValidationResult(is_valid=False, issues=issues)

        # Clean and normalize SQL
        cleaned_sql = self._clean_sql(sql)
        sql_upper = cleaned_sql.upper()

        # 1. Check for destructive keywords
        for keyword in self.DESTRUCTIVE_KEYWORDS:
            if self._contains_keyword(sql_upper, keyword):
                blocked_keywords.append(keyword)
                issues.append(ValidationIssue(
                    level=SecurityLevel.CRITICAL,
                    message=f"Blocked destructive operation: {keyword}"
                ))

        # 2. Check for risky keywords
        for keyword in self.RISKY_KEYWORDS:
            if self._contains_keyword(sql_upper, keyword):
                blocked_keywords.append(keyword)
                issues.append(ValidationIssue(
                    level=SecurityLevel.HIGH,
                    message=f"Blocked risky operation: {keyword}"
                ))

        # 3. Must start with SELECT
        if not self._starts_with_select(sql_upper):
            issues.append(ValidationIssue(
                level=SecurityLevel.CRITICAL,
                message="Query must start with SELECT"
            ))

        # 4. Check for SQL injection patterns
        injection_issues = self._check_injection_patterns(cleaned_sql)
        issues.extend(injection_issues)

        # 5. Validate table names (whitelist)
        table_issues, table_count = self._validate_tables(cleaned_sql)
        issues.extend(table_issues)

        # 6. Check query complexity
        complexity_issues, has_subquery = self._check_complexity(sql_upper)
        issues.extend(complexity_issues)

        # 7. Check for comments (potential obfuscation)
        if self._has_suspicious_comments(cleaned_sql):
            issues.append(ValidationIssue(
                level=SecurityLevel.MEDIUM,
                message="Query contains suspicious comments"
            ))

        # Determine complexity
        estimated_complexity = self._estimate_complexity(
            table_count,
            has_subquery,
            sql_upper
        )

        # Final decision
        is_valid = not any(
            issue.level in (SecurityLevel.CRITICAL, SecurityLevel.HIGH)
            for issue in issues
        )

        return SQLValidationResult(
            is_valid=is_valid,
            cleaned_sql=cleaned_sql if is_valid else None,
            issues=issues,
            blocked_keywords=blocked_keywords,
            table_count=table_count,
            has_subquery=has_subquery,
            estimated_complexity=estimated_complexity
        )

    def _clean_sql(self, sql: str) -> str:
        """Clean and normalize SQL query."""
        # Remove leading/trailing whitespace
        sql = sql.strip()

        # Remove line comments (--) but preserve rest of line
        sql = re.sub(r'--[^\n]*', '', sql)

        # Normalize whitespace
        sql = re.sub(r'\s+', ' ', sql)

        # Remove trailing semicolon if present
        sql = sql.rstrip(';')

        return sql

    def _contains_keyword(self, sql_upper: str, keyword: str) -> bool:
        """
        Check if SQL contains a keyword as a whole word.
        Uses word boundaries to avoid false positives.
        """
        pattern = r'\b' + re.escape(keyword) + r'\b'
        return bool(re.search(pattern, sql_upper))

    def _starts_with_select(self, sql_upper: str) -> bool:
        """Check if SQL starts with SELECT (after CTEs)."""
        # Allow WITH ... AS (...) SELECT pattern (CTEs)
        if sql_upper.strip().startswith('WITH'):
            # Find the main SELECT after CTE
            # Simple check: must contain SELECT after WITH
            return 'SELECT' in sql_upper
        return sql_upper.strip().startswith('SELECT')

    def _check_injection_patterns(self, sql: str) -> List[ValidationIssue]:
        """Check for SQL injection patterns."""
        issues = []
        sql_upper = sql.upper()

        # Check for suspicious patterns
        suspicious_patterns = [
            (r"'\s*OR\s+'", "Potential SQL injection: ' OR ' pattern"),
            (r";\s*DROP", "Potential SQL injection: ; DROP pattern"),
            (r"UNION\s+SELECT.*FROM.*INFORMATION_SCHEMA",
             "Potential SQL injection: UNION with information_schema"),
            (r"LOAD_FILE\s*\(", "Blocked function: LOAD_FILE"),
            (r"INTO\s+OUTFILE", "Blocked operation: INTO OUTFILE"),
            (r"BENCHMARK\s*\(", "Potential DoS: BENCHMARK function"),
            (r"SLEEP\s*\(", "Potential DoS: SLEEP function"),
            (r"PG_SLEEP\s*\(", "Potential DoS: PG_SLEEP function"),
        ]

        for pattern, message in suspicious_patterns:
            if re.search(pattern, sql_upper):
                issues.append(ValidationIssue(
                    level=SecurityLevel.HIGH,
                    message=message
                ))

        return issues

    def _validate_tables(self, sql: str) -> tuple[List[ValidationIssue], int]:
        """
        Validate table names against whitelist.
        Returns (issues, table_count).
        """
        issues = []
        sql_upper = sql.upper()

        # Extract CTE names to exclude them from validation
        cte_names = set()
        cte_pattern = r'WITH\s+([a-zA-Z_][a-zA-Z0-9_]*)\s+AS'
        cte_matches = re.findall(cte_pattern, sql, re.IGNORECASE)
        for cte_name in cte_matches:
            cte_names.add(cte_name.lower())

        # Extract table names from FROM and JOIN clauses
        # Pattern: FROM/JOIN table_name or FROM/JOIN schema.table_name
        # But exclude table aliases (table_name alias_name)
        table_pattern = r'(?:FROM|JOIN)\s+([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)?)'
        matches = re.findall(table_pattern, sql, re.IGNORECASE)

        found_tables = set()
        for match in matches:
            # Handle schema.table or just table
            table_name = match.split('.')[-1].lower()

            # Skip CTE names (they are temporary tables defined in the query)
            if table_name in cte_names:
                continue

            found_tables.add(table_name)

            # Check against whitelist
            if table_name not in self.ALLOWED_TABLES:
                issues.append(ValidationIssue(
                    level=SecurityLevel.CRITICAL,
                    message=f"Table '{table_name}' is not in the allowed list. "
                            f"Allowed tables: {', '.join(self.ALLOWED_TABLES)}"
                ))

        table_count = len(found_tables)

        # Check table count limit (count unique real tables, not aliases)
        if table_count > self.max_tables:
            issues.append(ValidationIssue(
                level=SecurityLevel.MEDIUM,
                message=f"Query uses {table_count} unique tables, exceeds limit of {self.max_tables}"
            ))

        return issues, table_count

    def _check_complexity(self, sql_upper: str) -> tuple[List[ValidationIssue], bool]:
        """
        Check query complexity.
        Returns (issues, has_subquery).
        """
        issues = []

        # Count subqueries
        subquery_count = sql_upper.count('SELECT') - 1  # Subtract main SELECT
        has_subquery = subquery_count > 0

        if subquery_count > self.max_subqueries:
            issues.append(ValidationIssue(
                level=SecurityLevel.MEDIUM,
                message=f"Query has {subquery_count} subqueries, exceeds limit of {self.max_subqueries}"
            ))

        # Count UNION operations
        union_count = sql_upper.count('UNION')
        if union_count > self.max_unions:
            issues.append(ValidationIssue(
                level=SecurityLevel.MEDIUM,
                message=f"Query has {union_count} UNION operations, exceeds limit of {self.max_unions}"
            ))

        return issues, has_subquery

    def _has_suspicious_comments(self, sql: str) -> bool:
        """Check for suspicious comment patterns."""
        # Check for /* */ style comments that might hide malicious code
        if re.search(r'/\*.*?\*/', sql, re.DOTALL):
            # Check if comment contains keywords
            comments = re.findall(r'/\*(.*?)\*/', sql, re.DOTALL)
            for comment in comments:
                comment_upper = comment.upper()
                for keyword in self.DESTRUCTIVE_KEYWORDS | self.RISKY_KEYWORDS:
                    if keyword in comment_upper:
                        return True
        return False

    def _estimate_complexity(
        self,
        table_count: int,
        has_subquery: bool,
        sql_upper: str
    ) -> str:
        """Estimate query complexity."""
        complexity_score = 0

        # Factors that increase complexity
        complexity_score += table_count * 2
        complexity_score += 5 if has_subquery else 0
        complexity_score += sql_upper.count('JOIN') * 2
        complexity_score += sql_upper.count('UNION') * 3
        complexity_score += sql_upper.count('GROUP BY') * 2
        complexity_score += sql_upper.count('ORDER BY')
        complexity_score += sql_upper.count('HAVING') * 2
        complexity_score += sql_upper.count('CASE WHEN') * 2

        if complexity_score < 5:
            return "low"
        elif complexity_score < 15:
            return "medium"
        else:
            return "high"

    def explain_validation(self, result: SQLValidationResult) -> str:
        """
        Generate human-readable explanation of validation result.

        Args:
            result: SQLValidationResult to explain

        Returns:
            Formatted explanation string
        """
        if result.is_valid:
            lines = [
                "✓ SQL Query Validated Successfully",
                f"  Tables: {result.table_count}",
                f"  Complexity: {result.estimated_complexity}",
                f"  Subqueries: {'Yes' if result.has_subquery else 'No'}"
            ]
            if result.issues:
                lines.append(f"  Warnings: {len(result.issues)}")
                for issue in result.issues:
                    lines.append(f"    - {issue.message}")
        else:
            lines = [
                "✗ SQL Query Validation Failed",
                f"  Critical Issues: {len(result.critical_issues)}",
                f"  Total Issues: {len(result.issues)}",
                ""
            ]
            if result.blocked_keywords:
                lines.append(f"  Blocked Keywords: {', '.join(result.blocked_keywords)}")
            lines.append("")
            lines.append("  Issues:")
            for issue in result.issues:
                level_icon = {
                    SecurityLevel.CRITICAL: "🔴",
                    SecurityLevel.HIGH: "🟠",
                    SecurityLevel.MEDIUM: "🟡",
                    SecurityLevel.LOW: "🔵"
                }.get(issue.level, "⚪")
                lines.append(f"    {level_icon} [{issue.level.value.upper()}] {issue.message}")

        return "\n".join(lines)
