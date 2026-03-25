"""
Integration tests for Text-to-SQL system.

This module tests the complete workflow from natural language to SQL execution and AI analysis.
Requires a running PostgreSQL database with test data.
"""

import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.services.text_to_sql_service import TextToSQLService
from app.services.dynamic_query_service import DynamicQueryService
from app.services.ai_analysis_service import AIAnalysisService
from app.config import get_settings


class TextToSQLIntegrationTest:
    """Integration test suite for Text-to-SQL system."""

    def __init__(self):
        """Initialize test suite with services."""
        self.settings = get_settings()

        # Initialize services
        self.text_to_sql = TextToSQLService(
            api_key=self.settings.anthropic_api_key,
            base_url=self.settings.base_url,
            schema_dir="schema",
            validate_sql=True
        )

        self.query_service = DynamicQueryService(
            database_url=self.settings.database_url,
            min_pool_size=2,
            max_pool_size=5,
            query_timeout=30.0,
            max_rows=1000
        )

        self.analysis_service = AIAnalysisService(
            api_key=self.settings.anthropic_api_key,
            base_url=self.settings.base_url
        )

        self.test_cases = self._define_test_cases()
        self.results = []

    def _define_test_cases(self) -> List[Dict[str, Any]]:
        """Define test cases covering different complexity levels."""
        return [
            # Category 1: Simple queries (单表、单条件)
            {
                "category": "简单查询",
                "query": "找出最近10个流程实例",
                "expected_tables": ["pe_ext_procinst"],
                "expected_complexity": "low"
            },
            {
                "category": "简单查询",
                "query": "Show me processes with status COMPLETED",
                "expected_tables": ["pe_ext_procinst"],
                "expected_complexity": "low"
            },
            {
                "category": "简单查询",
                "query": "统计一共有多少个流程实例",
                "expected_tables": ["pe_ext_procinst"],
                "expected_complexity": "low"
            },

            # Category 2: Medium complexity (多条件、聚合)
            {
                "category": "中等复杂度",
                "query": "找出执行时间超过100秒的已完成流程",
                "expected_tables": ["pe_ext_procinst"],
                "expected_complexity": "low"
            },
            {
                "category": "中等复杂度",
                "query": "按状态分组统计流程实例数量",
                "expected_tables": ["pe_ext_procinst"],
                "expected_complexity": "low"
            },
            {
                "category": "中等复杂度",
                "query": "Show me the top 5 slowest completed processes",
                "expected_tables": ["pe_ext_procinst"],
                "expected_complexity": "low"
            },
            {
                "category": "中等复杂度",
                "query": "统计每个流程定义的平均执行时间",
                "expected_tables": ["pe_ext_procinst"],
                "expected_complexity": "medium"
            },

            # Category 3: Complex queries (多表JOIN、子查询)
            {
                "category": "复杂查询",
                "query": "找出活动执行时间最长的流程实例，包括活动详情",
                "expected_tables": ["pe_ext_procinst", "pe_ext_actinst"],
                "expected_complexity": "medium"
            },
            {
                "category": "复杂查询",
                "query": "查找包含失败活动的流程实例",
                "expected_tables": ["pe_ext_procinst", "pe_ext_actinst"],
                "expected_complexity": "medium"
            },
            {
                "category": "复杂查询",
                "query": "Show me processes with their variable count",
                "expected_tables": ["pe_ext_procinst", "pe_ext_varinst"],
                "expected_complexity": "medium"
            },

            # Category 4: Edge cases (边界情况)
            {
                "category": "边界情况",
                "query": "找出状态为UNKNOWN的流程",  # Should return empty
                "expected_tables": ["pe_ext_procinst"],
                "expected_complexity": "low"
            },
            {
                "category": "边界情况",
                "query": "查询昨天的流程实例",
                "expected_tables": ["pe_ext_procinst"],
                "expected_complexity": "low"
            },
        ]

    async def setup(self):
        """Setup test environment."""
        print("🔧 Setting up test environment...")
        await self.query_service.initialize()

        # Check database connection
        result = await self.query_service.execute_query(
            "SELECT COUNT(*) as count FROM pe_ext_procinst"
        )
        if result.success:
            count = result.rows[0]['count'] if result.rows else 0
            print(f"✅ Database connected. Found {count} process instances.")
        else:
            print(f"❌ Database connection failed: {result.error_message}")
            raise Exception("Cannot connect to database")

    async def teardown(self):
        """Cleanup test environment."""
        print("\n🧹 Cleaning up...")
        await self.query_service.close()

    async def run_test_case(self, test_case: Dict[str, Any], index: int) -> Dict[str, Any]:
        """Run a single test case."""
        print(f"\n{'='*80}")
        print(f"Test Case #{index + 1}: {test_case['category']}")
        print(f"Query: {test_case['query']}")
        print(f"{'='*80}")

        result = {
            "index": index + 1,
            "category": test_case["category"],
            "query": test_case["query"],
            "stages": {}
        }

        try:
            # Stage 1: SQL Generation
            print("\n[Stage 1] Generating SQL...")
            sql_result = self.text_to_sql.generate_sql(
                user_query=test_case["query"]
            )

            result["stages"]["sql_generation"] = {
                "success": sql_result.success,
                "sql": sql_result.sql if sql_result.success else None,
                "explanation": sql_result.explanation,
                "error": sql_result.error_message
            }

            if not sql_result.success:
                print(f"❌ SQL generation failed: {sql_result.error_message}")
                return result

            print(f"✅ Generated SQL:\n{sql_result.sql}")
            print(f"📝 Explanation: {sql_result.explanation}")

            # Stage 2: SQL Validation
            print("\n[Stage 2] Validating SQL...")
            if sql_result.validation_result:
                result["stages"]["validation"] = {
                    "is_valid": sql_result.validation_result.is_valid,
                    "table_count": sql_result.validation_result.table_count,
                    "has_subquery": sql_result.validation_result.has_subquery,
                    "complexity": sql_result.validation_result.estimated_complexity,
                    "issues": [issue.to_dict() for issue in sql_result.validation_result.issues] if sql_result.validation_result.issues else []
                }

                if not sql_result.validation_result.is_valid:
                    print(f"❌ Validation failed: {len(sql_result.validation_result.issues)} issues")
                    for issue in sql_result.validation_result.issues:
                        print(f"   - {issue.severity}: {issue.message}")
                    return result

                print(f"✅ Validation passed")
                print(f"   Tables: {sql_result.validation_result.table_count}")
                print(f"   Complexity: {sql_result.validation_result.estimated_complexity}")

            # Stage 3: Query Execution
            print("\n[Stage 3] Executing query...")
            query_result = await self.query_service.execute_query(sql_result.sql)

            result["stages"]["execution"] = {
                "success": query_result.success,
                "row_count": query_result.row_count if query_result.success else None,
                "execution_time_ms": query_result.execution_time_ms if query_result.success else None,
                "error": query_result.error_message
            }

            if not query_result.success:
                print(f"❌ Query execution failed: {query_result.error_message}")
                return result

            print(f"✅ Query executed successfully")
            print(f"   Rows returned: {query_result.row_count}")
            print(f"   Execution time: {query_result.execution_time_ms:.2f}ms")

            # Show sample results
            if query_result.rows:
                print(f"\n📊 Sample results (first 3 rows):")
                for i, row in enumerate(query_result.rows[:3]):
                    print(f"   Row {i+1}: {row}")

            # Stage 4: AI Analysis
            print("\n[Stage 4] Analyzing results with AI...")
            analysis_result = self.analysis_service.analyze_query_results(
                user_query=test_case["query"],
                sql=sql_result.sql,
                results=query_result.rows or []
            )

            result["stages"]["analysis"] = {
                "success": analysis_result.success,
                "summary": analysis_result.summary if analysis_result.success else None,
                "key_findings_count": len(analysis_result.key_findings) if analysis_result.success else 0,
                "recommendations_count": len(analysis_result.recommendations) if analysis_result.success else 0,
                "error": analysis_result.error_message
            }

            if not analysis_result.success:
                print(f"⚠️  AI analysis failed: {analysis_result.error_message}")
            else:
                print(f"✅ AI analysis completed")
                print(f"\n💡 Summary: {analysis_result.summary}")
                if analysis_result.key_findings:
                    print(f"\n🔍 Key Findings ({len(analysis_result.key_findings)}):")
                    for finding in analysis_result.key_findings[:3]:
                        print(f"   - {finding}")
                if analysis_result.recommendations:
                    print(f"\n💡 Recommendations ({len(analysis_result.recommendations)}):")
                    for rec in analysis_result.recommendations[:3]:
                        print(f"   - {rec}")

            result["overall_success"] = True
            print(f"\n✅ Test case #{index + 1} PASSED")

        except Exception as e:
            result["overall_success"] = False
            result["error"] = str(e)
            print(f"\n❌ Test case #{index + 1} FAILED: {str(e)}")

        return result

    async def run_all_tests(self):
        """Run all test cases."""
        print("\n" + "="*80)
        print("🚀 Starting Text-to-SQL Integration Tests")
        print("="*80)

        await self.setup()

        passed = 0
        failed = 0

        for i, test_case in enumerate(self.test_cases):
            result = await self.run_test_case(test_case, i)
            self.results.append(result)

            if result.get("overall_success", False):
                passed += 1
            else:
                failed += 1

        await self.teardown()

        # Print summary
        self._print_summary(passed, failed)

    def _print_summary(self, passed: int, failed: int):
        """Print test summary."""
        print("\n" + "="*80)
        print("📊 TEST SUMMARY")
        print("="*80)

        total = passed + failed
        pass_rate = (passed / total * 100) if total > 0 else 0

        print(f"\nTotal Tests: {total}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"📈 Pass Rate: {pass_rate:.1f}%")

        # Group results by category
        print("\n📋 Results by Category:")
        categories = {}
        for result in self.results:
            cat = result["category"]
            if cat not in categories:
                categories[cat] = {"passed": 0, "failed": 0}
            if result.get("overall_success", False):
                categories[cat]["passed"] += 1
            else:
                categories[cat]["failed"] += 1

        for cat, stats in categories.items():
            total_cat = stats["passed"] + stats["failed"]
            print(f"\n  {cat}:")
            print(f"    ✅ {stats['passed']}/{total_cat} passed")
            if stats["failed"] > 0:
                print(f"    ❌ {stats['failed']}/{total_cat} failed")

        # Show failed tests
        if failed > 0:
            print("\n❌ Failed Tests:")
            for result in self.results:
                if not result.get("overall_success", False):
                    print(f"\n  Test #{result['index']}: {result['query']}")
                    print(f"  Category: {result['category']}")
                    if "error" in result:
                        print(f"  Error: {result['error']}")
                    else:
                        # Show which stage failed
                        for stage, stage_result in result["stages"].items():
                            if not stage_result.get("success", True):
                                print(f"  Failed at stage: {stage}")
                                if "error" in stage_result:
                                    print(f"  Error: {stage_result['error']}")

        print("\n" + "="*80)


async def main():
    """Main entry point."""
    test_suite = TextToSQLIntegrationTest()
    await test_suite.run_all_tests()


if __name__ == "__main__":
    # Run the integration tests
    asyncio.run(main())
