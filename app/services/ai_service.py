"""
AI 分析服务 - 使用 Claude API 进行性能分析
"""
from anthropic import AsyncAnthropic
from typing import List, Dict, Any
from app.config import get_settings
from datetime import datetime


class AIAnalysisService:
    """AI 分析服务"""

    def __init__(self):
        self.settings = get_settings()
        self.client = AsyncAnthropic(
            api_key=self.settings.anthropic_api_key,
            base_url=self.settings.base_url
        )

    async def analyze_slow_processes(
        self,
        processes: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        分析执行缓慢的流程实例

        Args:
            processes: 流程实例数据列表

        Returns:
            包含 AI 分析结果的字典
        """

        if not processes:
            return {
                "analysis": "没有数据可供分析",
                "model": self.settings.claude_model,
                "usage": {"input_tokens": 0, "output_tokens": 0}
            }

        # 格式化数据为表格
        data_summary = self._format_process_data(processes)

        prompt = f"""你是一个 BPMN 流程引擎性能分析专家。请分析以下执行时间最长的流程实例数据：

{data_summary}

数据说明：
- 这些是按执行时长排序的 Top K 慢流程
- duration_seconds: 流程从开始到结束的总时长
- status: 流程执行状态
- error_message: 如果有错误，会显示错误信息

请提供详细的分析报告，包括：

## 1. 性能瓶颈识别
- 哪些流程执行时间异常长？
- 是否有明显的性能问题模式？
- 正常流程和慢流程的时长差异分析

## 2. 异常模式检测
- 是否存在失败、超时或错误的流程？
- 错误流程与执行时长的关系
- 是否有特定的流程定义版本存在问题？

## 3. 对比分析
- 不同流程定义之间的性能差异
- 同一流程定义不同实例的执行时长波动
- 是否有流程版本性能退化的迹象？

## 4. 优化建议
请提供具体的、可操作的优化建议，分为：
- **代码级别**：流程定义优化、活动配置优化
- **配置级别**：引擎参数调优、资源配置
- **架构级别**：流程拆分、异步处理等架构优化

## 5. 根本原因分析
基于数据推测可能导致性能问题的深层原因：
- 业务逻辑复杂度
- 外部服务依赖
- 数据库查询性能
- 并发处理能力

请以清晰的 Markdown 格式输出分析结果。"""

        try:
            response = await self.client.messages.create(
                model=self.settings.claude_model,
                max_tokens=self.settings.claude_max_tokens,
                temperature=self.settings.claude_temperature,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            return {
                "analysis": response.content[0].text,
                "model": self.settings.claude_model,
                "usage": {
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens
                },
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            return {
                "analysis": f"AI 分析失败: {str(e)}",
                "model": self.settings.claude_model,
                "usage": {"input_tokens": 0, "output_tokens": 0},
                "error": str(e)
            }

    async def analyze_process_frequency(
        self,
        statistics: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        分析流程执行频率统计

        Args:
            statistics: 流程统计数据列表

        Returns:
            包含 AI 分析结果的字典
        """

        if not statistics:
            return {
                "analysis": "没有数据可供分析",
                "model": self.settings.claude_model,
                "usage": {"input_tokens": 0, "output_tokens": 0}
            }

        data_summary = self._format_statistics_data(statistics)

        prompt = f"""你是一个 BPMN 流程引擎性能分析专家。请分析以下流程执行频率统计数据：

{data_summary}

数据说明：
- execution_count: 在指定时间范围内的执行次数
- avg_duration_seconds: 平均执行时长
- min/max_duration: 最小/最大执行时长

请提供详细的分析报告，包括：

## 1. 执行模式分析
- 高频流程和低频流程的特征
- 执行频率分布是否合理？
- 是否存在异常的高频或低频流程？

## 2. 性能与频率的关系
- 高频流程的性能表现如何？
- 执行频率与平均耗时的相关性
- 是否有高频且高耗时的流程（优化优先级高）？

## 3. 资源利用分析
- 哪些流程消耗最多的系统资源？（频率 × 平均时长）
- 资源利用是否均衡？
- 是否存在资源浪费或瓶颈？

## 4. 优化优先级建议
基于执行频率和性能数据，提供优化优先级排序：
- 高优先级：高频 + 高耗时
- 中优先级：高频但低耗时，或低频但极高耗时
- 低优先级：低频且低耗时

## 5. 容量规划建议
- 基于当前执行频率的容量评估
- 预估峰值负载场景
- 扩展性建议

## 6. 版本对比分析
- 同一流程的不同版本性能差异
- 是否有版本升级导致的性能退化？
- 版本策略建议

请以清晰的 Markdown 格式输出分析结果。"""

        try:
            response = await self.client.messages.create(
                model=self.settings.claude_model,
                max_tokens=self.settings.claude_max_tokens,
                temperature=self.settings.claude_temperature,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            return {
                "analysis": response.content[0].text,
                "model": self.settings.claude_model,
                "usage": {
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens
                },
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            return {
                "analysis": f"AI 分析失败: {str(e)}",
                "model": self.settings.claude_model,
                "usage": {"input_tokens": 0, "output_tokens": 0},
                "error": str(e)
            }

    def _format_process_data(self, processes: List[Dict]) -> str:
        """
        格式化流程数据为 Markdown 表格

        Args:
            processes: 流程实例字典列表

        Returns:
            Markdown 格式的表格字符串
        """
        if not processes:
            return "无数据"

        lines = ["| 序号 | 流程名称 | 流程Key | 版本 | 执行时长(秒) | 状态 | 开始时间 | 错误信息 |"]
        lines.append("|-----|---------|---------|-----|------------|------|---------|---------|")

        for idx, p in enumerate(processes[:50], 1):  # 限制前50条
            # 处理可能的 None 值
            proc_name = p.get('proc_def_name') or p.get('proc_inst_name') or 'N/A'
            proc_key = p.get('proc_def_key', 'N/A')
            duration = p.get('duration_seconds', 0)
            status = p.get('status', 'N/A')
            start_time = p.get('start_time')
            error_msg = p.get('error_message', '') or '-'

            # 格式化时间
            if isinstance(start_time, datetime):
                start_time_str = start_time.strftime('%Y-%m-%d %H:%M:%S')
            else:
                start_time_str = str(start_time) if start_time else 'N/A'

            # 截断错误信息
            if len(error_msg) > 50:
                error_msg = error_msg[:47] + '...'

            lines.append(
                f"| {idx} | "
                f"{proc_name[:30]} | "
                f"{proc_key[:20]} | "
                f"- | "
                f"{duration:.2f} | "
                f"{status} | "
                f"{start_time_str} | "
                f"{error_msg} |"
            )

        lines.append(f"\n总计: {len(processes)} 个流程实例")

        return "\n".join(lines)

    def _format_statistics_data(self, stats: List[Dict]) -> str:
        """
        格式化统计数据为 Markdown 表格

        Args:
            stats: 统计数据字典列表

        Returns:
            Markdown 格式的表格字符串
        """
        if not stats:
            return "无数据"

        lines = ["| 序号 | 流程Key | 流程名称 | 版本 | 执行次数 | 平均时长(秒) | 最小时长(秒) | 最大时长(秒) | 资源消耗指数 |"]
        lines.append("|-----|---------|---------|------|---------|------------|------------|------------|------------|")

        for idx, s in enumerate(stats, 1):
            proc_key = s.get('proc_def_key', 'N/A')
            proc_name = s.get('proc_def_name', 'N/A')
            version = s.get('version', 0)
            count = s.get('execution_count', 0)
            avg_dur = s.get('avg_duration_seconds', 0)
            min_dur = s.get('min_duration', 0)
            max_dur = s.get('max_duration', 0)

            # 计算资源消耗指数（执行次数 × 平均时长）
            resource_index = count * avg_dur

            lines.append(
                f"| {idx} | "
                f"{proc_key[:25]} | "
                f"{proc_name[:25]} | "
                f"v{version} | "
                f"{count:,} | "
                f"{avg_dur:.2f} | "
                f"{min_dur:.2f} | "
                f"{max_dur:.2f} | "
                f"{resource_index:.2f} |"
            )

        lines.append(f"\n总计: {len(stats)} 个流程定义")

        return "\n".join(lines)
