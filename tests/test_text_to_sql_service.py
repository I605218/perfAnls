"""
Tests for Text-to-SQL Service.
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from anthropic.types import Message, ContentBlock, TextBlock

from app.services.text_to_sql_service import TextToSQLService, SQLGenerationResult


class TestTextToSQLService:
    """Test suite for TextToSQLService."""

    @pytest.fixture
    def mock_api_key(self):
        """Mock API key for testing."""
        return "test-api-key-12345"

    @pytest.fixture
    def service(self, mock_api_key):
        """Create service instance for testing."""
        with patch('app.services.text_to_sql_service.Anthropic'):
            service = TextToSQLService(
                api_key=mock_api_key,
                schema_dir="schema",
                validate_sql=True
            )
            return service

    def test_initialization(self, service):
        """Test service initialization."""
        assert service is not None
        assert service.model == "claude-opus-4-20250514"
        assert service.validate_sql is True
        assert service.prompt_builder is not None
        assert service.sql_validator is not None

    def test_initialization_with_custom_params(self, mock_api_key):
        """Test service initialization with custom parameters."""
        with patch('app.services.text_to_sql_service.Anthropic'):
            service = TextToSQLService(
                api_key=mock_api_key,
                base_url="http://custom-api.com",
                model="claude-sonnet-4-20250514",
                max_tokens=2048,
                temperature=0.3,
                validate_sql=False
            )

            assert service.model == "claude-sonnet-4-20250514"
            assert service.max_tokens == 2048
            assert service.temperature == 0.3
            assert service.validate_sql is False

    @patch('app.services.text_to_sql_service.Anthropic')
    def test_generate_sql_success(self, mock_anthropic_class, mock_api_key):
        """Test successful SQL generation."""
        # Mock Claude API response
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        mock_response = Mock(spec=Message)
        mock_content = Mock(spec=TextBlock)
        mock_content.text = json.dumps({
            "sql": "SELECT id, status FROM pe_ext_procinst LIMIT 10",
            "explanation": "This query retrieves process instances",
            "reasoning": "Simple SELECT on allowed table",
            "caveats": ["No time filter applied"],
            "performance_notes": "Uses primary key, very fast"
        })
        mock_response.content = [mock_content]

        mock_client.messages.create.return_value = mock_response

        # Create service and generate SQL
        service = TextToSQLService(api_key=mock_api_key, schema_dir="schema")
        result = service.generate_sql("Show me some process instances")

        # Verify result
        assert result.success
        assert result.sql is not None
        assert "SELECT" in result.sql
        assert result.explanation is not None
        assert result.validation_result is not None
        assert result.validation_result.is_valid

    @patch('app.services.text_to_sql_service.Anthropic')
    def test_generate_sql_with_context(self, mock_anthropic_class, mock_api_key):
        """Test SQL generation with context."""
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        mock_response = Mock(spec=Message)
        mock_content = Mock(spec=TextBlock)
        mock_content.text = json.dumps({
            "sql": "SELECT * FROM pe_ext_procinst WHERE tenant_id = 'tenant_123' LIMIT 10",
            "explanation": "Query with tenant filter",
            "reasoning": "Added tenant_id filter from context"
        })
        mock_response.content = [mock_content]
        mock_client.messages.create.return_value = mock_response

        service = TextToSQLService(api_key=mock_api_key, schema_dir="schema")
        context = {"tenant_id": "tenant_123", "time_range": "last 7 days"}

        result = service.generate_sql("Show processes", context=context)

        assert result.success
        assert result.sql is not None

        # Verify context was passed to prompt builder
        call_args = mock_client.messages.create.call_args
        assert call_args is not None

    @patch('app.services.text_to_sql_service.Anthropic')
    def test_generate_sql_validation_failure(self, mock_anthropic_class, mock_api_key):
        """Test SQL generation with validation failure."""
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        # Mock response with invalid SQL (DROP statement)
        mock_response = Mock(spec=Message)
        mock_content = Mock(spec=TextBlock)
        mock_content.text = json.dumps({
            "sql": "DROP TABLE pe_ext_procinst",
            "explanation": "This would drop the table",
            "reasoning": "Bad SQL"
        })
        mock_response.content = [mock_content]
        mock_client.messages.create.return_value = mock_response

        service = TextToSQLService(api_key=mock_api_key, schema_dir="schema")
        result = service.generate_sql("Delete all data")

        # Should fail validation
        assert not result.success
        assert result.validation_result is not None
        assert not result.validation_result.is_valid
        assert "DROP" in result.error_message

    @patch('app.services.text_to_sql_service.Anthropic')
    def test_generate_sql_api_error(self, mock_anthropic_class, mock_api_key):
        """Test handling of API errors."""
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client
        mock_client.messages.create.side_effect = Exception("API connection failed")

        service = TextToSQLService(api_key=mock_api_key, schema_dir="schema")
        result = service.generate_sql("Show processes")

        assert not result.success
        assert result.error_message is not None
        assert "API" in result.error_message or "Failed" in result.error_message

    @patch('app.services.text_to_sql_service.Anthropic')
    def test_generate_sql_invalid_json_response(self, mock_anthropic_class, mock_api_key):
        """Test handling of invalid JSON response."""
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        mock_response = Mock(spec=Message)
        mock_content = Mock(spec=TextBlock)
        mock_content.text = "This is not valid JSON"
        mock_response.content = [mock_content]
        mock_client.messages.create.return_value = mock_response

        service = TextToSQLService(api_key=mock_api_key, schema_dir="schema")
        result = service.generate_sql("Show processes")

        assert not result.success
        assert "parse" in result.error_message.lower()

    @patch('app.services.text_to_sql_service.Anthropic')
    def test_generate_sql_missing_sql_field(self, mock_anthropic_class, mock_api_key):
        """Test handling of response missing SQL field."""
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        mock_response = Mock(spec=Message)
        mock_content = Mock(spec=TextBlock)
        mock_content.text = json.dumps({
            "explanation": "Query explanation",
            "reasoning": "No SQL provided"
        })
        mock_response.content = [mock_content]
        mock_client.messages.create.return_value = mock_response

        service = TextToSQLService(api_key=mock_api_key, schema_dir="schema")
        result = service.generate_sql("Show processes")

        assert not result.success
        assert "parse" in result.error_message.lower()

    @patch('app.services.text_to_sql_service.Anthropic')
    def test_generate_sql_with_markdown_code_blocks(self, mock_anthropic_class, mock_api_key):
        """Test parsing JSON wrapped in markdown code blocks."""
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        mock_response = Mock(spec=Message)
        mock_content = Mock(spec=TextBlock)
        # Response wrapped in markdown
        mock_content.text = """```json
{
  "sql": "SELECT * FROM pe_ext_procinst LIMIT 10",
  "explanation": "Simple query",
  "reasoning": "Test"
}
```"""
        mock_response.content = [mock_content]
        mock_client.messages.create.return_value = mock_response

        service = TextToSQLService(api_key=mock_api_key, schema_dir="schema")
        result = service.generate_sql("Show processes")

        assert result.success
        assert result.sql is not None

    def test_parse_claude_response_valid_json(self, service):
        """Test parsing valid JSON response."""
        response = json.dumps({
            "sql": "SELECT * FROM pe_ext_procinst",
            "explanation": "Test query"
        })

        parsed = service._parse_claude_response(response)

        assert parsed is not None
        assert "sql" in parsed
        assert parsed["sql"] == "SELECT * FROM pe_ext_procinst"

    def test_parse_claude_response_with_code_blocks(self, service):
        """Test parsing JSON with markdown code blocks."""
        response = "```json\n{\"sql\": \"SELECT *\", \"explanation\": \"Test\"}\n```"

        parsed = service._parse_claude_response(response)

        assert parsed is not None
        assert "sql" in parsed

    def test_parse_claude_response_invalid(self, service):
        """Test parsing invalid JSON."""
        response = "This is not JSON"

        parsed = service._parse_claude_response(response)

        assert parsed is None

    def test_sql_generation_result_to_dict(self):
        """Test SQLGenerationResult to_dict conversion."""
        result = SQLGenerationResult(
            success=True,
            sql="SELECT * FROM pe_ext_procinst",
            explanation="Test query",
            reasoning="For testing",
            caveats=["No filter"],
            performance_notes="Fast query"
        )

        result_dict = result.to_dict()

        assert result_dict["success"] is True
        assert result_dict["sql"] == "SELECT * FROM pe_ext_procinst"
        assert result_dict["explanation"] == "Test query"
        assert result_dict["reasoning"] == "For testing"
        assert result_dict["caveats"] == ["No filter"]
        assert result_dict["performance_notes"] == "Fast query"

    def test_sql_generation_result_with_validation(self, service):
        """Test SQLGenerationResult with validation info."""
        from app.security.sql_validator import SQLValidationResult

        validation = service.sql_validator.validate("SELECT * FROM pe_ext_procinst LIMIT 10")

        result = SQLGenerationResult(
            success=True,
            sql="SELECT * FROM pe_ext_procinst LIMIT 10",
            explanation="Test",
            validation_result=validation
        )

        result_dict = result.to_dict()

        assert "validation" in result_dict
        assert result_dict["validation"]["is_valid"] is True
        assert "complexity" in result_dict["validation"]

    def test_explain_validation(self, service):
        """Test validation explanation."""
        from app.security.sql_validator import SQLValidationResult

        validation = service.sql_validator.validate("SELECT * FROM pe_ext_procinst LIMIT 10")

        result = SQLGenerationResult(
            success=True,
            sql="SELECT * FROM pe_ext_procinst LIMIT 10",
            validation_result=validation
        )

        explanation = service.explain_validation(result)

        assert explanation is not None
        assert len(explanation) > 0
        assert "Validated" in explanation or "Valid" in explanation

    def test_get_schema_summary(self, service):
        """Test getting schema summary."""
        summary = service.get_schema_summary()

        assert summary is not None
        assert len(summary) > 0
        # Should have our three tables if schemas are loaded
        if summary:
            assert isinstance(summary, dict)

    @patch('app.services.text_to_sql_service.Anthropic')
    def test_validation_disabled(self, mock_anthropic_class, mock_api_key):
        """Test SQL generation with validation disabled."""
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        mock_response = Mock(spec=Message)
        mock_content = Mock(spec=TextBlock)
        mock_content.text = json.dumps({
            "sql": "DROP TABLE pe_ext_procinst",  # Invalid SQL
            "explanation": "This would normally fail validation"
        })
        mock_response.content = [mock_content]
        mock_client.messages.create.return_value = mock_response

        # Create service with validation disabled
        service = TextToSQLService(
            api_key=mock_api_key,
            schema_dir="schema",
            validate_sql=False
        )

        result = service.generate_sql("Delete data")

        # Should succeed even with invalid SQL
        assert result.success
        assert result.validation_result is None

    @pytest.mark.asyncio
    async def test_generate_sql_async(self, service):
        """Test async SQL generation (currently wraps sync)."""
        with patch.object(service, 'generate_sql') as mock_sync:
            mock_sync.return_value = SQLGenerationResult(
                success=True,
                sql="SELECT * FROM pe_ext_procinst"
            )

            result = await service.generate_sql_async("Show processes")

            assert result.success
            assert mock_sync.called


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
