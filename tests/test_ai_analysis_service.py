"""
Tests for AI Analysis Service.
"""

import pytest
import json
from unittest.mock import Mock, patch
from anthropic.types import Message, TextBlock

from app.services.ai_analysis_service import AIAnalysisService, AnalysisResult


class TestAIAnalysisService:
    """Test suite for AIAnalysisService."""

    @pytest.fixture
    def mock_api_key(self):
        """Mock API key."""
        return "test-api-key-12345"

    @pytest.fixture
    def service(self, mock_api_key):
        """Create service instance."""
        with patch('app.services.ai_analysis_service.Anthropic'):
            service = AIAnalysisService(api_key=mock_api_key)
            return service

    @pytest.fixture
    def sample_results(self):
        """Sample query results."""
        return [
            {"process_key": "OrderProcess", "avg_duration": 45.2, "count": 150},
            {"process_key": "ShipmentProcess", "avg_duration": 32.1, "count": 200},
            {"process_key": "InvoiceProcess", "avg_duration": 67.8, "count": 80}
        ]

    def test_initialization(self, service):
        """Test service initialization."""
        assert service is not None
        assert service.model == "claude-sonnet-4-20250514"
        assert service.temperature == 0.3

    def test_initialization_with_custom_params(self, mock_api_key):
        """Test initialization with custom parameters."""
        with patch('app.services.ai_analysis_service.Anthropic'):
            service = AIAnalysisService(
                api_key=mock_api_key,
                model="claude-opus-4-20250514",
                max_tokens=2048,
                temperature=0.5
            )

            assert service.model == "claude-opus-4-20250514"
            assert service.max_tokens == 2048
            assert service.temperature == 0.5

    @patch('app.services.ai_analysis_service.Anthropic')
    def test_analyze_query_results_success(
        self, mock_anthropic_class, mock_api_key, sample_results
    ):
        """Test successful analysis."""
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        mock_response = Mock(spec=Message)
        mock_content = Mock(spec=TextBlock)
        mock_content.text = json.dumps({
            "summary": "Processes show varying performance levels",
            "key_findings": [
                "InvoiceProcess is 50% slower than average",
                "ShipmentProcess handles highest volume"
            ],
            "interpretation": "The data shows performance bottlenecks in invoice processing",
            "recommendations": [
                "Optimize InvoiceProcess database queries",
                "Add caching for ShipmentProcess"
            ],
            "visualization_suggestions": [
                {
                    "chart_type": "bar chart",
                    "title": "Average Process Duration",
                    "description": "Compare execution times",
                    "x_axis": "Process",
                    "y_axis": "Duration (seconds)"
                }
            ]
        })
        mock_response.content = [mock_content]
        mock_client.messages.create.return_value = mock_response

        service = AIAnalysisService(api_key=mock_api_key)

        result = service.analyze_query_results(
            user_query="Show me the slowest processes",
            sql="SELECT * FROM pe_ext_procinst",
            results=sample_results
        )

        assert result.success
        assert result.summary is not None
        assert len(result.key_findings) == 2
        assert result.interpretation is not None
        assert len(result.recommendations) == 2
        assert len(result.visualization_suggestions) == 1

    @patch('app.services.ai_analysis_service.Anthropic')
    def test_analyze_query_results_with_context(
        self, mock_anthropic_class, mock_api_key, sample_results
    ):
        """Test analysis with context."""
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        mock_response = Mock(spec=Message)
        mock_content = Mock(spec=TextBlock)
        mock_content.text = json.dumps({
            "summary": "Test summary",
            "key_findings": ["Finding 1"],
            "interpretation": "Test interpretation",
            "recommendations": ["Recommendation 1"]
        })
        mock_response.content = [mock_content]
        mock_client.messages.create.return_value = mock_response

        service = AIAnalysisService(api_key=mock_api_key)

        context = {"tenant_id": "tenant_123", "time_range": "last 7 days"}
        result = service.analyze_query_results(
            user_query="Show processes",
            sql="SELECT * FROM pe_ext_procinst",
            results=sample_results,
            context=context
        )

        assert result.success

        # Verify context was included in prompt
        call_args = mock_client.messages.create.call_args
        assert call_args is not None
        user_message = call_args[1]["messages"][0]["content"]
        assert "tenant_123" in user_message
        assert "last 7 days" in user_message

    @patch('app.services.ai_analysis_service.Anthropic')
    def test_analyze_empty_results(self, mock_anthropic_class, mock_api_key):
        """Test analysis with empty results."""
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        mock_response = Mock(spec=Message)
        mock_content = Mock(spec=TextBlock)
        mock_content.text = json.dumps({
            "summary": "No data returned",
            "key_findings": ["Query returned no results"],
            "interpretation": "No processes match the filter criteria",
            "recommendations": ["Adjust query filters"]
        })
        mock_response.content = [mock_content]
        mock_client.messages.create.return_value = mock_response

        service = AIAnalysisService(api_key=mock_api_key)

        result = service.analyze_query_results(
            user_query="Show failed processes",
            sql="SELECT * FROM pe_ext_procinst WHERE status='FAILED'",
            results=[]
        )

        assert result.success

    @patch('app.services.ai_analysis_service.Anthropic')
    def test_analyze_large_results(self, mock_anthropic_class, mock_api_key):
        """Test analysis with large result set."""
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        mock_response = Mock(spec=Message)
        mock_content = Mock(spec=TextBlock)
        mock_content.text = json.dumps({
            "summary": "Large dataset analysis",
            "key_findings": ["High volume data"],
            "interpretation": "Analysis of 100 rows",
            "recommendations": ["Add pagination"]
        })
        mock_response.content = [mock_content]
        mock_client.messages.create.return_value = mock_response

        service = AIAnalysisService(api_key=mock_api_key)

        # Create 100 rows
        large_results = [
            {"id": i, "duration": i * 10}
            for i in range(100)
        ]

        result = service.analyze_query_results(
            user_query="Show all processes",
            sql="SELECT * FROM pe_ext_procinst",
            results=large_results
        )

        assert result.success

        # Verify results were truncated in prompt (should show first 25 + last 25)
        call_args = mock_client.messages.create.call_args
        user_message = call_args[1]["messages"][0]["content"]
        assert "first 25 and last 25" in user_message

    @patch('app.services.ai_analysis_service.Anthropic')
    def test_analyze_api_error(self, mock_anthropic_class, mock_api_key, sample_results):
        """Test handling of API errors."""
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client
        mock_client.messages.create.side_effect = Exception("API error")

        service = AIAnalysisService(api_key=mock_api_key)

        result = service.analyze_query_results(
            user_query="Show processes",
            sql="SELECT * FROM pe_ext_procinst",
            results=sample_results
        )

        assert not result.success
        assert result.error_message is not None
        assert "API" in result.error_message or "Failed" in result.error_message

    @patch('app.services.ai_analysis_service.Anthropic')
    def test_analyze_invalid_json_response(
        self, mock_anthropic_class, mock_api_key, sample_results
    ):
        """Test handling of invalid JSON response."""
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        mock_response = Mock(spec=Message)
        mock_content = Mock(spec=TextBlock)
        mock_content.text = "This is not valid JSON"
        mock_response.content = [mock_content]
        mock_client.messages.create.return_value = mock_response

        service = AIAnalysisService(api_key=mock_api_key)

        result = service.analyze_query_results(
            user_query="Show processes",
            sql="SELECT * FROM pe_ext_procinst",
            results=sample_results
        )

        assert not result.success
        assert "parse" in result.error_message.lower()

    def test_parse_response_with_markdown(self, service):
        """Test parsing response with markdown code blocks."""
        response = """```json
{
  "summary": "Test",
  "key_findings": ["Finding 1"],
  "interpretation": "Test interpretation",
  "recommendations": ["Rec 1"]
}
```"""

        parsed = service._parse_response(response)

        assert parsed is not None
        assert "summary" in parsed
        assert parsed["summary"] == "Test"

    def test_parse_response_missing_fields(self, service):
        """Test parsing response with missing required fields."""
        response = json.dumps({
            "summary": "Test"
            # Missing key_findings, interpretation, recommendations
        })

        parsed = service._parse_response(response)

        # Should still return parsed result but log warnings
        assert parsed is not None
        assert "summary" in parsed

    def test_analysis_result_to_dict(self):
        """Test AnalysisResult to_dict conversion."""
        result = AnalysisResult(
            success=True,
            summary="Test summary",
            key_findings=["Finding 1", "Finding 2"],
            interpretation="Test interpretation",
            recommendations=["Rec 1", "Rec 2"],
            visualization_suggestions=[
                {"chart_type": "bar", "title": "Test Chart"}
            ]
        )

        result_dict = result.to_dict()

        assert result_dict["success"] is True
        assert result_dict["summary"] == "Test summary"
        assert len(result_dict["key_findings"]) == 2
        assert result_dict["interpretation"] == "Test interpretation"
        assert len(result_dict["recommendations"]) == 2
        assert len(result_dict["visualization_suggestions"]) == 1

    def test_analysis_result_to_dict_with_error(self):
        """Test AnalysisResult to_dict with error."""
        result = AnalysisResult(
            success=False,
            error_message="Analysis failed"
        )

        result_dict = result.to_dict()

        assert result_dict["success"] is False
        assert result_dict["error"] == "Analysis failed"

    def test_generate_executive_summary(self, service):
        """Test executive summary generation."""
        analysis_results = [
            AnalysisResult(
                success=True,
                key_findings=["Finding 1", "Finding 2"],
                recommendations=["Rec 1", "Rec 2"]
            ),
            AnalysisResult(
                success=True,
                key_findings=["Finding 3"],
                recommendations=["Rec 3"]
            )
        ]

        summary = service.generate_executive_summary(analysis_results)

        assert summary is not None
        assert "Executive Summary" in summary
        assert "Key Findings" in summary
        assert "Recommendations" in summary
        assert "Finding 1" in summary
        assert "Rec 1" in summary

    def test_generate_executive_summary_empty(self, service):
        """Test executive summary with empty results."""
        summary = service.generate_executive_summary([])

        assert "No analysis results" in summary

    def test_build_system_prompt(self, service):
        """Test system prompt generation."""
        prompt = service._build_system_prompt()

        assert prompt is not None
        assert "Performance Analysis Expert" in prompt
        assert "Key Findings" in prompt
        assert "Recommendations" in prompt
        assert "JSON format" in prompt

    def test_build_user_prompt(self, service, sample_results):
        """Test user prompt generation."""
        prompt = service._build_user_prompt(
            user_query="Show slowest processes",
            sql="SELECT * FROM pe_ext_procinst",
            results=sample_results,
            context=None
        )

        assert prompt is not None
        assert "Show slowest processes" in prompt
        assert "SELECT * FROM pe_ext_procinst" in prompt
        assert "Total rows: 3" in prompt
        assert "OrderProcess" in prompt

    def test_build_user_prompt_with_context(self, service, sample_results):
        """Test user prompt generation with context."""
        context = {"tenant_id": "tenant_123", "time_range": "last 7 days"}
        prompt = service._build_user_prompt(
            user_query="Show processes",
            sql="SELECT * FROM pe_ext_procinst",
            results=sample_results,
            context=context
        )

        assert "tenant_123" in prompt
        assert "last 7 days" in prompt


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
