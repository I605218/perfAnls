"""
性能分析 API 路由
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from datetime import datetime, timedelta
from typing import Optional
import asyncpg

from app.services.analysis_service import AnalysisService
from app.repositories.database import get_db_connection
from app.api.models.responses import (
    SlowProcessAnalysisResponse,
    FrequencyAnalysisResponse,
    HealthResponse,
    ErrorResponse
)
from app.config import get_settings

router = APIRouter(prefix="/analysis", tags=["Performance Analysis"])
analysis_service = AnalysisService()
settings = get_settings()


@router.get(
    "/top-slowest",
    response_model=SlowProcessAnalysisResponse,
    summary="Top K 最慢流程分析",
    description="""
    查询执行时间最长的流程实例，并使用 AI 分析性能瓶颈。

    **功能特性：**
    - 查询指定时间范围内执行时间最长的流程实例
    - 使用 Claude AI 深度分析性能问题
    - 识别瓶颈、异常模式和优化建议

    **默认行为：**
    - 如果不指定时间范围，默认查询最近 7 天
    - 返回查询结果和 AI 生成的分析报告
    """,
    responses={
        200: {"description": "成功返回分析结果"},
        400: {"model": ErrorResponse, "description": "参数错误"},
        500: {"model": ErrorResponse, "description": "服务器错误"}
    }
)
async def analyze_top_slowest(
    k: int = Query(
        default=10,
        ge=1,
        le=100,
        description="返回前 K 个最慢的流程实例"
    ),
    start_time: Optional[datetime] = Query(
        default=None,
        description="开始时间（ISO 8601 格式，例如：2026-03-16T00:00:00）"
    ),
    end_time: Optional[datetime] = Query(
        default=None,
        description="结束时间（ISO 8601 格式，例如：2026-03-23T23:59:59）"
    ),
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    """
    Top K 最慢流程分析

    返回执行时间最长的 K 个流程实例，并提供 AI 分析报告。
    """

    try:
        # 设置默认时间范围：最近7天
        if not end_time:
            end_time = datetime.now()
        if not start_time:
            start_time = end_time - timedelta(days=settings.default_time_range_days)

        # 执行分析
        result = await analysis_service.analyze_top_slowest(
            conn, k, start_time, end_time
        )

        return result

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"分析失败: {str(e)}"
        )


@router.get(
    "/most-frequent",
    response_model=FrequencyAnalysisResponse,
    summary="最频繁运行流程分析",
    description="""
    统计指定时间范围内运行次数最多的流程定义，并使用 AI 分析执行模式。

    **功能特性：**
    - 按流程定义 Key 分组统计执行次数
    - 计算平均/最小/最大执行时间
    - AI 分析执行频率模式和资源利用情况
    - 提供优化优先级建议

    **默认行为：**
    - 如果不指定时间范围，默认查询最近 7 天
    """,
    responses={
        200: {"description": "成功返回分析结果"},
        400: {"model": ErrorResponse, "description": "参数错误"},
        500: {"model": ErrorResponse, "description": "服务器错误"}
    }
)
async def analyze_most_frequent(
    start_time: Optional[datetime] = Query(
        default=None,
        description="开始时间（ISO 8601 格式）"
    ),
    end_time: Optional[datetime] = Query(
        default=None,
        description="结束时间（ISO 8601 格式）"
    ),
    limit: int = Query(
        default=10,
        ge=1,
        le=50,
        description="返回前 N 个流程定义"
    ),
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    """
    最频繁运行流程分析

    统计并分析执行次数最多的流程定义。
    """

    try:
        # 设置默认时间范围：最近7天
        if not end_time:
            end_time = datetime.now()
        if not start_time:
            start_time = end_time - timedelta(days=settings.default_time_range_days)

        # 执行分析
        result = await analysis_service.analyze_frequency(
            conn, start_time, end_time, limit
        )

        return result

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"分析失败: {str(e)}"
        )


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="健康检查",
    description="检查服务和数据库连接状态"
)
async def health_check(
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    """
    健康检查接口

    返回服务运行状态和数据库连接信息。
    """

    try:
        # 获取数据库健康信息
        db_health = await analysis_service.get_database_health(conn)

        return {
            "status": "healthy",
            "service": settings.app_name,
            "timestamp": datetime.now().isoformat(),
            "database": db_health
        }

    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"健康检查失败: {str(e)}"
        )


@router.get(
    "/stats/summary",
    summary="数据库统计摘要",
    description="快速查看数据库中的流程数据统计"
)
async def get_statistics_summary(
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    """
    数据库统计摘要

    返回流程实例总数、流程定义数量等基础统计信息。
    """

    try:
        # 流程实例总数
        total_instances = await conn.fetchval(
            "SELECT COUNT(*) FROM pe_ext_procinst"
        )

        # 已完成的流程实例
        completed_instances = await conn.fetchval(
            "SELECT COUNT(*) FROM pe_ext_procinst WHERE end_time IS NOT NULL"
        )

        # 流程定义数量
        process_definitions = await conn.fetchval(
            "SELECT COUNT(*) FROM act_re_procdef"
        )

        # 部署数量
        deployments = await conn.fetchval(
            "SELECT COUNT(*) FROM act_re_deployment"
        )

        # 最近一次流程实例时间
        latest_instance = await conn.fetchval(
            "SELECT MAX(start_time) FROM pe_ext_procinst"
        )

        return {
            "summary": {
                "total_process_instances": total_instances,
                "completed_instances": completed_instances,
                "running_instances": total_instances - completed_instances,
                "process_definitions": process_definitions,
                "deployments": deployments,
                "latest_instance_time": latest_instance.isoformat() if latest_instance else None
            },
            "data_availability": {
                "has_data": total_instances > 0,
                "has_completed_data": completed_instances > 0,
                "message": "数据充足，可以进行分析" if completed_instances > 0 else "数据库为空或没有已完成的流程实例"
            },
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"查询统计信息失败: {str(e)}"
        )
