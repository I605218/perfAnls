"""
流程相关的数据模型
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class ProcessInstance(BaseModel):
    """流程实例模型"""
    id: str = Field(description="流程实例ID")
    proc_def_id: str = Field(description="流程定义ID")
    proc_def_name: Optional[str] = Field(None, description="流程定义名称")
    proc_def_key: Optional[str] = Field(None, description="流程定义Key")
    proc_inst_name: Optional[str] = Field(None, description="流程实例名称")
    start_time: datetime = Field(description="开始时间")
    end_time: Optional[datetime] = Field(None, description="结束时间")
    duration_seconds: Optional[float] = Field(None, description="执行时长(秒)")
    status: Optional[str] = Field(None, description="流程状态")
    sub_status: Optional[str] = Field(None, description="子状态")
    error_message: Optional[str] = Field(None, description="错误信息")
    tenant_id: Optional[str] = Field(None, description="租户ID")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "proc-inst-001",
                "proc_def_id": "proc-def-001",
                "proc_def_name": "Order Processing",
                "proc_def_key": "orderProcess",
                "start_time": "2026-03-23T10:00:00",
                "end_time": "2026-03-23T10:05:30",
                "duration_seconds": 330.0,
                "status": "COMPLETED"
            }
        }


class ProcessStatistics(BaseModel):
    """流程统计信息"""
    proc_def_key: str = Field(description="流程定义Key")
    proc_def_name: str = Field(description="流程定义名称")
    version: int = Field(description="流程版本号")
    execution_count: int = Field(description="执行次数")
    avg_duration_seconds: float = Field(description="平均执行时长(秒)")
    min_duration: float = Field(description="最小执行时长(秒)")
    max_duration: float = Field(description="最大执行时长(秒)")

    class Config:
        json_schema_extra = {
            "example": {
                "proc_def_key": "orderProcess",
                "proc_def_name": "Order Processing",
                "version": 3,
                "execution_count": 1523,
                "avg_duration_seconds": 45.3,
                "min_duration": 12.5,
                "max_duration": 320.8
            }
        }


class ActivityInstance(BaseModel):
    """活动实例模型"""
    act_id: str = Field(description="活动ID")
    act_name: str = Field(description="活动名称")
    act_type: str = Field(description="活动类型")
    proc_inst_id: str = Field(description="流程实例ID")
    start_time: datetime = Field(description="开始时间")
    end_time: Optional[datetime] = Field(None, description="结束时间")
    duration_seconds: Optional[float] = Field(None, description="执行时长(秒)")


class ActivityStatistics(BaseModel):
    """活动统计信息"""
    act_id: str = Field(description="活动ID")
    act_name: str = Field(description="活动名称")
    act_type: str = Field(description="活动类型")
    execution_count: int = Field(description="执行次数")
    avg_duration: float = Field(description="平均执行时长(秒)")
    max_duration: float = Field(description="最大执行时长(秒)")
    min_duration: float = Field(description="最小执行时长(秒)")
