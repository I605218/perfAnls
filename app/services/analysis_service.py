"""
分析服务 - 协调查询和 AI 分析
"""
from typing import Dict, Any
from datetime import datetime
import asyncpg

from app.repositories.performance_repo import PerformanceRepository
from app.services.ai_service import AIAnalysisService


class AnalysisService:
    """分析服务 - 业务逻辑层"""

    def __init__(self):
        self.perf_repo = PerformanceRepository()
        self.ai_service = AIAnalysisService()

    async def analyze_top_slowest(
        self,
        conn: asyncpg.Connection,
        k: int = 10,
        start_time: datetime = None,
        end_time: datetime = None
    ) -> Dict[str, Any]:
        """
        分析执行时间最长的流程

        Args:
            conn: 数据库连接
            k: 返回前 K 个最慢的流程
            start_time: 开始时间
            end_time: 结束时间

        Returns:
            包含查询结果和 AI 分析的字典
        """

        # 1. 查询数据
        processes = await self.perf_repo.get_top_slowest_processes(
            conn, k, start_time, end_time
        )

        # 2. 转换为字典格式
        process_dicts = [p.model_dump(mode='json') for p in processes]

        # 3. AI 分析
        ai_insights = await self.ai_service.analyze_slow_processes(process_dicts)

        # 4. 组装返回结果
        return {
            "query_params": {
                "k": k,
                "start_time": start_time.isoformat() if start_time else None,
                "end_time": end_time.isoformat() if end_time else None
            },
            "data": {
                "total_count": len(processes),
                "processes": process_dicts
            },
            "ai_insights": ai_insights
        }

    async def analyze_frequency(
        self,
        conn: asyncpg.Connection,
        start_time: datetime,
        end_time: datetime,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        分析流程执行频率

        Args:
            conn: 数据库连接
            start_time: 开始时间
            end_time: 结束时间
            limit: 返回结果数量限制

        Returns:
            包含统计数据和 AI 分析的字典
        """

        # 1. 查询统计数据
        stats = await self.perf_repo.get_most_frequent_processes(
            conn, start_time, end_time, limit
        )

        # 2. 转换为字典格式
        stats_dicts = [s.model_dump(mode='json') for s in stats]

        # 3. AI 分析
        ai_insights = await self.ai_service.analyze_process_frequency(stats_dicts)

        # 4. 组装返回结果
        return {
            "query_params": {
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "limit": limit
            },
            "data": {
                "total_definitions": len(stats),
                "statistics": stats_dicts
            },
            "ai_insights": ai_insights
        }

    async def get_database_health(
        self,
        conn: asyncpg.Connection
    ) -> Dict[str, Any]:
        """
        获取数据库健康状态

        Returns:
            数据库健康信息
        """

        # 获取表信息
        table_info = await self.perf_repo.get_table_info(conn)

        # 获取流程实例总数
        total_processes = await self.perf_repo.get_process_count(conn)

        return {
            "database": {
                "total_tables": table_info["total_tables"],
                "core_tables": table_info["core_tables"],
                "all_core_tables_exist": table_info["all_core_tables_exist"]
            },
            "data": {
                "total_process_instances": total_processes
            },
            "status": "healthy" if table_info["all_core_tables_exist"] else "degraded"
        }
