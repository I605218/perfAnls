"""
应用配置管理
"""
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    """应用配置"""

    # 应用配置
    app_name: str = "Process Engine Performance Analyzer"
    app_version: str = "0.1.0"
    app_port: int = 8000
    log_level: str = "INFO"

    # 数据库配置
    database_url: str = "postgresql://postgres:postgres@localhost:5432/process-engine"
    db_pool_min_size: int = 5
    db_pool_max_size: int = 10
    db_timeout: int = 30

    # AI 配置
    anthropic_api_key: str
    base_url: Optional[str] = None
    claude_model: str = "claude-haiku-4-5"
    claude_max_tokens: int = 4096
    claude_temperature: float = 1.0

    # 分析配置
    default_top_k: int = 10
    default_time_range_days: int = 7
    max_query_results: int = 1000

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()
