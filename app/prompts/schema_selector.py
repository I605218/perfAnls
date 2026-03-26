"""
Schema table keywords mapping configuration.

Maps natural language keywords to database tables for intelligent schema loading.
"""
from typing import Dict, List, Set

# 表关键词映射：每张表对应的中英文关键词
TABLE_KEYWORDS: Dict[str, List[str]] = {
    "pe_ext_procinst": [
        # 中文关键词
        "流程实例", "流程", "执行时长", "执行时间", "流程定义", "流程状态",
        "已完成", "失败", "运行中", "完成率", "成功率", "失败率",
        "流程性能", "流程执行", "流程分析", "流程统计",
        "parent", "子流程", "父流程", "根流程",

        # 英文关键词
        "process", "instance", "execution", "duration", "completed", "failed",
        "running", "status", "performance", "definition", "proc_def",
        "start_time", "end_time", "trigger"
    ],

    "pe_ext_actinst": [
        # 中文关键词
        "活动实例", "活动", "任务", "节点", "环节", "步骤",
        "用户任务", "服务任务", "活动类型", "活动性能", "瓶颈",
        "等待时间", "活动耗时", "活动分析",

        # 英文关键词
        "activity", "task", "node", "step", "user task", "service task",
        "bottleneck", "activity type", "waiting time", "act_inst"
    ],

    "pe_ext_varinst": [
        # 中文关键词
        "变量", "参数", "输入", "输出", "变量值", "变量类型",
        "变量大小", "变量影响", "数据", "字段",

        # 英文关键词
        "variable", "var", "parameter", "input", "output", "value",
        "data", "field", "varinst"
    ],

    "act_ru_job": [
        # 中文关键词（避免通用词"任务"，使用更specific的词）
        "任务队列", "异步任务", "job队列", "排队", "积压",
        "等待执行", "执行中", "锁定", "任务调度", "调度器",
        "定时器任务", "timer", "重试次数", "任务等待",

        # 英文关键词
        "job queue", "async task", "job", "queue", "pending", "locked", "waiting",
        "scheduler", "timer job", "retry", "backlog"
    ],

    "act_ge_bytearray": [
        # 中文关键词
        "二进制", "字节", "大字段", "大变量", "附件", "文件",
        "存储", "容量", "大小", "异常堆栈", "堆栈",
        "json", "xml", "pdf",

        # 英文关键词
        "binary", "byte", "bytearray", "large", "file", "attachment",
        "storage", "size", "capacity", "exception stack", "stack trace"
    ],

    "act_ru_deadletter_job": [
        # 中文关键词
        "死信", "死信队列", "失败任务", "彻底失败", "无法恢复",
        "重试失败", "僵尸", "故障", "错误",

        # 英文关键词
        "deadletter", "dead letter", "failed", "failure", "error",
        "zombie", "unrecoverable", "retry exhausted"
    ]
}

# 表之间的关联关系：当选择某张表时，可能需要自动加载的关联表
# 注意：只添加高频使用的关联表，避免过度加载
TABLE_RELATIONSHIPS: Dict[str, List[str]] = {
    "pe_ext_procinst": [],  # 基础表，不需要自动关联

    "pe_ext_actinst": [
        "pe_ext_procinst"  # 活动实例通常需要关联流程实例
    ],

    "pe_ext_varinst": [
        "pe_ext_procinst"  # 变量通常需要关联流程实例
    ],

    "act_ru_job": [
        "pe_ext_procinst"  # 任务通常需要关联流程实例
    ],

    "act_ge_bytearray": [],  # 按需加载，不自动关联

    "act_ru_deadletter_job": [
        "pe_ext_procinst",      # 死信任务需要关联流程实例
        "act_ge_bytearray"      # 通常需要查看异常堆栈
    ]
}

# 查询类型关键词：用于识别查询意图
QUERY_TYPE_KEYWORDS: Dict[str, List[str]] = {
    "statistics": [
        "统计", "总数", "数量", "count", "多少", "有几个",
        "汇总", "合计", "sum"
    ],

    "aggregation": [
        "平均", "最大", "最小", "总和", "中位数", "分位数",
        "average", "avg", "max", "min", "sum", "median", "percentile",
        "p95", "p99"
    ],

    "performance": [
        "性能", "耗时", "时长", "速度", "快慢", "瓶颈",
        "performance", "duration", "time", "slow", "fast", "bottleneck",
        "优化", "optimize"
    ],

    "failure": [
        "失败", "错误", "异常", "故障", "问题",
        "failed", "failure", "error", "exception", "issue", "problem"
    ],

    "trend": [
        "趋势", "变化", "对比", "增长", "下降",
        "trend", "change", "compare", "growth", "decline",
        "本周", "上周", "昨天", "今天"
    ]
}


def identify_relevant_tables(user_query: str) -> Set[str]:
    """
    根据用户查询识别相关的表。

    Args:
        user_query: 用户的自然语言查询

    Returns:
        相关表名的集合
    """
    query_lower = user_query.lower()
    relevant_tables = set()

    # 1. 基于关键词匹配
    for table_name, keywords in TABLE_KEYWORDS.items():
        for keyword in keywords:
            if keyword.lower() in query_lower:
                relevant_tables.add(table_name)
                break

    # 2. 如果没有匹配到任何表，使用默认表
    if not relevant_tables:
        # 默认使用流程实例表（最基础的表）
        relevant_tables.add("pe_ext_procinst")

    # 3. 自动添加关联表
    tables_with_relationships = set(relevant_tables)
    for table in relevant_tables:
        if table in TABLE_RELATIONSHIPS:
            for related_table in TABLE_RELATIONSHIPS[table]:
                tables_with_relationships.add(related_table)

    return tables_with_relationships


def get_query_type(user_query: str) -> List[str]:
    """
    识别查询类型（用于未来扩展）。

    Args:
        user_query: 用户的自然语言查询

    Returns:
        查询类型列表
    """
    query_lower = user_query.lower()
    query_types = []

    for query_type, keywords in QUERY_TYPE_KEYWORDS.items():
        for keyword in keywords:
            if keyword.lower() in query_lower:
                query_types.append(query_type)
                break

    return query_types or ["general"]


# 示例用法
if __name__ == "__main__":
    test_queries = [
        "统计流程实例总数",
        "查询死信任务",
        "分析大变量对性能的影响",
        "查询最近7天的任务积压情况",
        "对比本周和上周的流程性能"
    ]

    for query in test_queries:
        tables = identify_relevant_tables(query)
        query_types = get_query_type(query)
        print(f"\n查询: {query}")
        print(f"相关表: {tables}")
        print(f"查询类型: {query_types}")
