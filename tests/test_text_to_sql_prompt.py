"""
Tests for Text-to-SQL Prompt Builder.
"""

import pytest
import json
from pathlib import Path
from app.prompts.text_to_sql_prompt import TextToSQLPromptBuilder, FewShotExample


class TestTextToSQLPromptBuilder:
    """Test suite for TextToSQLPromptBuilder."""

    def setup_method(self):
        """Set up test fixtures."""
        self.builder = TextToSQLPromptBuilder(schema_dir="schema")

    def test_initialization(self):
        """Test prompt builder initialization."""
        assert self.builder is not None
        assert len(self.builder.schema_cache) > 0

    def test_schema_loading(self):
        """Test schema files are loaded correctly."""
        expected_tables = ['pe_ext_procinst', 'pe_ext_actinst', 'pe_ext_varinst']
        for table in expected_tables:
            assert table in self.builder.schema_cache
            schema = self.builder.schema_cache[table]
            assert 'description' in schema
            assert 'columns' in schema
            assert 'relationships' in schema

    def test_get_schema_summary(self):
        """Test schema summary generation."""
        summary = self.builder.get_schema_summary()
        assert len(summary) > 0
        for table, info in summary.items():
            assert 'description' in info
            assert 'columns_count' in info
            assert 'indexes_count' in info
            assert info['columns_count'] > 0

    def test_build_system_prompt_without_examples(self):
        """Test system prompt generation without examples."""
        prompt = self.builder.build_system_prompt(include_examples=False)

        # Check required sections
        assert "Role: Process Engine Performance Analysis Expert" in prompt
        assert "Database Schema" in prompt
        assert "SQL Generation Constraints" in prompt
        assert "Output Format" in prompt
        assert "Best Practices" in prompt

        # Should not include examples
        assert "Example 1:" not in prompt

    def test_build_system_prompt_with_examples(self):
        """Test system prompt generation with examples."""
        prompt = self.builder.build_system_prompt(include_examples=True)

        # Check examples are included
        assert "Examples" in prompt
        assert "Example 1:" in prompt
        assert "User Query" in prompt
        assert "Explanation" in prompt

    def test_system_prompt_includes_schema_details(self):
        """Test system prompt includes schema details."""
        prompt = self.builder.build_system_prompt(include_examples=False)

        # Check table names
        assert "pe_ext_procinst" in prompt
        assert "pe_ext_actinst" in prompt
        assert "pe_ext_varinst" in prompt

        # Check key columns are mentioned
        assert "proc_def_id" in prompt or "id" in prompt
        assert "start_time" in prompt
        assert "end_time" in prompt

    def test_system_prompt_includes_constraints(self):
        """Test system prompt includes SQL constraints."""
        prompt = self.builder.build_system_prompt(include_examples=False)

        # Security constraints
        assert "ONLY SELECT statements" in prompt
        assert "Table whitelist" in prompt

        # Quality rules
        assert "tenant_id" in prompt
        assert "time range" in prompt or "start_time" in prompt

    def test_system_prompt_includes_output_format(self):
        """Test system prompt specifies output format."""
        prompt = self.builder.build_system_prompt(include_examples=False)

        assert "Output Format" in prompt
        assert "json" in prompt.lower()
        assert "sql" in prompt.lower()
        assert "explanation" in prompt.lower()

    def test_build_user_prompt_simple(self):
        """Test user prompt generation without context."""
        user_query = "Show me the slowest processes"
        prompt = self.builder.build_user_prompt(user_query)

        assert "User Query" in prompt
        assert user_query in prompt
        assert "SELECT" in prompt
        assert "Remember to" in prompt

    def test_build_user_prompt_with_context(self):
        """Test user prompt generation with context."""
        user_query = "Show me failed processes"
        context = {
            "tenant_id": "tenant_123",
            "time_range": "last 7 days"
        }
        prompt = self.builder.build_user_prompt(user_query, context)

        assert "Context" in prompt
        assert "tenant_123" in prompt
        assert "last 7 days" in prompt
        assert user_query in prompt

    def test_build_full_prompt(self):
        """Test full prompt generation."""
        user_query = "Find slow activities"
        system_prompt, user_prompt = self.builder.build_full_prompt(user_query)

        # System prompt checks
        assert len(system_prompt) > 1000  # Should be comprehensive
        assert "Role" in system_prompt
        assert "Schema" in system_prompt

        # User prompt checks
        assert user_query in user_prompt
        assert "User Query" in user_prompt

    def test_few_shot_examples_structure(self):
        """Test few-shot examples have correct structure."""
        examples = self.builder._get_few_shot_examples()

        assert len(examples) >= 5  # Should have at least 5 examples

        for example in examples:
            assert isinstance(example, FewShotExample)
            assert example.user_query
            assert example.sql
            assert example.explanation
            assert example.category

            # SQL should be valid format
            assert "SELECT" in example.sql.upper()
            assert "FROM" in example.sql.upper()

    def test_few_shot_examples_cover_categories(self):
        """Test few-shot examples cover different query types."""
        examples = self.builder._get_few_shot_examples()
        categories = {ex.category for ex in examples}

        # Should have diverse examples
        expected_categories = {'aggregation', 'simple_filter', 'drill_down', 'time_series'}
        assert len(categories.intersection(expected_categories)) >= 3

    def test_few_shot_examples_follow_best_practices(self):
        """Test few-shot examples follow SQL best practices."""
        examples = self.builder._get_few_shot_examples()

        for example in examples:
            sql_upper = example.sql.upper().strip()

            # Should use SELECT or WITH (for CTEs)
            assert sql_upper.startswith('SELECT') or sql_upper.startswith('WITH')

            # Should not have destructive operations
            assert 'DROP' not in sql_upper
            assert 'DELETE' not in sql_upper
            assert 'UPDATE' not in sql_upper or 'UPDATE_TIME' in sql_upper  # Allow column name

            # Should use allowed tables
            if 'FROM' in sql_upper:
                assert ('PE_EXT_PROCINST' in sql_upper or
                        'PE_EXT_ACTINST' in sql_upper or
                        'PE_EXT_VARINST' in sql_upper)

    def test_prompt_includes_duration_calculation(self):
        """Test prompt includes duration calculation pattern."""
        prompt = self.builder.build_system_prompt(include_examples=True)

        # Should show how to calculate duration
        assert "EXTRACT(EPOCH FROM" in prompt or "end_time - start_time" in prompt

    def test_prompt_includes_percentile_calculation(self):
        """Test prompt includes percentile calculation pattern."""
        prompt = self.builder.build_system_prompt(include_examples=True)

        # Should show how to calculate percentiles
        assert "PERCENTILE_CONT" in prompt

    def test_prompt_includes_common_filters(self):
        """Test prompt includes common filter patterns."""
        prompt = self.builder.build_system_prompt(include_examples=True)

        # Should mention common filters
        assert "status" in prompt.lower()
        assert "COMPLETED" in prompt
        assert "end_time IS NOT NULL" in prompt or "not null" in prompt.lower()

    def test_prompt_warns_about_debug_data(self):
        """Test prompt warns about excluding debug data."""
        prompt = self.builder.build_system_prompt(include_examples=False)

        # Should mention debug state exclusion
        assert "BREAKING" in prompt or "debug" in prompt.lower()

    def test_prompt_emphasizes_indexing(self):
        """Test prompt emphasizes using indexed columns."""
        prompt = self.builder.build_system_prompt(include_examples=False)

        # Should mention indexes
        assert "index" in prompt.lower() or "INDEXED" in prompt

    def test_prompt_length_reasonable(self):
        """Test prompt is comprehensive but not too long."""
        prompt = self.builder.build_system_prompt(include_examples=True)

        # Should be substantial but not excessive
        assert 5000 < len(prompt) < 50000  # Between 5K and 50K characters

    def test_context_with_additional_filters(self):
        """Test context with additional filters."""
        user_query = "Show processes"
        context = {
            "tenant_id": "tenant_123",
            "time_range": "last 30 days",
            "additional_filters": "status='COMPLETED'"
        }
        prompt = self.builder.build_user_prompt(user_query, context)

        assert "tenant_123" in prompt
        assert "last 30 days" in prompt
        assert "status='COMPLETED'" in prompt

    def test_empty_schema_dir_handling(self):
        """Test handling of missing schema directory."""
        # This should not crash, just have empty cache
        builder = TextToSQLPromptBuilder(schema_dir="nonexistent")
        assert len(builder.schema_cache) == 0

    def test_prompt_json_format_specification(self):
        """Test prompt specifies JSON output format clearly."""
        prompt = self.builder.build_system_prompt(include_examples=False)

        # Should specify JSON fields
        assert "sql" in prompt.lower()
        assert "explanation" in prompt.lower()
        assert "reasoning" in prompt.lower() or "caveats" in prompt.lower()


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
