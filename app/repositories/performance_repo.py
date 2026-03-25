"""
性能数据查询仓库
"""
from typing import List
from datetime import datetime
import asyncpg
from app.models.process import ProcessInstance, ProcessStatistics, ActivityStatistics


class PerformanceRepository:
    """性能数据仓库 - 封装所有性能相关的 SQL 查询"""

    async def get_top_slowest_processes(
        self,
        conn: asyncpg.Connection,
        k: int = 10,
        start_time: datetime = None,
        end_time: datetime = None
    ) -> List[ProcessInstance]:
        """
        获取 Top K 最慢的流程实例

        Args:
            conn: 数据库连接
            k: 返回前 K 个结果
            start_time: 开始时间（包含）
            end_time: 结束时间（包含）

        Returns:
            流程实例列表，按执行时长降序排列
        """

        query = """
        SELECT
            e.id,
            e.proc_def_id,
            d.name_ as proc_def_name,
            d.key_ as proc_def_key,
            e.proc_inst_name,
            e.start_time,
            e.end_time,
            EXTRACT(EPOCH FROM (e.end_time - e.start_time)) as duration_seconds,
            e.status,
            e.sub_status,
            e.error_message,
            e.tenant_id
        FROM pe_ext_procinst e
        LEFT JOIN act_re_procdef d ON e.proc_def_id = d.id_
        WHERE e.end_time IS NOT NULL
          AND e.start_time >= $1
          AND e.end_time <= $2
        ORDER BY duration_seconds DESC
        LIMIT $3
        """

        rows = await conn.fetch(query, start_time, end_time, k)
        return [ProcessInstance(**dict(row)) for row in rows]

    async def get_most_frequent_processes(
        self,
        conn: asyncpg.Connection,
        start_time: datetime,
        end_time: datetime,
        limit: int = 10
    ) -> List[ProcessStatistics]:
        """
        获取运行次数最多的流程定义

        Args:
            conn: 数据库连接
            start_time: 开始时间
            end_time: 结束时间
            limit: 返回结果数量限制

        Returns:
            流程统计列表，按执行次数降序排列
        """

        query = """
        SELECT
            d.key_ as proc_def_key,
            d.name_ as proc_def_name,
            d.version_,
            COUNT(*) as execution_count,
            COALESCE(
                ROUND(AVG(EXTRACT(EPOCH FROM (e.end_time - e.start_time)))::numeric, 2),
                0
            ) as avg_duration_seconds,
            COALESCE(
                ROUND(MIN(EXTRACT(EPOCH FROM (e.end_time - e.start_time)))::numeric, 2),
                0
            ) as min_duration,
            COALESCE(
                ROUND(MAX(EXTRACT(EPOCH FROM (e.end_time - e.start_time)))::numeric, 2),
                0
            ) as max_duration
        FROM pe_ext_procinst e
        JOIN act_re_procdef d ON e.proc_def_id = d.id_
        WHERE e.start_time >= $1
          AND e.start_time <= $2
        GROUP BY d.key_, d.name_, d.version_
        ORDER BY execution_count DESC
        LIMIT $3
        """

        rows = await conn.fetch(query, start_time, end_time, limit)
        return [ProcessStatistics(**dict(row)) for row in rows]

    async def get_activity_statistics_by_process(
        self,
        conn: asyncpg.Connection,
        proc_inst_id: str
    ) -> List[ActivityStatistics]:
        """
        获取指定流程实例的活动级别统计

        Args:
            conn: 数据库连接
            proc_inst_id: 流程实例ID

        Returns:
            活动统计列表，按平均执行时长降序排列
        """

        query = """
        SELECT
            a.act_id,
            a.act_name,
            a.act_type,
            COUNT(*) as execution_count,
            ROUND(AVG(EXTRACT(EPOCH FROM (a.end_time - a.start_time)))::numeric, 2)
                as avg_duration,
            ROUND(MAX(EXTRACT(EPOCH FROM (a.end_time - a.start_time)))::numeric, 2)
                as max_duration,
            ROUND(MIN(EXTRACT(EPOCH FROM (a.end_time - a.start_time)))::numeric, 2)
                as min_duration
        FROM pe_ext_actinst a
        WHERE a.proc_inst_id = $1
          AND a.end_time IS NOT NULL
        GROUP BY a.act_id, a.act_name, a.act_type
        ORDER BY avg_duration DESC
        """

        rows = await conn.fetch(query, proc_inst_id)
        return [ActivityStatistics(**dict(row)) for row in rows]

    async def get_process_count(
        self,
        conn: asyncpg.Connection,
        start_time: datetime = None,
        end_time: datetime = None
    ) -> int:
        """
        获取流程实例总数

        Args:
            conn: 数据库连接
            start_time: 开始时间（可选）
            end_time: 结束时间（可选）

        Returns:
            流程实例数量
        """

        if start_time and end_time:
            query = """
            SELECT COUNT(*)
            FROM pe_ext_procinst
            WHERE start_time >= $1 AND start_time <= $2
            """
            count = await conn.fetchval(query, start_time, end_time)
        else:
            query = "SELECT COUNT(*) FROM pe_ext_procinst"
            count = await conn.fetchval(query)

        return count

    async def get_table_info(self, conn: asyncpg.Connection) -> dict:
        """
        获取数据库表信息（用于健康检查）

        Returns:
            包含表数量和核心表存在性的字典
        """

        # 查询表总数
        total_tables = await conn.fetchval(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public'"
        )

        # 检查核心表
        core_tables = ['pe_ext_procinst', 'pe_ext_actinst', 'pe_ext_varinst', 'act_re_procdef']
        existing_tables = []

        for table in core_tables:
            exists = await conn.fetchval(
                "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public' AND table_name=$1",
                table
            )
            if exists:
                existing_tables.append(table)

        return {
            "total_tables": total_tables,
            "core_tables": existing_tables,
            "all_core_tables_exist": len(existing_tables) == len(core_tables)
        }
