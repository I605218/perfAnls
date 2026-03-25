"""
API 响应模型
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional


class AIInsights(BaseModel):
    """AI 分析结果"""
    analysis: str = Field(description="AI 生成的分析报告（Markdown 格式）")
    model: str = Field(description="使用的 AI 模型")
    usage: Dict[str, int] = Field(description="Token 使用情况")
    timestamp: Optional[str] = Field(None, description="分析时间戳")
    error: Optional[str] = Field(None, description="错误信息（如果有）")


class QueryParams(BaseModel):
    """查询参数"""
    k: Optional[int] = Field(None, description="Top K 参数")
    start_time: Optional[str] = Field(None, description="开始时间（ISO 8601格式）")
    end_time: Optional[str] = Field(None, description="结束时间（ISO 8601格式）")
    limit: Optional[int] = Field(None, description="结果数量限制")


class ProcessDataSection(BaseModel):
    """流程数据部分"""
    total_count: int = Field(description="流程实例总数")
    processes: List[Dict[str, Any]] = Field(description="流程实例详细数据")


class StatisticsDataSection(BaseModel):
    """统计数据部分"""
    total_definitions: int = Field(description="流程定义总数")
    statistics: List[Dict[str, Any]] = Field(description="统计数据详细信息")


class SlowProcessAnalysisResponse(BaseModel):
    """Top K 最慢流程分析响应"""
    query_params: QueryParams = Field(description="查询参数")
    data: ProcessDataSection = Field(description="查询结果数据")
    ai_insights: AIInsights = Field(description="AI 分析结果")

    class Config:
        json_schema_extra = {
            "example": {
                "query_params": {
                    "k": 10,
                    "start_time": "2026-03-16T00:00:00",
                    "end_time": "2026-03-23T23:59:59"
                },
                "data": {
                    "total_count": 10,
                    "processes": [
                        {
                            "id": "proc-001",
                            "proc_def_name": "Order Processing",
                            "duration_seconds": 320.5,
                            "status": "COMPLETED"
                        }
                    ]
                },
                "ai_insights": {
                    "analysis": "## 性能瓶颈识别\n...",
                    "model": "claude-sonnet-4-6",
                    "usage": {"input_tokens": 1500, "output_tokens": 2000}
                }
            }
        }


class FrequencyAnalysisResponse(BaseModel):
    """最频繁运行流程分析响应"""
    query_params: QueryParams = Field(description="查询参数")
    data: StatisticsDataSection = Field(description="统计数据")
    ai_insights: AIInsights = Field(description="AI 分析结果")

    class Config:
        json_schema_extra = {
            "example": {
                "query_params": {
                    "start_time": "2026-03-16T00:00:00",
                    "end_time": "2026-03-23T23:59:59",
                    "limit": 10
                },
                "data": {
                    "total_definitions": 10,
                    "statistics": [
                        {
                            "proc_def_key": "orderProcess",
                            "proc_def_name": "Order Processing",
                            "version": 3,
                            "execution_count": 1523,
                            "avg_duration_seconds": 45.3
                        }
                    ]
                },
                "ai_insights": {
                    "analysis": "## 执行模式分析\n...",
                    "model": "claude-sonnet-4-6",
                    "usage": {"input_tokens": 1200, "output_tokens": 1800}
                }
            }
        }


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str = Field(description="服务状态")
    service: str = Field(description="服务名称")
    timestamp: str = Field(description="时间戳")
    database: Optional[Dict[str, Any]] = Field(None, description="数据库信息")


class ErrorResponse(BaseModel):
    """错误响应"""
    error: str = Field(description="错误类型")
    message: str = Field(description="错误消息")
    detail: Optional[str] = Field(None, description="详细信息")
    timestamp: str = Field(description="时间戳")
