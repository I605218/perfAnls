"""
Text-to-SQL Prompt Builder for AI-powered performance analysis.

This module constructs high-quality prompts for Claude AI to generate SQL queries
from natural language descriptions. It includes:
- System prompt with role definition and database schema
- Few-shot examples for common query patterns
- Output format specifications
- SQL generation constraints
"""

import json
from typing import List, Optional, Dict, Any, Set
from dataclasses import dataclass
from pathlib import Path
from app.prompts.schema_selector import identify_relevant_tables


@dataclass
class FewShotExample:
    """A few-shot example for Text-to-SQL learning."""
    user_query: str
    sql: str
    explanation: str
    category: str = "general"  # general, aggregation, join, time_series, etc.


class TextToSQLPromptBuilder:
    """
    Builder for Text-to-SQL prompts.

    Constructs comprehensive prompts that guide Claude AI to generate
    safe, efficient, and accurate SQL queries for performance analysis.
    """

    def __init__(self, schema_dir: str = "schema", enable_smart_loading: bool = True):
        """
        Initialize prompt builder.

        Args:
            schema_dir: Directory containing schema JSON files
            enable_smart_loading: If True, only load relevant schemas based on user query.
                                 If False, load all schemas (backward compatible).
        """
        self.schema_dir = Path(schema_dir)
        self.schema_cache = {}
        self.enable_smart_loading = enable_smart_loading

        # Always load all schemas into cache for smart selection
        self._load_all_schemas()

    def _load_all_schemas(self):
        """Load all schema files into memory cache."""
        schema_files = [
            "pe_ext_procinst.json",
            "pe_ext_actinst.json",
            "pe_ext_varinst.json",
            "act_ru_job.json",
            "act_ge_bytearray.json",
            "act_ru_deadletter_job.json"
        ]

        for filename in schema_files:
            file_path = self.schema_dir / filename
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    table_name = filename.replace('.json', '')
                    self.schema_cache[table_name] = json.load(f)

    def build_system_prompt(
        self,
        user_query: Optional[str] = None,
        include_examples: bool = True
    ) -> str:
        """
        Build the system prompt for Text-to-SQL.

        Args:
            user_query: Optional user query for smart schema loading
            include_examples: Whether to include few-shot examples

        Returns:
            Complete system prompt string
        """
        sections = [
            self._build_role_definition(),
            self._build_schema_section(user_query=user_query),
            self._build_constraints_section(),
            self._build_output_format_section()
        ]

        if include_examples:
            sections.append(self._build_examples_section())

        sections.append(self._build_best_practices_section())

        return "\n\n".join(sections)

    def _build_role_definition(self) -> str:
        """Build the AI role definition."""
        return """# Role: Process Engine Performance Analysis Expert

You are an expert SQL developer specializing in process engine performance analysis. Your task is to convert natural language queries into safe, efficient PostgreSQL queries that analyze process execution data.

## Your Responsibilities
- Generate ONLY SELECT queries (no modifications allowed)
- Prioritize query safety and performance
- Use proper indexing hints from schema
- Follow PostgreSQL best practices
- Provide clear explanations of your SQL logic

## Database Context
You are analyzing SAP Digital Manufacturing Process Engine data stored in PostgreSQL 9.6. The database contains three core tables tracking BPMN process execution:
- **pe_ext_procinst**: Process instance lifecycle data (flow-level metrics)
- **pe_ext_actinst**: Activity instance execution data (step-level metrics)
- **pe_ext_varinst**: Variable data (business context and input/output parameters)"""

    def _build_schema_section(self, user_query: Optional[str] = None) -> str:
        """
        Build the database schema section.

        Args:
            user_query: Optional user query for smart schema selection

        Returns:
            Schema section string
        """
        schema_parts = ["# Database Schema"]

        # Determine which schemas to include
        if self.enable_smart_loading and user_query:
            # Smart loading: only include relevant tables
            relevant_tables = identify_relevant_tables(user_query)
            schemas_to_include = {
                table: schema
                for table, schema in self.schema_cache.items()
                if table in relevant_tables
            }

            # Log for debugging
            schema_parts.append(
                f"\n**Note**: Based on your query, we're focusing on these tables: "
                f"{', '.join(relevant_tables)}. "
                f"If you need other tables, please mention them explicitly.\n"
            )
        else:
            # Load all schemas (backward compatible)
            schemas_to_include = self.schema_cache

        # Add each table's schema
        for table_name, schema in schemas_to_include.items():
            schema_parts.append(f"\n## Table: {schema['table_name']}")
            schema_parts.append(f"**Description**: {schema['description']}")
            schema_parts.append(f"**Business Context**: {schema['business_context']}")

            # Add key columns
            schema_parts.append("\n### Key Columns:")
            for col in schema['columns'][:10]:  # Show first 10 most important columns
                col_info = f"- **{col['name']}** ({col['type']}): {col['description']}"
                if col.get('indexed'):
                    col_info += " [INDEXED]"
                if col.get('possible_values'):
                    values_preview = ', '.join([str(v['value']) for v in col['possible_values'][:3]])
                    col_info += f" (Values: {values_preview}, ...)"
                schema_parts.append(col_info)

            # Add relationships
            if schema.get('relationships'):
                schema_parts.append("\n### Relationships:")
                for rel in schema['relationships']:
                    # Handle different relationship structures
                    target = rel.get('target_table', 'N/A')
                    target_col = rel.get('target_column', 'N/A')
                    fk = rel.get('foreign_key') or rel.get('foreign_key_in_target', 'N/A')
                    schema_parts.append(
                        f"- {rel['type']}: {fk} → {target}.{target_col}"
                    )

            # Add AI analysis guidelines (CRITICAL for SQL generation rules)
            if schema.get('ai_analysis_guidelines'):
                schema_parts.append(f"\n### **IMPORTANT: SQL Generation Guidelines for {schema['table_name']}**")
                for guideline in schema['ai_analysis_guidelines']:
                    schema_parts.append(f"- {guideline}")

            # Add common query examples for few-shot learning
            if schema.get('common_queries'):
                schema_parts.append(f"\n### Common Query Examples for {schema['table_name']}:")
                for i, query_example in enumerate(schema['common_queries'], 1):
                    schema_parts.append(f"\n**Example {i}**: {query_example.get('description', 'N/A')}")
                    schema_parts.append(f"```sql\n{query_example.get('sql', '')}\n```")

        return "\n".join(schema_parts)

    def _build_constraints_section(self) -> str:
        """Build the SQL generation constraints section."""
        return """# SQL Generation Constraints

## CRITICAL - Security Rules
1. **ONLY SELECT statements** - Never generate INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, TRUNCATE
2. **Table whitelist** - Only query these tables: pe_ext_procinst, pe_ext_actinst, pe_ext_varinst
3. **No system tables** - Never access information_schema, pg_catalog, or other system tables
4. **No dangerous functions** - Avoid EXECUTE, LOAD_FILE, INTO OUTFILE, PG_SLEEP, BENCHMARK

## Query Quality Rules
1. **Always filter by time range** - Use start_time >= ... with indexed columns
2. **Always add tenant_id filter** - Multi-tenant data requires: WHERE tenant_id = 'xxx'
3. **Check NULL values** - For duration calculations: end_time IS NOT NULL AND start_time IS NOT NULL
4. **Standard status filter** - For completed processes: status IN ('COMPLETED', 'COMPLETED_WITH_ERROR')
5. **Exclude debug data** - Add: AND sub_status NOT IN ('BREAKING', 'SUB_BREAKING')

## Performance Best Practices
1. **Use indexed columns** - Start_time, end_time, proc_inst_id, name have indexes
2. **Limit result sets** - Always include LIMIT clause (default: 100, max: 10000)
3. **Aggregate first** - When possible, aggregate before joining
4. **Use LEFT JOIN** - Safer than INNER JOIN (handles deleted records)
5. **Avoid SELECT *** - Select specific columns for better performance"""

    def _build_output_format_section(self) -> str:
        """Build the output format specification."""
        return """# Output Format

You must respond in the following JSON format:

```json
{
  "sql": "SELECT ... (your PostgreSQL query)",
  "explanation": "Clear explanation of what this query does and why",
  "reasoning": "Step-by-step reasoning for query design choices",
  "caveats": ["Important limitations or assumptions"],
  "performance_notes": "Expected query performance and optimization hints"
}
```

## Explanation Guidelines
- Start with "This query..." and describe the main purpose
- Explain any complex logic (CASE statements, subqueries, window functions)
- Mention which indexes will be used
- Note any assumptions about data (e.g., "assuming processes are completed")

## Reasoning Guidelines
- Explain why you chose specific tables
- Justify filtering conditions
- Describe join strategy if applicable
- Mention any trade-offs made

## Caveats Guidelines
- List data quality assumptions
- Note edge cases not handled
- Warn about potential performance issues for large datasets
- Mention any limitations of the analysis"""

    def _build_examples_section(self) -> str:
        """Build the few-shot examples section."""
        examples = self._get_few_shot_examples()

        parts = ["# Examples\n"]
        parts.append("Here are examples of how to convert natural language queries to SQL:\n")

        for i, example in enumerate(examples, 1):
            parts.append(f"## Example {i}: {example.category.title()}")
            parts.append(f"**User Query**: {example.user_query}")
            parts.append(f"\n**SQL**:")
            parts.append(f"```sql\n{example.sql}\n```")
            parts.append(f"\n**Explanation**: {example.explanation}\n")

        return "\n".join(parts)

    def _get_few_shot_examples(self) -> List[FewShotExample]:
        """Get few-shot learning examples."""
        return [
            FewShotExample(
                user_query="Show me the 10 slowest process definitions in the last 30 days",
                sql="""SELECT
  SPLIT_PART(proc_def_id, ':', 1) as process_key,
  COUNT(*) as execution_count,
  ROUND((AVG(EXTRACT(EPOCH FROM (end_time - start_time))))::numeric, 2) as avg_duration_seconds,
  ROUND((PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY EXTRACT(EPOCH FROM (end_time - start_time))))::numeric, 2) as p95_duration
FROM pe_ext_procinst
WHERE status IN ('COMPLETED', 'COMPLETED_WITH_ERROR')
  AND end_time IS NOT NULL
  AND start_time IS NOT NULL
  AND start_time >= CURRENT_TIMESTAMP - INTERVAL '30 days'
GROUP BY SPLIT_PART(proc_def_id, ':', 1)
HAVING COUNT(*) > 10
ORDER BY avg_duration_seconds DESC
LIMIT 10""",
                explanation="This query identifies the slowest process definitions by calculating average and P95 execution time. It filters to completed processes in the last 30 days, groups by process key (removing version info), and only includes processes with >10 executions to ensure statistical significance. Uses indexed start_time column for efficient filtering.",
                category="aggregation"
            ),

            FewShotExample(
                user_query="Find processes that failed in the last 7 days with their error messages",
                sql="""SELECT
  id as process_instance_id,
  proc_def_id,
  proc_inst_name,
  start_time,
  end_time,
  EXTRACT(EPOCH FROM (end_time - start_time)) as duration_seconds,
  error_message_id,
  LEFT(error_message, 200) as error_preview
FROM pe_ext_procinst
WHERE status = 'FAILED'
  AND start_time >= CURRENT_TIMESTAMP - INTERVAL '7 days'
ORDER BY start_time DESC
LIMIT 100""",
                explanation="This query retrieves failed processes with their error information. It limits error_message to 200 characters for readability, calculates duration, and orders by most recent failures first. Uses indexed start_time for efficient time-range filtering.",
                category="simple_filter"
            ),

            FewShotExample(
                user_query="Which activity types take the longest to execute on average?",
                sql="""SELECT
  activity_type,
  activity_name,
  COUNT(*) as execution_count,
  ROUND((AVG(EXTRACT(EPOCH FROM (end_time - start_time))))::numeric, 2) as avg_duration_seconds,
  ROUND((MAX(EXTRACT(EPOCH FROM (end_time - start_time))))::numeric, 2) as max_duration_seconds
FROM pe_ext_actinst
WHERE status = 'COMPLETED'
  AND end_time IS NOT NULL
  AND start_time IS NOT NULL
  AND sub_status NOT IN ('BREAKING', 'SUB_BREAKING')
  AND start_time >= CURRENT_TIMESTAMP - INTERVAL '30 days'
GROUP BY activity_type, activity_name
HAVING COUNT(*) > 5
ORDER BY avg_duration_seconds DESC
LIMIT 20""",
                explanation="This query analyzes activity-level performance by grouping activities by type and name. It excludes debug states (BREAKING) which artificially inflate duration, requires minimum 5 executions for reliability, and uses indexed start_time for time filtering.",
                category="activity_analysis"
            ),

            FewShotExample(
                user_query="Show me the slowest activities in process instance 'abc123'",
                sql="""SELECT
  activity_name,
  activity_type,
  start_time,
  end_time,
  EXTRACT(EPOCH FROM (end_time - start_time)) as duration_seconds,
  status,
  error_message
FROM pe_ext_actinst
WHERE proc_inst_id = 'abc123'
  AND end_time IS NOT NULL
ORDER BY duration_seconds DESC
LIMIT 50""",
                explanation="This query drills into a specific process instance to identify its slowest activities. Uses indexed proc_inst_id for fast lookup, includes error information for failed activities, and orders by duration to show bottlenecks first.",
                category="drill_down"
            ),

            FewShotExample(
                user_query="Compare process performance between this week and last week",
                sql="""WITH this_week AS (
  SELECT
    SPLIT_PART(proc_def_id, ':', 1) as process_key,
    COUNT(*) as count,
    ROUND((AVG(EXTRACT(EPOCH FROM (end_time - start_time))))::numeric, 2) as avg_duration
  FROM pe_ext_procinst
  WHERE status IN ('COMPLETED', 'COMPLETED_WITH_ERROR')
    AND start_time >= DATE_TRUNC('week', CURRENT_TIMESTAMP)
    AND end_time IS NOT NULL
  GROUP BY SPLIT_PART(proc_def_id, ':', 1)
),
last_week AS (
  SELECT
    SPLIT_PART(proc_def_id, ':', 1) as process_key,
    COUNT(*) as count,
    ROUND((AVG(EXTRACT(EPOCH FROM (end_time - start_time))))::numeric, 2) as avg_duration
  FROM pe_ext_procinst
  WHERE status IN ('COMPLETED', 'COMPLETED_WITH_ERROR')
    AND start_time >= DATE_TRUNC('week', CURRENT_TIMESTAMP) - INTERVAL '7 days'
    AND start_time < DATE_TRUNC('week', CURRENT_TIMESTAMP)
    AND end_time IS NOT NULL
  GROUP BY SPLIT_PART(proc_def_id, ':', 1)
)
SELECT
  COALESCE(tw.process_key, lw.process_key) as process_key,
  lw.count as last_week_count,
  tw.count as this_week_count,
  lw.avg_duration as last_week_avg_duration,
  tw.avg_duration as this_week_avg_duration,
  ROUND((tw.avg_duration - lw.avg_duration)::numeric, 2) as duration_change,
  ROUND((100.0 * (tw.avg_duration - lw.avg_duration) / NULLIF(lw.avg_duration, 0))::numeric, 2) as percent_change
FROM this_week tw
FULL OUTER JOIN last_week lw ON tw.process_key = lw.process_key
ORDER BY ABS(percent_change) DESC NULLS LAST
LIMIT 20""",
                explanation="This query uses CTEs to separately calculate metrics for this week and last week, then joins them to compute week-over-week changes. Uses DATE_TRUNC for precise week boundaries, FULL OUTER JOIN to include processes that only ran in one period, and calculates both absolute and percentage changes. Orders by largest changes to highlight processes with significant performance shifts.",
                category="time_comparison"
            ),

            FewShotExample(
                user_query="What variables are causing processes to run slowly?",
                sql="""SELECT
  v.name as variable_name,
  v.type as variable_type,
  COUNT(DISTINCT v.proc_inst_id) as process_count,
  ROUND((AVG(LENGTH(v.value)))::numeric, 2) as avg_size_bytes,
  COUNT(CASE WHEN v.value_id IS NOT NULL THEN 1 END) as large_value_count,
  ROUND((AVG(EXTRACT(EPOCH FROM (p.end_time - p.start_time))))::numeric, 2) as avg_process_duration_seconds
FROM pe_ext_varinst v
INNER JOIN pe_ext_procinst p ON v.proc_inst_id = p.id
WHERE v.create_time >= CURRENT_TIMESTAMP - INTERVAL '30 days'
  AND p.status IN ('COMPLETED', 'COMPLETED_WITH_ERROR')
  AND p.end_time IS NOT NULL
  AND (LENGTH(v.value) > 1000 OR v.value_id IS NOT NULL)
GROUP BY v.name, v.type
HAVING COUNT(DISTINCT v.proc_inst_id) > 10
ORDER BY avg_process_duration_seconds DESC
LIMIT 20""",
                explanation="This query correlates large variables with process execution time to identify data-driven performance issues. Filters to large variables (>1000 chars or using external storage), joins with process table to get duration, and groups by variable name to find patterns. Uses indexed columns (create_time, proc_inst_id) for performance.",
                category="variable_analysis"
            ),

            FewShotExample(
                user_query="Show hourly process execution trends over the last 24 hours",
                sql="""SELECT
  DATE_TRUNC('hour', start_time) as hour_bucket,
  COUNT(*) as execution_count,
  COUNT(CASE WHEN status = 'COMPLETED' THEN 1 END) as completed_count,
  COUNT(CASE WHEN status = 'FAILED' THEN 1 END) as failed_count,
  ROUND((AVG(EXTRACT(EPOCH FROM (end_time - start_time))))::numeric, 2) as avg_duration_seconds,
  ROUND((PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY EXTRACT(EPOCH FROM (end_time - start_time))))::numeric, 2) as p95_duration
FROM pe_ext_procinst
WHERE start_time >= CURRENT_TIMESTAMP - INTERVAL '24 hours'
  AND end_time IS NOT NULL
GROUP BY DATE_TRUNC('hour', start_time)
ORDER BY hour_bucket DESC""",
                explanation="This query analyzes process execution patterns by hour to identify load peaks and performance degradation periods. Uses DATE_TRUNC to group by hour, calculates completion/failure counts and duration metrics per hour, and orders by most recent first. Uses indexed start_time for efficient range filtering.",
                category="time_series"
            ),

            FewShotExample(
                user_query="Find processes with subprocess calls and their performance impact",
                sql="""SELECT
  parent.proc_def_id as parent_process,
  COUNT(DISTINCT parent.id) as parent_count,
  ROUND((AVG(EXTRACT(EPOCH FROM (parent.end_time - parent.start_time))))::numeric, 2) as avg_parent_duration,
  COUNT(child.id) as total_subprocesses,
  ROUND((AVG(EXTRACT(EPOCH FROM (child.end_time - child.start_time))))::numeric, 2) as avg_child_duration,
  ROUND((100.0 * AVG(EXTRACT(EPOCH FROM (child.end_time - child.start_time))) /
        NULLIF(AVG(EXTRACT(EPOCH FROM (parent.end_time - parent.start_time))), 0))::numeric, 2) as subprocess_time_percentage
FROM pe_ext_procinst parent
INNER JOIN pe_ext_procinst child ON child.parent_inst_id = parent.id
WHERE parent.status IN ('COMPLETED', 'COMPLETED_WITH_ERROR')
  AND child.status IN ('COMPLETED', 'COMPLETED_WITH_ERROR')
  AND parent.end_time IS NOT NULL
  AND child.end_time IS NOT NULL
  AND parent.start_time >= CURRENT_TIMESTAMP - INTERVAL '30 days'
GROUP BY parent.proc_def_id
HAVING COUNT(DISTINCT parent.id) > 5
ORDER BY subprocess_time_percentage DESC
LIMIT 20""",
                explanation="This query analyzes subprocess performance impact by joining parent and child processes via parent_inst_id. Calculates what percentage of parent execution time is spent in subprocesses, helping identify where subprocess calls are bottlenecks. Uses indexed parent_inst_id and start_time for efficient querying.",
                category="subprocess_analysis"
            )
        ]

    def _build_best_practices_section(self) -> str:
        """Build best practices guidance."""
        return """# SQL Best Practices Summary

1. **Time Filtering**: Always use `start_time >= CURRENT_TIMESTAMP - INTERVAL 'X days'`
2. **Duration Calculation**: `EXTRACT(EPOCH FROM (end_time - start_time))` for seconds
3. **Process Key Extraction**: `SPLIT_PART(proc_def_id, ':', 1)` to remove version
4. **Percentiles**: Use `PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY ...)` for P95
5. **Safe Division**: Use `NULLIF(denominator, 0)` to avoid division by zero
6. **Low Frequency Filter**: `HAVING COUNT(*) > N` to exclude statistical noise
7. **Join Strategy**: Use LEFT JOIN for robustness, INNER JOIN only when necessary
8. **Limit Results**: Always include LIMIT clause (default 100, max 10000)
9. **Index Usage**: Filter on indexed columns first (start_time, end_time, proc_inst_id, name)
10. **Status Check**: Include appropriate status filters for completed/failed processes

# Common Patterns to Remember

## Time Duration Formula
```sql
EXTRACT(EPOCH FROM (end_time - start_time)) as duration_seconds
```

## Standard Process Filter
```sql
WHERE status IN ('COMPLETED', 'COMPLETED_WITH_ERROR')
  AND end_time IS NOT NULL
  AND start_time IS NOT NULL
  AND start_time >= CURRENT_TIMESTAMP - INTERVAL '30 days'
```

## Activity Filter (exclude debug)
```sql
WHERE status = 'COMPLETED'
  AND end_time IS NOT NULL
  AND sub_status NOT IN ('BREAKING', 'SUB_BREAKING')
```

## Safe Percentage Calculation
```sql
ROUND((100.0 * numerator / NULLIF(denominator, 0))::numeric, 2) as percentage
```

Now, please convert the user's natural language query into SQL following all the rules and examples above."""

    def build_user_prompt(self, user_query: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Build the user prompt with query and optional context.

        Args:
            user_query: Natural language query from user
            context: Optional context (tenant_id, time_range, etc.)

        Returns:
            Formatted user prompt
        """
        parts = []

        if context:
            parts.append("# Context")
            if context.get('tenant_id'):
                parts.append(f"- Tenant ID: {context['tenant_id']}")
            if context.get('time_range'):
                parts.append(f"- Time Range: {context['time_range']}")
            if context.get('additional_filters'):
                parts.append(f"- Additional Filters: {context['additional_filters']}")
            parts.append("")

        parts.append("# User Query")
        parts.append(user_query)
        parts.append("")
        parts.append("Please generate a SQL query that answers this question. Remember to:")
        parts.append("- Only use SELECT statements")
        parts.append("- Query only allowed tables (pe_ext_procinst, pe_ext_actinst, pe_ext_varinst)")
        parts.append("- Include time range filter using indexed columns")
        parts.append("- Add appropriate status filters")
        parts.append("- Return results in the specified JSON format")

        return "\n".join(parts)

    def build_full_prompt(
        self,
        user_query: str,
        context: Optional[Dict[str, Any]] = None,
        include_examples: bool = True
    ) -> tuple[str, str]:
        """
        Build complete prompt (system + user).

        Args:
            user_query: Natural language query
            context: Optional context information
            include_examples: Whether to include few-shot examples

        Returns:
            Tuple of (system_prompt, user_prompt)
        """
        # Build system prompt with smart schema loading
        system_prompt = self.build_system_prompt(
            user_query=user_query,
            include_examples=include_examples
        )
        user_prompt = self.build_user_prompt(user_query, context)

        return system_prompt, user_prompt

    def get_schema_summary(self) -> Dict[str, Any]:
        """Get a summary of loaded schemas."""
        return {
            table: {
                "description": schema["description"],
                "columns_count": len(schema["columns"]),
                "indexes_count": len(schema["indexes"]),
                "relationships": len(schema.get("relationships", []))
            }
            for table, schema in self.schema_cache.items()
        }
