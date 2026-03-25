"""
Dynamic Query Analysis API endpoint.

This endpoint accepts natural language queries, converts them to SQL,
executes the query, and provides AI-powered analysis of the results.
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
import logging

from app.services.text_to_sql_service import TextToSQLService, SQLGenerationResult
from app.services.dynamic_query_service import DynamicQueryService, QueryResult
from app.services.ai_analysis_service import AIAnalysisService, AnalysisResult
from app.config import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analysis", tags=["Dynamic Analysis"])
settings = get_settings()


def get_security_level_from_validation(validation_result: Optional['SQLValidationResult']) -> str:
    """Determine security level from validation result."""
    if not validation_result:
        return "SAFE"

    if not validation_result.is_valid:
        # Check if there are CRITICAL severity issues
        for issue in validation_result.issues or []:
            if issue.severity == "CRITICAL":
                return "CRITICAL"
            if issue.severity == "HIGH":
                return "HIGH"
        return "WARNING"

    return "SAFE"


def get_complexity_from_validation(validation_result: Optional['SQLValidationResult']) -> Dict[str, int]:
    """Extract complexity metrics from validation result."""
    if not validation_result:
        return {}

    return {
        "tables": validation_result.table_count,
        "subqueries": 1 if validation_result.has_subquery else 0
    }


# Request/Response Models
class DynamicQueryRequest(BaseModel):
    """Request model for dynamic query endpoint."""
    query: str = Field(
        ...,
        description="Natural language query in Chinese or English",
        min_length=5,
        max_length=500,
        examples=["找出最慢的10个流程", "Show me failed processes in the last week"]
    )
    context: Optional[Dict[str, Any]] = Field(
        None,
        description="Optional context (tenant_id, time_range, etc.)",
        examples=[{"tenant_id": "tenant_123", "time_range": "last 7 days"}]
    )


class SQLValidationInfo(BaseModel):
    """SQL validation information."""
    is_valid: bool = Field(description="Whether the SQL passed validation")
    security_level: str = Field(description="Security level (SAFE, WARNING, CRITICAL)")
    issues: List[Dict[str, Any]] = Field(description="List of validation issues")
    complexity: Dict[str, int] = Field(description="Query complexity metrics")


class DynamicQueryResponse(BaseModel):
    """Response model for dynamic query endpoint."""
    success: bool = Field(description="Whether the request was successful")

    # SQL Generation
    sql: Optional[str] = Field(None, description="Generated SQL query")
    explanation: Optional[str] = Field(None, description="Explanation of the SQL query")
    reasoning: Optional[str] = Field(None, description="Reasoning behind the SQL generation")
    caveats: Optional[List[str]] = Field(None, description="Caveats about the query")
    performance_notes: Optional[str] = Field(None, description="Performance considerations")
    validation: Optional[SQLValidationInfo] = Field(None, description="SQL validation results")

    # Query Execution
    results: Optional[List[Dict[str, Any]]] = Field(None, description="Query results")
    row_count: Optional[int] = Field(None, description="Number of rows returned")
    columns: Optional[List[str]] = Field(None, description="Column names")
    execution_time_ms: Optional[float] = Field(None, description="Query execution time in milliseconds")

    # AI Analysis
    analysis: Optional[Dict[str, Any]] = Field(None, description="AI-powered analysis of results")

    # Error Information
    error: Optional[str] = Field(None, description="Error message if request failed")
    error_stage: Optional[str] = Field(
        None,
        description="Stage where error occurred (sql_generation, validation, execution, analysis)"
    )

    timestamp: str = Field(description="Response timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "sql": "SELECT id, proc_def_key, status, EXTRACT(EPOCH FROM (end_time - start_time)) as duration_seconds FROM pe_ext_procinst WHERE end_time IS NOT NULL ORDER BY duration_seconds DESC LIMIT 10",
                "explanation": "This query finds the 10 slowest completed process instances",
                "reasoning": "Filtered for completed processes, calculated duration, ordered by duration descending",
                "validation": {
                    "is_valid": True,
                    "security_level": "SAFE",
                    "issues": [],
                    "complexity": {"tables": 1, "joins": 0, "subqueries": 0}
                },
                "results": [
                    {"id": "proc-001", "proc_def_key": "OrderProcess", "status": "COMPLETED", "duration_seconds": 320.5}
                ],
                "row_count": 10,
                "columns": ["id", "proc_def_key", "status", "duration_seconds"],
                "execution_time_ms": 45.2,
                "analysis": {
                    "summary": "The 10 slowest processes show significant performance issues",
                    "key_findings": [
                        "OrderProcess averages 320 seconds, 50% slower than typical processes"
                    ],
                    "interpretation": "The data indicates performance bottlenecks...",
                    "recommendations": [
                        "Add database index on proc_def_key column",
                        "Optimize OrderProcess workflow"
                    ],
                    "visualization_suggestions": [
                        {
                            "chart_type": "bar chart",
                            "title": "Top 10 Slowest Processes",
                            "description": "Compare execution times",
                            "x_axis": "Process ID",
                            "y_axis": "Duration (seconds)"
                        }
                    ]
                },
                "timestamp": "2026-03-24T10:30:00"
            }
        }


# Initialize services (will be properly initialized at app startup)
text_to_sql_service: Optional[TextToSQLService] = None
query_service: Optional[DynamicQueryService] = None
analysis_service: Optional[AIAnalysisService] = None


def get_text_to_sql_service() -> TextToSQLService:
    """Get or initialize Text-to-SQL service."""
    global text_to_sql_service
    if text_to_sql_service is None:
        text_to_sql_service = TextToSQLService(
            api_key=settings.anthropic_api_key,
            base_url=settings.base_url,
            schema_dir="schema",
            validate_sql=True
        )
    return text_to_sql_service


def get_query_service() -> DynamicQueryService:
    """Get or initialize Query service."""
    global query_service
    if query_service is None:
        query_service = DynamicQueryService(
            database_url=settings.database_url,
            min_pool_size=settings.db_pool_min_size,
            max_pool_size=settings.db_pool_max_size,
            query_timeout=float(settings.db_timeout),
            max_rows=settings.max_query_results
        )
    return query_service


def get_analysis_service() -> AIAnalysisService:
    """Get or initialize Analysis service."""
    global analysis_service
    if analysis_service is None:
        analysis_service = AIAnalysisService(
            api_key=settings.anthropic_api_key,
            base_url=settings.base_url
        )
    return analysis_service


async def initialize_services():
    """Initialize all services (call at app startup)."""
    query_svc = get_query_service()
    await query_svc.initialize()
    logger.info("Dynamic analysis services initialized")


async def shutdown_services():
    """Shutdown all services (call at app shutdown)."""
    if query_service is not None:
        await query_service.close()
    logger.info("Dynamic analysis services shut down")


@router.post(
    "/query",
    response_model=DynamicQueryResponse,
    summary="Natural Language Query to SQL Analysis",
    description="""
    Execute a natural language query against the Process Engine database.

    **Workflow:**
    1. Convert natural language query to SQL using Claude AI
    2. Validate SQL for security and correctness
    3. Execute SQL query against database
    4. Analyze results with AI to provide insights

    **Features:**
    - Supports both Chinese and English queries
    - Automatic SQL security validation
    - Query timeout protection
    - AI-powered result analysis with recommendations
    - Visualization suggestions

    **Example Queries:**
    - "找出最慢的10个流程" (Find 10 slowest processes)
    - "Show me failed processes in the last week"
    - "统计每个流程定义的执行次数" (Count executions by process definition)
    - "What are the most common activity types?"
    """,
    responses={
        200: {"description": "Successfully executed query and analysis"},
        400: {"description": "Invalid request parameters"},
        500: {"description": "Internal server error"}
    }
)
async def execute_dynamic_query(
    request: DynamicQueryRequest,
    text_to_sql: TextToSQLService = Depends(get_text_to_sql_service),
    query_svc: DynamicQueryService = Depends(get_query_service),
    analysis_svc: AIAnalysisService = Depends(get_analysis_service)
) -> DynamicQueryResponse:
    """
    Execute a natural language query with AI-powered analysis.

    This endpoint orchestrates the complete workflow:
    1. SQL generation from natural language
    2. SQL validation and security checks
    3. Query execution with timeout protection
    4. AI analysis of results
    """

    try:
        logger.info(f"Received dynamic query request: {request.query[:100]}...")

        # Stage 1: Generate SQL from natural language
        logger.info("Stage 1: Generating SQL from natural language")
        sql_result: SQLGenerationResult = text_to_sql.generate_sql(
            user_query=request.query,
            context=request.context
        )

        if not sql_result.success:
            logger.warning(f"SQL generation failed: {sql_result.error_message}")
            return DynamicQueryResponse(
                success=False,
                error=sql_result.error_message or "Failed to generate SQL",
                error_stage="sql_generation",
                timestamp=datetime.now().isoformat()
            )

        # Stage 2: Validate SQL (already done in sql_result)
        if sql_result.validation_result and not sql_result.validation_result.is_valid:
            logger.warning("SQL validation failed")
            return DynamicQueryResponse(
                success=False,
                sql=sql_result.sql,
                explanation=sql_result.explanation,
                reasoning=sql_result.reasoning,
                validation=SQLValidationInfo(
                    is_valid=False,
                    security_level=get_security_level_from_validation(sql_result.validation_result),
                    issues=[issue.to_dict() for issue in sql_result.validation_result.issues],
                    complexity=get_complexity_from_validation(sql_result.validation_result)
                ),
                error="SQL validation failed. The generated SQL contains security issues or is not allowed.",
                error_stage="validation",
                timestamp=datetime.now().isoformat()
            )

        logger.info(f"Generated and validated SQL: {sql_result.sql[:100]}...")

        # Stage 3: Execute SQL query
        logger.info("Stage 3: Executing SQL query")
        query_result: QueryResult = await query_svc.execute_query(sql_result.sql)

        if not query_result.success:
            logger.error(f"Query execution failed: {query_result.error_message}")
            return DynamicQueryResponse(
                success=False,
                sql=sql_result.sql,
                explanation=sql_result.explanation,
                reasoning=sql_result.reasoning,
                validation=SQLValidationInfo(
                    is_valid=True,
                    security_level=get_security_level_from_validation(sql_result.validation_result),
                    issues=[],
                    complexity=get_complexity_from_validation(sql_result.validation_result)
                ) if sql_result.validation_result else None,
                error=query_result.error_message or "Query execution failed",
                error_stage="execution",
                timestamp=datetime.now().isoformat()
            )

        logger.info(f"Query executed successfully: {query_result.row_count} rows in {query_result.execution_time_ms:.2f}ms")

        # Stage 4: Analyze results with AI
        logger.info("Stage 4: Analyzing results with AI")
        analysis_result: AnalysisResult = analysis_svc.analyze_query_results(
            user_query=request.query,
            sql=sql_result.sql,
            results=query_result.rows or [],
            context=request.context
        )

        if not analysis_result.success:
            logger.warning(f"AI analysis failed: {analysis_result.error_message}")
            # Analysis failure is not critical - still return query results
            analysis_dict = {
                "error": analysis_result.error_message,
                "note": "Query executed successfully but AI analysis failed"
            }
        else:
            analysis_dict = {
                "summary": analysis_result.summary,
                "key_findings": analysis_result.key_findings,
                "interpretation": analysis_result.interpretation,
                "recommendations": analysis_result.recommendations,
                "visualization_suggestions": analysis_result.visualization_suggestions
            }

        # Return complete response
        return DynamicQueryResponse(
            success=True,
            sql=sql_result.sql,
            explanation=sql_result.explanation,
            reasoning=sql_result.reasoning,
            caveats=sql_result.caveats,
            performance_notes=sql_result.performance_notes,
            validation=SQLValidationInfo(
                is_valid=True,
                security_level=get_security_level_from_validation(sql_result.validation_result),
                issues=[],
                complexity=get_complexity_from_validation(sql_result.validation_result)
            ) if sql_result.validation_result else None,
            results=query_result.rows,
            row_count=query_result.row_count,
            columns=query_result.columns,
            execution_time_ms=query_result.execution_time_ms,
            analysis=analysis_dict,
            timestamp=datetime.now().isoformat()
        )

    except Exception as e:
        logger.error(f"Unexpected error in dynamic query execution: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.get(
    "/schema",
    summary="Get Database Schema Information",
    description="Retrieve schema information for available tables"
)
async def get_schema_info(
    text_to_sql: TextToSQLService = Depends(get_text_to_sql_service)
) -> Dict[str, Any]:
    """Get database schema summary."""
    try:
        schema_summary = text_to_sql.get_schema_summary()
        return {
            "success": True,
            "schema": schema_summary,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get schema info: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve schema information: {str(e)}"
        )
