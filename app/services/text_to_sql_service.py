"""
Text-to-SQL Service for converting natural language to SQL queries.

This service integrates:
- TextToSQLPromptBuilder for prompt construction
- Claude AI for SQL generation
- SQLValidator for security validation
"""

import json
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass

from anthropic import Anthropic
from anthropic.types import Message

from app.prompts.text_to_sql_prompt import TextToSQLPromptBuilder
from app.security.sql_validator import SQLValidator, SQLValidationResult


logger = logging.getLogger(__name__)


@dataclass
class SQLGenerationResult:
    """Result of SQL generation from natural language."""
    success: bool
    sql: Optional[str] = None
    explanation: Optional[str] = None
    reasoning: Optional[str] = None
    caveats: Optional[list] = None
    performance_notes: Optional[str] = None
    validation_result: Optional[SQLValidationResult] = None
    error_message: Optional[str] = None
    raw_response: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        result = {
            "success": self.success,
            "sql": self.sql,
            "explanation": self.explanation,
            "reasoning": self.reasoning,
            "caveats": self.caveats,
            "performance_notes": self.performance_notes
        }

        if self.validation_result:
            result["validation"] = {
                "is_valid": self.validation_result.is_valid,
                "issues": [
                    {
                        "level": issue.level.value,
                        "message": issue.message
                    }
                    for issue in self.validation_result.issues
                ],
                "complexity": self.validation_result.estimated_complexity,
                "table_count": self.validation_result.table_count
            }

        if self.error_message:
            result["error"] = self.error_message

        return result


class TextToSQLService:
    """
    Service for converting natural language queries to SQL.

    This service orchestrates the entire Text-to-SQL pipeline:
    1. Build comprehensive prompts from schema and user query
    2. Call Claude AI to generate SQL
    3. Parse and validate the generated SQL
    4. Return structured results with validation status
    """

    def __init__(
        self,
        api_key: str,
        base_url: Optional[str] = None,
        schema_dir: str = "schema",
        model: str = "claude-sonnet-4-6",
        max_tokens: int = 4096,
        temperature: float = 0.0,
        validate_sql: bool = True
    ):
        """
        Initialize Text-to-SQL service.

        Args:
            api_key: Anthropic API key
            base_url: Optional custom API base URL (for proxy)
            schema_dir: Directory containing schema JSON files
            model: Claude model to use
            max_tokens: Maximum tokens for response
            temperature: Temperature for generation (0 = deterministic)
            validate_sql: Whether to validate generated SQL
        """
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.validate_sql = validate_sql

        # Initialize components
        self.client = Anthropic(api_key=api_key, base_url=base_url)
        self.prompt_builder = TextToSQLPromptBuilder(schema_dir=schema_dir)
        self.sql_validator = SQLValidator()

        logger.info(
            f"TextToSQLService initialized with model={model}, "
            f"schema_dir={schema_dir}, validate_sql={validate_sql}"
        )

    def generate_sql(
        self,
        user_query: str,
        context: Optional[Dict[str, Any]] = None,
        include_examples: bool = True
    ) -> SQLGenerationResult:
        """
        Generate SQL from natural language query.

        Args:
            user_query: Natural language query from user
            context: Optional context (tenant_id, time_range, etc.)
            include_examples: Whether to include few-shot examples in prompt

        Returns:
            SQLGenerationResult with generated SQL and validation status
        """
        try:
            logger.info(f"Generating SQL for query: {user_query[:100]}...")

            # Step 1: Build prompts
            system_prompt, user_prompt = self.prompt_builder.build_full_prompt(
                user_query=user_query,
                context=context,
                include_examples=include_examples
            )

            logger.debug(f"System prompt length: {len(system_prompt)} chars")
            logger.debug(f"User prompt length: {len(user_prompt)} chars")

            # Step 2: Call Claude API
            response = self._call_claude_api(system_prompt, user_prompt)

            if not response:
                return SQLGenerationResult(
                    success=False,
                    error_message="Failed to get response from Claude API"
                )

            logger.debug(f"Received response from Claude, length: {len(response)} chars")
            logger.debug(f"Response preview (first 300 chars): {response[:300]}")

            # Check if response contains a scope error before parsing
            if "SCOPE_ERROR" in response:
                logger.warning("Claude rejected query due to scope")
                # Try to extract the error message
                try:
                    response_stripped = response.strip()
                    if response_stripped.startswith("```json"):
                        response_stripped = response_stripped[7:]
                    if response_stripped.startswith("```"):
                        response_stripped = response_stripped[3:]
                    if response_stripped.endswith("```"):
                        response_stripped = response_stripped[:-3]
                    response_stripped = response_stripped.strip()

                    error_data = json.loads(response_stripped)
                    error_msg = error_data.get("message", "Query is not related to process engine analysis")

                    return SQLGenerationResult(
                        success=False,
                        error_message=error_msg,
                        raw_response=response[:1000]
                    )
                except:
                    return SQLGenerationResult(
                        success=False,
                        error_message="Query is not related to process engine performance analysis. Please ask questions about process execution, performance metrics, or failure analysis.",
                        raw_response=response[:1000]
                    )

            # Step 3: Parse response
            parsed_result = self._parse_claude_response(response)

            if not parsed_result:
                return SQLGenerationResult(
                    success=False,
                    error_message="Failed to parse Claude response",
                    raw_response=response[:1000]  # Include partial response for debugging
                )

            logger.info(f"Successfully parsed SQL: {parsed_result.get('sql', '')[:100]}...")

            # Step 4: Validate SQL if enabled
            validation_result = None
            if self.validate_sql and parsed_result.get("sql"):
                validation_result = self.sql_validator.validate(parsed_result["sql"])

                if not validation_result.is_valid:
                    logger.warning(
                        f"Generated SQL failed validation: "
                        f"{validation_result.errors}"
                    )
                    return SQLGenerationResult(
                        success=False,
                        sql=parsed_result.get("sql"),
                        explanation=parsed_result.get("explanation"),
                        validation_result=validation_result,
                        error_message=f"SQL validation failed: {'; '.join(validation_result.errors)}"
                    )

                # Use cleaned SQL from validator
                parsed_result["sql"] = validation_result.cleaned_sql

                logger.info(
                    f"SQL validated successfully - "
                    f"complexity={validation_result.estimated_complexity}, "
                    f"tables={validation_result.table_count}"
                )

            # Step 5: Return successful result
            return SQLGenerationResult(
                success=True,
                sql=parsed_result.get("sql"),
                explanation=parsed_result.get("explanation"),
                reasoning=parsed_result.get("reasoning"),
                caveats=parsed_result.get("caveats"),
                performance_notes=parsed_result.get("performance_notes"),
                validation_result=validation_result,
                raw_response=response[:500]  # Include partial for debugging
            )

        except Exception as e:
            logger.error(f"Error generating SQL: {str(e)}", exc_info=True)
            return SQLGenerationResult(
                success=False,
                error_message=f"Internal error: {str(e)}"
            )

    def _call_claude_api(self, system_prompt: str, user_prompt: str) -> Optional[str]:
        """
        Call Claude API to generate SQL.

        Args:
            system_prompt: System prompt with schema and instructions
            user_prompt: User query prompt

        Returns:
            Response text or None if failed
        """
        try:
            response: Message = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system=system_prompt,
                messages=[
                    {
                        "role": "user",
                        "content": user_prompt
                    }
                ]
            )

            # Extract text content from response
            if response.content and len(response.content) > 0:
                content_block = response.content[0]
                if hasattr(content_block, 'text'):
                    return content_block.text

            logger.error("Claude API response has no text content")
            return None

        except Exception as e:
            logger.error(f"Claude API call failed: {str(e)}", exc_info=True)
            return None

    def _parse_claude_response(self, response: str) -> Optional[Dict[str, Any]]:
        """
        Parse Claude's JSON response.

        Expected format:
        {
          "sql": "SELECT ...",
          "explanation": "...",
          "reasoning": "...",
          "caveats": ["..."],
          "performance_notes": "..."
        }

        OR (for scope errors):
        {
          "error": "SCOPE_ERROR",
          "message": "...",
          "examples": [...]
        }

        Args:
            response: Raw response text from Claude

        Returns:
            Parsed dictionary or None if parsing failed
        """
        try:
            # Try to extract JSON from response
            # Claude might wrap JSON in markdown code blocks
            response = response.strip()

            # Remove markdown code blocks if present
            if response.startswith("```json"):
                response = response[7:]  # Remove ```json
            if response.startswith("```"):
                response = response[3:]  # Remove ```
            if response.endswith("```"):
                response = response[:-3]  # Remove trailing ```

            response = response.strip()

            # Parse JSON
            parsed = json.loads(response)

            # Check if it's a scope error (invalid query)
            if "error" in parsed and parsed.get("error") == "SCOPE_ERROR":
                logger.warning(f"Query rejected due to scope: {parsed.get('message')}")
                # Return None to trigger error handling, but set a specific error
                return None

            # Validate required fields for normal responses
            if "sql" not in parsed:
                logger.error("Response missing 'sql' field")
                return None

            return parsed

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {str(e)}")
            logger.error(f"Error at line {e.lineno}, column {e.colno}")
            logger.error(f"Full response (first 2000 chars):\n{response[:2000]}")

            # Try to extract JSON using regex as fallback
            try:
                import re
                # Find JSON object in the response
                json_match = re.search(r'\{[\s\S]*\}', response, re.MULTILINE)
                if json_match:
                    json_str = json_match.group(0)
                    logger.info("Attempting to parse extracted JSON block")
                    parsed = json.loads(json_str)

                    # Check for scope error in extracted JSON
                    if "error" in parsed and parsed.get("error") == "SCOPE_ERROR":
                        logger.warning("Extracted JSON contains scope error")
                        return None

                    if "sql" in parsed:
                        logger.info("Successfully extracted and parsed JSON from response")
                        return parsed
            except Exception as fallback_error:
                logger.error(f"Fallback JSON extraction also failed: {str(fallback_error)}")

            return None

        except Exception as e:
            logger.error(f"Error parsing response: {str(e)}", exc_info=True)
            logger.error(f"Response preview: {response[:500]}...")
            return None

    def explain_validation(self, result: SQLGenerationResult) -> str:
        """
        Generate human-readable explanation of validation result.

        Args:
            result: SQLGenerationResult to explain

        Returns:
            Formatted explanation string
        """
        if not result.validation_result:
            return "No validation performed"

        return self.sql_validator.explain_validation(result.validation_result)

    def get_schema_summary(self) -> Dict[str, Any]:
        """Get summary of loaded database schemas."""
        return self.prompt_builder.get_schema_summary()

    async def generate_sql_async(
        self,
        user_query: str,
        context: Optional[Dict[str, Any]] = None,
        include_examples: bool = True
    ) -> SQLGenerationResult:
        """
        Async version of generate_sql.

        Note: Currently wraps sync implementation.
        Can be enhanced with async Anthropic client in the future.

        Args:
            user_query: Natural language query from user
            context: Optional context (tenant_id, time_range, etc.)
            include_examples: Whether to include few-shot examples

        Returns:
            SQLGenerationResult with generated SQL and validation status
        """
        # For now, just call sync version
        # In production, consider using async Anthropic client
        return self.generate_sql(user_query, context, include_examples)
