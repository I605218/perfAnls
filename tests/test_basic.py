"""
基础测试 - 验证核心功能
"""
import pytest
from datetime import datetime, timedelta


class TestConfiguration:
    """测试配置加载"""

    def test_import_config(self):
        """测试配置模块导入"""
        from app.config import get_settings

        settings = get_settings()
        assert settings.app_name == "Process Engine Performance Analyzer"
        assert settings.app_version == "0.1.0"
        assert settings.app_port == 8000


class TestModels:
    """测试数据模型"""

    def test_process_instance_model(self):
        """测试流程实例模型"""
        from app.models.process import ProcessInstance

        proc = ProcessInstance(
            id="test-001",
            proc_def_id="def-001",
            proc_def_name="Test Process",
            proc_def_key="testProc",
            start_time=datetime.now(),
            end_time=datetime.now() + timedelta(seconds=30),
            duration_seconds=30.0,
            status="COMPLETED"
        )

        assert proc.id == "test-001"
        assert proc.duration_seconds == 30.0

    def test_process_statistics_model(self):
        """测试流程统计模型"""
        from app.models.process import ProcessStatistics

        stats = ProcessStatistics(
            proc_def_key="testProc",
            proc_def_name="Test Process",
            version=1,
            execution_count=100,
            avg_duration_seconds=45.5,
            min_duration=10.0,
            max_duration=120.0
        )

        assert stats.execution_count == 100
        assert stats.avg_duration_seconds == 45.5


# 运行测试：
# pytest tests/test_basic.py -v
