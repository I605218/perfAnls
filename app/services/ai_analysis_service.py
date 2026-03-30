"""
AI Analysis Service for analyzing SQL query results.

This service uses Claude AI to:
- Interpret query results with business context
- Generate actionable insights
- Provide optimization recommendations
- Suggest visualizations
"""

import json
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from anthropic import Anthropic
from anthropic.types import Message


logger = logging.getLogger(__name__)


@dataclass
class AnalysisResult:
    """Result of AI analysis on query data."""
    success: bool
    key_findings: Optional[List[str]] = None
    interpretation: Optional[str] = None
    recommendations: Optional[List[str]] = None
    visualization_suggestions: Optional[List[Dict[str, str]]] = None
    summary: Optional[str] = None
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "success": self.success,
            "summary": self.summary,
            "key_findings": self.key_findings,
            "interpretation": self.interpretation,
            "recommendations": self.recommendations,
            "visualization_suggestions": self.visualization_suggestions,
            "error": self.error_message
        }


class AIAnalysisService:
    """
    Service for AI-powered analysis of query results.

    This service takes SQL query results and provides:
    - Business-focused interpretation
    - Key findings and patterns
    - Actionable recommendations
    - Visualization suggestions
    """

    def __init__(
        self,
        api_key: str,
        base_url: Optional[str] = None,
        model: str = "claude-haiku-4-5",
        max_tokens: int = 4096,
        temperature: float = 0.3
    ):
        """
        Initialize AI analysis service.

        Args:
            api_key: Anthropic API key
            base_url: Optional custom API base URL
            model: Claude model to use (Sonnet for analysis)
            max_tokens: Maximum tokens for response
            temperature: Temperature for generation (0.3 for balanced creativity)
        """
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature

        self.client = Anthropic(api_key=api_key, base_url=base_url)

        logger.info(f"AIAnalysisService initialized with model={model}")

    def analyze_query_results(
        self,
        user_query: str,
        sql: str,
        results: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> AnalysisResult:
        """
        Analyze SQL query results and provide insights.

        Args:
            user_query: Original natural language query
            sql: SQL query that was executed
            results: Query results (list of row dictionaries)
            context: Optional context (tenant_id, time_range, etc.)

        Returns:
            AnalysisResult with insights and recommendations
        """
        try:
            logger.info(
                f"Analyzing results for query: {user_query[:100]}... "
                f"({len(results)} rows)"
            )

            # Build analysis prompt
            system_prompt = self._build_system_prompt()
            user_prompt = self._build_user_prompt(
                user_query, sql, results, context
            )

            logger.debug(f"System prompt length: {len(system_prompt)} chars")
            logger.debug(f"User prompt length: {len(user_prompt)} chars")

            # Call Claude API
            response = self._call_claude_api(system_prompt, user_prompt)

            if not response:
                return AnalysisResult(
                    success=False,
                    error_message="Failed to get response from Claude API"
                )

            logger.debug(f"Claude response length: {len(response)} chars")
            logger.debug(f"Claude response preview: {response[:300]}...")

            # Parse response
            parsed_result = self._parse_response(response)

            if not parsed_result:
                # Log the full response for debugging
                logger.error(f"Failed to parse response. Full response:\n{response}")
                return AnalysisResult(
                    success=False,
                    error_message="Failed to parse analysis response. The AI response was not in valid JSON format."
                )

            logger.info("Analysis completed successfully")

            return AnalysisResult(
                success=True,
                key_findings=parsed_result.get("key_findings"),
                interpretation=parsed_result.get("interpretation"),
                recommendations=parsed_result.get("recommendations"),
                visualization_suggestions=parsed_result.get("visualization_suggestions"),
                summary=parsed_result.get("summary")
            )

        except Exception as e:
            logger.error(f"Error analyzing results: {str(e)}", exc_info=True)
            return AnalysisResult(
                success=False,
                error_message=f"Internal error: {str(e)}"
            )

    def _build_system_prompt(self) -> str:
        """Build system prompt for analysis."""
        return """# Role: Process Engine Performance Analysis Expert

You are an expert in analyzing SAP Digital Manufacturing Process Engine performance data. Your task is to analyze query results and provide actionable insights for performance optimization.

## Your Responsibilities
- Interpret data in business context (not just raw numbers)
- Identify key patterns, trends, and anomalies
- Provide specific, actionable recommendations
- Suggest appropriate visualizations for the data
- Focus on performance bottlenecks and optimization opportunities

## Analysis Framework

### Key Findings
- Identify 3-5 most important observations from the data
- Quantify findings with specific numbers when possible
- Highlight unusual patterns or outliers

### Data Interpretation
- Explain what the data means for business operations
- Contextualize performance metrics (is it good/bad/concerning?)
- Identify root causes of performance issues
- Compare against typical benchmarks when relevant

### Recommendations
- Provide 3-5 specific, actionable recommendations
- Prioritize by impact and feasibility
- Include both quick wins and long-term improvements
- Focus on:
  - Query optimization (indexes, query structure)
  - Process design improvements (reduce activities, parallelize)
  - System configuration (timeouts, pooling, caching)
  - Data management (variable size, cleanup policies)

### Visualization Suggestions
- Recommend appropriate chart types for the data
- Suggest key metrics to visualize
- Consider time-series trends, distributions, comparisons

## Output Format

**CRITICAL**: You MUST respond with ONLY valid JSON. No additional text before or after the JSON object.

Respond in this exact JSON format:
```json
{
  "summary": "One-sentence executive summary",
  "key_findings": [
    "Finding 1 with specific numbers",
    "Finding 2...",
    "..."
  ],
  "interpretation": "Detailed explanation of what the data means (2-3 paragraphs)",
  "recommendations": [
    "Specific recommendation 1",
    "Specific recommendation 2",
    "..."
  ],
  "visualization_suggestions": [
    {
      "chart_type": "bar chart / line chart / scatter plot / heatmap / etc.",
      "title": "Chart title",
      "description": "What to show and why it's useful",
      "x_axis": "X-axis metric",
      "y_axis": "Y-axis metric"
    }
  ]
}
```

## JSON Formatting Rules (CRITICAL!)
- All string values must be properly escaped
- Use \\n for newlines in strings (not actual newlines)
- Use \\" for quotes inside strings
- Arrays must use valid JSON array syntax
- Do NOT include any text outside the JSON object
- Do NOT add markdown code blocks around the JSON
- Ensure all brackets and braces are properly matched

## Important Guidelines
- Be concise but insightful
- Focus on actionable insights, not just describing data
- Use domain-specific terminology (process instances, activities, variables)
- Quantify impact when possible ("25% slower", "300ms overhead")
- Consider both technical and business perspectives"""

    def _build_user_prompt(
        self,
        user_query: str,
        sql: str,
        results: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]]
    ) -> str:
        """Build user prompt with query and results."""
        parts = []

        # Add context if available
        if context:
            parts.append("# Context")
            if context.get("tenant_id"):
                parts.append(f"- Tenant: {context['tenant_id']}")
            if context.get("time_range"):
                parts.append(f"- Time Range: {context['time_range']}")
            parts.append("")

        # Add original query
        parts.append("# User Query")
        parts.append(user_query)
        parts.append("")

        # Add SQL (for reference)
        parts.append("# SQL Executed")
        parts.append(f"```sql\n{sql}\n```")
        parts.append("")

        # Add results summary
        parts.append("# Query Results")
        parts.append(f"Total rows: {len(results)}")

        if results:
            # Show column names
            columns = list(results[0].keys())
            parts.append(f"Columns: {', '.join(columns)}")
            parts.append("")

            # Include results (limit to avoid token overflow)
            max_rows = 50
            if len(results) <= max_rows:
                parts.append("Data:")
                parts.append("```json")
                parts.append(json.dumps(results, indent=2, default=str))
                parts.append("```")
            else:
                # Show first 25 and last 25 rows
                parts.append(f"Data (showing first 25 and last 25 of {len(results)} rows):")
                parts.append("```json")
                sample_results = results[:25] + results[-25:]
                parts.append(json.dumps(sample_results, indent=2, default=str))
                parts.append("```")
        else:
            parts.append("")
            parts.append("⚠️ **Empty Result Set**: The query returned no data.")
            parts.append("")
            parts.append("**Important**: When analyzing empty results, focus on:")
            parts.append("- Why the query might return no data (data availability, time range, filters)")
            parts.append("- Whether this is expected or indicates an issue")
            parts.append("- What actions the user should take (expand time range, check data source, verify filters)")
            parts.append("- Provide meaningful insights even with zero rows")

        parts.append("")
        parts.append("Please analyze these results and provide insights in the specified JSON format.")
        parts.append("")
        parts.append("**Remember**: Even with empty results, provide valuable analysis about what this means and what to do next.")

        return "\n".join(parts)

    def _call_claude_api(self, system_prompt: str, user_prompt: str) -> Optional[str]:
        """Call Claude API for analysis."""
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

            if response.content and len(response.content) > 0:
                content_block = response.content[0]
                if hasattr(content_block, 'text'):
                    return content_block.text

            logger.error("Claude API response has no text content")
            return None

        except Exception as e:
            logger.error(f"Claude API call failed: {str(e)}", exc_info=True)
            return None

    def _parse_response(self, response: str) -> Optional[Dict[str, Any]]:
        """Parse Claude's JSON response with robust error handling."""
        try:
            # Step 1: Clean the response
            response = response.strip()

            # Step 2: Remove ALL markdown code blocks (more aggressive)
            # Handle cases like "```json\n{...}\n```" or "```\n{...}\n```"
            import re

            # Remove markdown code block markers
            response = re.sub(r'^```json\s*', '', response, flags=re.IGNORECASE | re.MULTILINE)
            response = re.sub(r'^```\s*', '', response, flags=re.MULTILINE)
            response = re.sub(r'\s*```\s*$', '', response, flags=re.MULTILINE)

            response = response.strip()

            # Step 3: Try to extract JSON using multiple strategies
            parsed = None
            parse_method = None

            # Strategy 1: Direct parse
            try:
                parsed = json.loads(response)
                parse_method = "direct"
                logger.info("Successfully parsed JSON (direct)")
            except json.JSONDecodeError as e:
                logger.debug(f"Direct parse failed: {str(e)} at line {e.lineno}, col {e.colno}")

            # Strategy 2: Extract first complete JSON object using brace matching
            if parsed is None:
                try:
                    # Find the first '{' and matching '}'
                    start_idx = response.find('{')
                    if start_idx != -1:
                        # Count braces to find matching closing brace
                        brace_count = 0
                        end_idx = -1
                        in_string = False
                        escape_next = False

                        for i in range(start_idx, len(response)):
                            char = response[i]

                            # Handle string escaping
                            if escape_next:
                                escape_next = False
                                continue

                            if char == '\\':
                                escape_next = True
                                continue

                            # Track if we're inside a string
                            if char == '"':
                                in_string = not in_string
                                continue

                            # Only count braces outside strings
                            if not in_string:
                                if char == '{':
                                    brace_count += 1
                                elif char == '}':
                                    brace_count -= 1
                                    if brace_count == 0:
                                        end_idx = i + 1
                                        break

                        if end_idx != -1:
                            json_str = response[start_idx:end_idx]
                            parsed = json.loads(json_str)
                            parse_method = "brace_matching"
                            logger.info(f"Successfully extracted JSON using brace matching")
                            if len(response) > end_idx:
                                logger.warning(f"Removed {len(response) - end_idx} extra characters after JSON")
                except Exception as e:
                    logger.debug(f"Brace matching extraction failed: {str(e)}")

            # Strategy 3: Regex extraction (fallback)
            if parsed is None:
                try:
                    json_match = re.search(r'\{[\s\S]*\}', response, re.DOTALL)
                    if json_match:
                        json_str = json_match.group(0)
                        parsed = json.loads(json_str)
                        parse_method = "regex"
                        logger.info("Successfully extracted JSON using regex")
                except Exception as e:
                    logger.debug(f"Regex extraction failed: {str(e)}")

            # If all strategies failed
            if parsed is None:
                logger.error(f"Failed to parse JSON response: All strategies failed")
                logger.error(f"Response length: {len(response)} chars")
                logger.error(f"Response preview (first 500 chars): {response[:500]}")
                logger.error(f"Response preview (last 500 chars): {response[-500:]}")
                # Save full response to temp file for debugging
                try:
                    import tempfile
                    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                        f.write(response)
                        logger.error(f"Full response saved to: {f.name}")
                except:
                    pass
                return None

            logger.info(f"JSON parsed successfully using method: {parse_method}")

            # Step 4: Clean up extra fields that shouldn't be there
            # (Haiku sometimes adds fields like "interpretation_continued")
            extra_fields = []
            expected_fields = {"summary", "key_findings", "interpretation", "recommendations", "visualization_suggestions"}
            for field in list(parsed.keys()):
                if field not in expected_fields:
                    extra_fields.append(field)

            if extra_fields:
                logger.warning(f"Removing unexpected fields from response: {extra_fields}")
                # Merge extra interpretation fields into main interpretation
                for field in extra_fields:
                    if 'interpretation' in field.lower() and isinstance(parsed[field], str):
                        if 'interpretation' in parsed:
                            parsed['interpretation'] += "\n\n" + parsed[field]
                        else:
                            parsed['interpretation'] = parsed[field]
                    # Remove the extra field
                    del parsed[field]

            # Step 5: Validate and normalize required fields
            required_fields = ["key_findings", "interpretation", "recommendations"]
            for field in required_fields:
                if field not in parsed:
                    logger.warning(f"Response missing '{field}' field, adding default")
                    if field == "key_findings" or field == "recommendations":
                        parsed[field] = []
                    else:
                        parsed[field] = ""

            # Ensure summary field exists
            if "summary" not in parsed:
                parsed["summary"] = "Analysis completed"

            # Ensure visualization_suggestions exists and is a list
            if "visualization_suggestions" not in parsed:
                parsed["visualization_suggestions"] = []
            elif not isinstance(parsed["visualization_suggestions"], list):
                parsed["visualization_suggestions"] = []

            # Clean up string fields (remove extra whitespace, normalize newlines)
            if isinstance(parsed.get("interpretation"), str):
                parsed["interpretation"] = parsed["interpretation"].strip()
            if isinstance(parsed.get("summary"), str):
                parsed["summary"] = parsed["summary"].strip()

            return parsed

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {str(e)}")
            logger.error(f"Error at line {e.lineno}, column {e.colno}: {e.msg}")
            logger.error(f"Raw response (first 1000 chars): {response[:1000]}")
            return None

        except Exception as e:
            logger.error(f"Error parsing response: {str(e)}", exc_info=True)
            logger.error(f"Response type: {type(response)}")
            logger.error(f"Response preview: {response[:500] if response else 'None'}")
            return None

    def generate_executive_summary(
        self,
        analysis_results: List[AnalysisResult]
    ) -> str:
        """
        Generate an executive summary from multiple analysis results.

        Args:
            analysis_results: List of analysis results to summarize

        Returns:
            Executive summary text
        """
        if not analysis_results:
            return "No analysis results to summarize."

        # Collect all findings and recommendations
        all_findings = []
        all_recommendations = []

        for result in analysis_results:
            if result.success and result.key_findings:
                all_findings.extend(result.key_findings)
            if result.success and result.recommendations:
                all_recommendations.extend(result.recommendations)

        # Build summary
        summary_parts = [
            "# Performance Analysis Executive Summary",
            "",
            f"Analyzed {len(analysis_results)} query result(s)",
            ""
        ]

        if all_findings:
            summary_parts.append("## Key Findings")
            for i, finding in enumerate(all_findings[:10], 1):  # Top 10
                summary_parts.append(f"{i}. {finding}")
            summary_parts.append("")

        if all_recommendations:
            summary_parts.append("## Top Recommendations")
            for i, rec in enumerate(all_recommendations[:10], 1):  # Top 10
                summary_parts.append(f"{i}. {rec}")

        return "\n".join(summary_parts)
