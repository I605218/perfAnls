"""
Tests for Dynamic Analysis API endpoint.
"""

import pytest
import json
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from anthropic.types import Message, TextBlock

from app.api.v1.endpoints.dynamic_analysis import router
from app.services.text_to_sql_service import SQLGenerationResult
from app.services.dynamic_query_service import QueryResult
from app.services.ai_analysis_service import AnalysisResult
from app.security.sql_validator import SQLValidationResult, ValidationIssue


@pytest.fixture
def mock_services():
    """Mock all three services together."""
    text_to_sql_mock = Mock()
    query_mock = Mock()
    analysis_mock = Mock()

    with patch('app.api.v1.endpoints.dynamic_analysis.TextToSQLService', return_value=text_to_sql_mock), \
         patch('app.api.v1.endpoints.dynamic_analysis.DynamicQueryService', return_value=query_mock), \
         patch('app.api.v1.endpoints.dynamic_analysis.AIAnalysisService', return_value=analysis_mock):
        yield text_to_sql_mock, query_mock, analysis_mock


@pytest.fixture
def client():
    """Create test client."""
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_successful_query_execution(client, mock_services):
    """Test successful complete query execution."""
    text_to_sql_mock, query_mock, analysis_mock = mock_services

    # Mock SQL generation
    validation_result = SQLValidationResult(
        is_valid=True,
        issues=[],
        table_count=1,
        has_subquery=False,
        estimated_complexity="low"
    )
    sql_result = SQLGenerationResult(
        success=True,
        sql="SELECT * FROM pe_ext_procinst LIMIT 10",
        explanation="Retrieve 10 process instances",
        reasoning="Simple SELECT query",
        caveats=["No time filter"],
        performance_notes="Fast query",
        validation_result=validation_result
    )
    text_to_sql_mock.generate_sql.return_value = sql_result

    # Mock query execution
    query_result = QueryResult(
        success=True,
        rows=[{"id": "1", "status": "COMPLETED"}],
        row_count=1,
        columns=["id", "status"],
        execution_time_ms=45.2
    )
    query_mock.execute_query = AsyncMock(return_value=query_result)

    # Mock analysis
    analysis_result = AnalysisResult(
        success=True,
        summary="Test summary",
        key_findings=["Finding 1"],
        interpretation="Test interpretation",
        recommendations=["Recommendation 1"],
        visualization_suggestions=[{"chart_type": "bar"}]
    )
    analysis_mock.analyze_query_results.return_value = analysis_result

    # Make request
    response = client.post(
        "/analysis/query",
        json={"query": "Show me some process instances"}
    )

    # Verify response
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["sql"] == "SELECT * FROM pe_ext_procinst LIMIT 10"
    assert data["explanation"] == "Retrieve 10 process instances"
    assert data["row_count"] == 1
    assert data["execution_time_ms"] == 45.2
    assert "analysis" in data
    assert data["analysis"]["summary"] == "Test summary"


def test_sql_generation_failure(client, mock_services):
    """Test SQL generation failure."""
    text_to_sql_mock, _, _ = mock_services

    sql_result = SQLGenerationResult(
        success=False,
        error_message="Failed to parse natural language query"
    )
    text_to_sql_mock.generate_sql.return_value = sql_result

    response = client.post(
        "/analysis/query",
        json={"query": "Invalid query"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert data["error_stage"] == "sql_generation"
    assert data["error"] is not None


def test_sql_validation_failure(client, mock_services):
    """Test SQL validation failure."""
    text_to_sql_mock, _, _ = mock_services

    validation_result = SQLValidationResult(
        is_valid=False,
        issues=[
            ValidationIssue(
                severity="CRITICAL",
                message="DROP statements not allowed",
                location="query"
            )
        ],
        table_count=1,
        has_subquery=False,
        estimated_complexity="low"
    )
    sql_result = SQLGenerationResult(
        success=True,
        sql="DROP TABLE pe_ext_procinst",
        explanation="Drop table",
        validation_result=validation_result
    )
    text_to_sql_mock.generate_sql.return_value = sql_result

    response = client.post(
        "/analysis/query",
        json={"query": "Delete all data"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert data["error_stage"] == "validation"
    assert "validation failed" in data["error"].lower()


def test_query_execution_failure(client, mock_services):
    """Test query execution failure."""
    text_to_sql_mock, query_mock, _ = mock_services

    validation_result = SQLValidationResult(
        is_valid=True,
        issues=[],
        table_count=1,
        has_subquery=False,
        estimated_complexity="low"
    )
    sql_result = SQLGenerationResult(
        success=True,
        sql="SELECT * FROM pe_ext_procinst",
        validation_result=validation_result
    )
    text_to_sql_mock.generate_sql.return_value = sql_result

    query_result = QueryResult(
        success=False,
        error_message="Database connection failed"
    )
    query_mock.execute_query = AsyncMock(return_value=query_result)

    response = client.post(
        "/analysis/query",
        json={"query": "Show processes"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert data["error_stage"] == "execution"
    assert "connection failed" in data["error"].lower()


def test_analysis_failure_non_critical(client, mock_services):
    """Test that analysis failure doesn't fail the whole request."""
    text_to_sql_mock, query_mock, analysis_mock = mock_services

    validation_result = SQLValidationResult(
        is_valid=True,
        issues=[],
        table_count=1,
        has_subquery=False,
        estimated_complexity="low"
    )
    sql_result = SQLGenerationResult(
        success=True,
        sql="SELECT * FROM pe_ext_procinst LIMIT 10",
        validation_result=validation_result
    )
    text_to_sql_mock.generate_sql.return_value = sql_result

    query_result = QueryResult(
        success=True,
        rows=[{"id": "1"}],
        row_count=1,
        columns=["id"],
        execution_time_ms=30.0
    )
    query_mock.execute_query = AsyncMock(return_value=query_result)

    analysis_result = AnalysisResult(
        success=False,
        error_message="AI analysis timeout"
    )
    analysis_mock.analyze_query_results.return_value = analysis_result

    response = client.post(
        "/analysis/query",
        json={"query": "Show processes"}
    )

    # Should still succeed even if analysis fails
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["row_count"] == 1
    assert "error" in data["analysis"]


def test_query_with_context(client, mock_services):
    """Test query execution with context."""
    text_to_sql_mock, query_mock, analysis_mock = mock_services

    validation_result = SQLValidationResult(
        is_valid=True,
        issues=[],
        table_count=1,
        has_subquery=False,
        estimated_complexity="low"
    )
    sql_result = SQLGenerationResult(
        success=True,
        sql="SELECT * FROM pe_ext_procinst WHERE tenant_id = 'tenant_123'",
        validation_result=validation_result
    )
    text_to_sql_mock.generate_sql.return_value = sql_result

    query_result = QueryResult(
        success=True,
        rows=[],
        row_count=0,
        columns=[],
        execution_time_ms=10.0
    )
    query_mock.execute_query = AsyncMock(return_value=query_result)

    analysis_result = AnalysisResult(
        success=True,
        summary="No data",
        key_findings=[],
        interpretation="Empty result",
        recommendations=[]
    )
    analysis_mock.analyze_query_results.return_value = analysis_result

    response = client.post(
        "/analysis/query",
        json={
            "query": "Show processes",
            "context": {"tenant_id": "tenant_123", "time_range": "last 7 days"}
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True

    # Verify context was passed
    text_to_sql_mock.generate_sql.assert_called_once()
    call_args = text_to_sql_mock.generate_sql.call_args
    assert call_args[1]["context"] == {"tenant_id": "tenant_123", "time_range": "last 7 days"}


def test_invalid_request_payload(client):
    """Test invalid request payload."""
    response = client.post(
        "/analysis/query",
        json={"invalid_field": "value"}
    )

    assert response.status_code == 422  # Validation error


def test_empty_query(client):
    """Test empty query string."""
    response = client.post(
        "/analysis/query",
        json={"query": ""}
    )

    assert response.status_code == 422  # Validation error


def test_query_too_long(client):
    """Test query exceeding max length."""
    response = client.post(
        "/analysis/query",
        json={"query": "a" * 501}  # Exceeds 500 char limit
    )

    assert response.status_code == 422  # Validation error


def test_get_schema_info(client, mock_services):
    """Test schema information endpoint."""
    text_to_sql_mock, _, _ = mock_services

    text_to_sql_mock.get_schema_summary.return_value = {
        "pe_ext_procinst": {"columns": ["id", "status"]},
        "pe_ext_actinst": {"columns": ["id", "activity_id"]},
        "pe_ext_varinst": {"columns": ["id", "name", "value"]}
    }

    response = client.get("/analysis/schema")

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "schema" in data
    assert "pe_ext_procinst" in data["schema"]


def test_unexpected_exception(client, mock_services):
    """Test handling of unexpected exceptions."""
    text_to_sql_mock, _, _ = mock_services

    text_to_sql_mock.generate_sql.side_effect = Exception("Unexpected error")

    response = client.post(
        "/analysis/query",
        json={"query": "Show processes"}
    )

    assert response.status_code == 500
    data = response.json()
    assert "Internal server error" in data["detail"]


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
