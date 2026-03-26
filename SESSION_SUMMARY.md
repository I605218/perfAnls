# Session Summary - 2026-03-26

**Date**: 2026-03-26
**Session Focus**: 语义层(Semantic Layer) + CTE模板集成 & 性能诊断功能探讨
**Status**: 语义层集成完成 ✅ | 性能诊断功能放弃 ⚠️

---

## 📋 本次会话完成的工作

### 1. ✅ 完成语义层（Semantic Layer）+ CTE模板的集成

#### 背景与动机
- **优化目标**: 提升复杂查询的生成质量和稳定性
- **方案选择**: 采用方案C - 预定义语义层 + CTE模板（单次SQL生成）
- **核心思路**: 在schema文件中定义可复用的指标和CTE模板，让Claude参考这些预定义结构生成更稳定的SQL

#### 完成的Schema文件更新

所有6个schema文件都已添加完整的`semantic_metrics`和`cte_templates`：

##### 1. **pe_ext_procinst.json** ✅
**Base Metrics（基础指标）**:
- `duration_seconds`: 流程执行时长（秒）
- `process_key`: 流程定义key（去除版本号）
- `is_completed`: 是否成功完成
- `is_failed`: 是否失败
- `is_timeout`: 是否超时

**Aggregate Metrics（聚合指标）**:
- `avg_duration`: 平均执行时长
- `p95_duration`: P95执行时长
- `success_rate`: 成功率（%）
- `failure_rate`: 失败率（%）
- `timeout_rate`: 超时率（%）

**CTE Templates（CTE模板）**:
- `time_series_analysis`: 时间序列分析（按小时/天聚合）
- `period_comparison`: 周期对比（本周 vs 上周）

---

##### 2. **pe_ext_actinst.json** ✅
**Base Metrics**:
- `duration_seconds`: 活动执行时长
- `is_user_task`: 是否为用户任务
- `is_service_task`: 是否为服务任务
- `is_failed`: 是否失败
- `is_bottleneck`: 是否为瓶颈（时长>阈值）

**Aggregate Metrics**:
- `avg_duration`: 平均执行时长
- `max_duration`: 最大执行时长
- `p95_duration`: P95执行时长
- `failure_rate`: 失败率

**CTE Templates**:
- `bottleneck_detection`: 瓶颈检测（识别慢活动）
- `activity_performance_by_process`: 按流程分析活动性能
- `user_task_waiting_time`: 用户任务等待时间分析

---

##### 3. **pe_ext_varinst.json** ✅
**Base Metrics**:
- `value_size_bytes`: 变量值大小（字节）
- `is_large_variable`: 是否为大字段变量（>1000字节或使用外部存储）
- `is_external_storage`: 是否使用外部存储（ACT_GE_BYTEARRAY）
- `is_process_level`: 是否为流程级变量
- `is_activity_level`: 是否为活动级变量
- `update_count`: 变量是否被更新过
- `is_serializable_type`: 是否为高开销序列化类型（json/serializable/bytes）

**Aggregate Metrics**:
- `avg_variable_size`: 平均变量大小
- `max_variable_size`: 最大变量大小
- `large_variable_count`: 大字段变量数量
- `external_storage_count`: 外部存储变量数量
- `avg_variables_per_process`: 每个流程的平均变量数量
- `update_frequency`: 变量更新频率（%）

**CTE Templates**:
- `large_variable_impact`: 分析大字段变量对流程性能的影响
- `variable_type_serialization_cost`: 按变量类型评估序列化性能开销
- `variable_density_by_process`: 统计每个流程的变量密度
- `frequent_update_analysis`: 识别频繁更新的变量及其对性能的影响
- `input_output_comparison`: 对比流程的输入和输出变量，识别数据膨胀问题

---

##### 4-6. **act_ru_job.json, act_ge_bytearray.json, act_ru_deadletter_job.json** ✅
这三个表的schema在之前会话中已经完成了完整的语义层定义。

---

#### Prompt Builder更新

**文件**: `app/prompts/text_to_sql_prompt.py`

**修改内容**: 在`_build_schema_section()`方法中添加了两个新部分：

```python
# 1. Semantic Metrics部分
if schema.get('semantic_metrics'):
    schema_parts.append(f"\n### **Semantic Metrics for {schema['table_name']}**")

    # 展示Base Metrics（基础指标）
    if schema['semantic_metrics'].get('base_metrics'):
        for metric_name, metric_def in schema['semantic_metrics']['base_metrics'].items():
            # 显示：指标名、公式、描述、使用场景

    # 展示Aggregate Metrics（聚合指标）
    if schema['semantic_metrics'].get('aggregate_metrics'):
        for metric_name, metric_def in schema['semantic_metrics']['aggregate_metrics'].items():
            # 显示：指标名、公式、描述、使用场景

# 2. CTE Templates部分
if schema.get('cte_templates'):
    schema_parts.append(f"\n### **CTE Templates for {schema['table_name']}**")

    for template_name, template_def in schema['cte_templates'].items():
        # 显示：模板名、描述、用途、CTE结构SQL、完整示例查询
```

**效果**:
- Claude在生成SQL时可以直接参考这些预定义的指标公式和CTE模板
- 确保生成的SQL更稳定、更符合最佳实践
- 提升复杂查询的生成质量（如周期对比、瓶颈检测、变量影响分析）

---

### 2. ⚠️ 性能诊断服务的讨论（未完成/放弃）

#### 问题识别
**当前问题**: AI分析是通用的，缺乏针对性能分析领域的深度知识

**期望增强**:
- 异常检测（异常值、趋势突变）
- 根因分析（为什么慢？）
- 对比基线（与历史数据对比）
- 预测趋势（未来是否会恶化）
- 专家级优化建议

#### 方案设计

**方案A（推荐）**: 独立的诊断服务
```
用户查询
  → SQL生成
  → SQL执行
  → Stage 4: AI通用分析
  → Stage 5: 性能诊断服务（专家级）
  → 返回结果
```

**方案B**: 融入prompt
- 在prompt中注入性能专家知识
- 但无法做复杂计算和历史对比

#### 实现尝试

创建了`app/services/performance_diagnostics_service.py`，包含：

1. **PerformanceBaseline类**: 性能基准值定义
   ```python
   process_avg_duration_threshold: float = 60.0  # 秒
   process_p95_duration_threshold: float = 120.0  # 秒
   process_failure_rate_threshold: float = 5.0  # 百分比
   variable_count_per_process_threshold: int = 50
   large_variable_size_threshold: int = 1000  # 字节
   # ...更多基准值
   ```

2. **diagnose()方法**: 深度性能诊断
   - 整体健康评估（健康/轻微问题/需要关注/严重问题）
   - 性能异常检测（对比基准值）
   - 根因分析（技术原因+业务原因）
   - 趋势预测（性能是否在恶化）
   - 优化建议（按优先级排序，包含预期收益和实施难度）

3. **免责声明**:
   > ⚠️ 本诊断结果由AI生成，仅供参考。实际性能问题需结合具体业务场景和系统环境，由专业工程师判断。

#### 放弃原因 ⚠️

**用户反馈**:
> "我感觉performance_diagnostics_service.py中的定义需要仔细考量的，我感觉你在这个文件里面给出的代码都是臆想出来的，你没有真正实际流程的经验，所以我放弃这次修改。"

**根本问题**:
- 性能基准值（如"60秒"、"50个变量"）都是基于理论假设，缺乏实际依据
- 没有真实的流程引擎运维经验，无法准确设定合理阈值
- 不同业务场景的性能标准差异很大，不能一概而论
- 需要基于真实生产数据和领域专家经验来定义基准

**重要教训**:
> 性能诊断需要领域专家知识和实际数据支撑，不能凭空臆想。AI助手可以帮助实现技术架构，但业务规则和性能基准必须由有实际经验的人来定义。

---

## 📊 当前系统架构总结

### 完整的查询流程（5个阶段）

```
用户输入自然语言查询
    ↓
Stage 1: Text-to-SQL（SQL生成）
    ├─ schema_selector.py 识别相关表
    ├─ 加载对应schema（包含semantic_metrics和cte_templates）
    └─ 调用Claude API生成SQL
    ↓
Stage 2: SQL Validation（安全验证）
    ├─ 检查SQL类型（只允许SELECT）
    ├─ 检查表白名单
    └─ 检查危险函数
    ↓
Stage 3: Query Execution（执行SQL）
    ├─ asyncpg连接池执行
    ├─ 超时保护（默认30秒）
    ├─ PostgreSQL 9.6语法自动修复
    └─ 结果格式化
    ↓
Stage 4: AI Analysis（通用分析）
    ├─ 分析查询结果
    ├─ 提供业务洞察
    ├─ 给出优化建议
    └─ 可视化建议
    ↓
返回结果给用户
```

### 核心优化成果

#### ✅ 优化1: 按需加载Schema（已完成）
- **文件**: `app/prompts/schema_selector.py`
- **效果**: 根据用户查询智能加载相关表，节省50-83%上下文
- **机制**: 关键词映射 + 自动关联表加载

#### ✅ 优化2: 语义层 + CTE模板（本次完成）
- **效果**: 提供可复用的指标定义和CTE模板，提升复杂查询生成质量
- **关键**: 所有6个schema文件都包含完整的semantic_metrics和cte_templates
- **价值**:
  - Claude可以直接引用预定义的指标公式（如`avg_duration`, `success_rate`）
  - Claude可以参考CTE模板生成复杂分析查询（如周期对比、瓶颈检测）
  - 确保生成的SQL遵循最佳实践和一致的命名规范

---

## 🗂️ 技术栈与关键文件

### 技术栈
- **AI**: Claude Sonnet 4.6 (anthropic--claude-4.5-sonnet)
- **Database**: PostgreSQL 9.6
- **Framework**: FastAPI + asyncpg
- **Language**: Python 3.10+

### Schema文件（6个，全部已完成语义层）
- `schema/pe_ext_procinst.json` - 流程实例 ✅
- `schema/pe_ext_actinst.json` - 活动实例 ✅
- `schema/pe_ext_varinst.json` - 变量实例 ✅
- `schema/act_ru_job.json` - 异步任务队列 ✅
- `schema/act_ge_bytearray.json` - 二进制数据存储 ✅
- `schema/act_ru_deadletter_job.json` - 死信队列 ✅

### Prompt系统
- `app/prompts/text_to_sql_prompt.py` - SQL生成提示词构建器（✅ 已更新：包含semantic_metrics和cte_templates）
- `app/prompts/schema_selector.py` - 智能schema选择器

### 服务层
- `app/services/text_to_sql_service.py` - Text-to-SQL服务
- `app/services/dynamic_query_service.py` - SQL执行服务（包含PostgreSQL 9.6语法自动修复）
- `app/services/ai_analysis_service.py` - AI分析服务
- `app/services/performance_diagnostics_service.py` - ⚠️ 已创建但未启用（基准值需重新设计）

### API层
- `app/api/v1/endpoints/dynamic_analysis.py` - 动态查询API端点

### 安全层
- `app/security/sql_validator.py` - SQL安全验证器

---

## 📝 待办事项

### Task #4: 创建API使用示例文档 [pending]
- 创建实际的API调用示例
- 包含curl命令、Python代码示例
- 展示不同场景的查询示例

### Task #6: 实现语义层 + CTE 模板优化 [completed] ✅
- ✅ 所有schema文件添加semantic_metrics
- ✅ 所有schema文件添加cte_templates
- ✅ Prompt Builder集成语义层展示

### 性能诊断功能（需重新设计）⚠️
**问题**: 当前的性能基准值是臆想的，不符合实际

**建议方案**:
1. **数据驱动的基准值**:
   - 收集实际生产数据，统计真实的性能指标分布
   - 计算P50/P75/P90/P95/P99分位数
   - 识别正常范围和异常阈值

2. **领域专家验证**:
   - 与有实际流程引擎运维经验的专家确认合理的性能阈值
   - 不同业务场景可能需要不同的基准值

3. **可配置的基准系统**:
   - 将基准值设计为可配置（不同业务场景可能不同）
   - 支持按流程定义、按租户、按时间段自定义基准

4. **渐进式实现**:
   - 阶段1: 先实现简单的异常检测（基于统计学方法）
   - 阶段2: 添加历史对比功能
   - 阶段3: 引入性能基准和诊断建议

**是否需要性能诊断**:
- 考虑是否真的需要自动化诊断，或者只保留通用的AI分析
- 自动化诊断可能给出误导性建议，不如让用户基于数据自行判断

---

## 💡 重要经验教训

### 1. Schema即知识库
把业务知识、SQL最佳实践、常见查询模式都编入schema，比在prompt中反复强调更有效。Claude会更自然地参考schema中的示例和指导。

### 2. 语义层的价值
预定义可复用的指标和CTE模板，能显著提升复杂查询的生成质量和一致性：
- **一致性**: 所有查询使用相同的指标计算方式
- **可维护性**: 修改指标定义只需更新schema，不需要修改prompt
- **可扩展性**: 新增指标和模板不影响现有功能

### 3. 性能基准需实证 ⚠️
**不能凭空臆想性能阈值，必须基于实际数据和领域专家经验。**

这是本次会话最重要的教训：
- AI助手可以帮助实现技术架构和编写代码
- 但业务规则、性能基准、诊断逻辑必须由有实际经验的人来定义
- 没有真实数据支撑的"专家系统"可能比没有还糟糕（误导用户）

### 4. 渐进式优化策略
先完成核心功能，再逐步添加高级特性：
- ✅ Phase 1: Text-to-SQL基础功能
- ✅ Phase 2: Schema优化（按需加载）
- ✅ Phase 3: 语义层集成
- ⏳ Phase 4: 性能诊断（需重新评估是否必要）

---

## 🎯 下一步建议

### 短期（立即可做）
1. **测试语义层效果**:
   - 用复杂查询测试semantic_metrics和cte_templates
   - 验证Claude是否能正确引用预定义指标
   - 评估CTE模板对查询质量的提升

2. **收集用户反馈**:
   - 哪些CTE模板最有用？
   - 哪些指标定义需要调整？
   - 是否需要添加新的指标或模板？

3. **完成文档**:
   - Task #4: 创建API使用示例文档
   - 补充语义层使用指南
   - 更新README和用户手册

### 中期（需要数据支撑）
1. **数据收集**:
   - 统计真实生产环境的性能指标分布
   - 识别常见的性能问题模式
   - 与业务专家访谈，了解实际痛点

2. **评估性能诊断需求**:
   - 用户真正需要什么样的诊断功能？
   - 是自动化诊断，还是更强大的数据展示？
   - 能否通过改进通用AI分析达到目标？

3. **如果确实需要诊断功能**:
   - 基于真实数据定义性能基准
   - 设计可配置的基准系统
   - 实现简单的异常检测（统计学方法）

### 长期（增强功能）
1. 支持历史数据对比（当前 vs 上周/上月）
2. 异常检测算法（基于统计学或机器学习）
3. 性能趋势预测（时间序列分析）
4. 自动化性能报告生成（定期扫描）

---

## 🔄 系统状态

### 已完成 ✅
- Text-to-SQL核心功能完整
- SQL安全验证完善
- 按需Schema加载优化完成
- **语义层 + CTE模板集成完成** ✨ 本次重点
- PostgreSQL 9.6语法自动修复

### 待完善 ⏳
- API文档和示例补充
- 语义层效果验证和优化
- 性能诊断功能评估和重新设计

### 已放弃 ⚠️
- 基于臆想基准值的性能诊断服务
  - 原因：缺乏实际数据和领域经验支撑
  - 教训：不能凭空设计业务规则

---

## 📂 Git状态

当前分支: main
工作区状态: 干净（无待提交文件）

**注意**:
- `app/services/performance_diagnostics_service.py` 文件已创建但未提交
- `app/api/v1/endpoints/dynamic_analysis.py` 修改了但被linter恢复（未集成诊断服务）
- **建议**: 删除`performance_diagnostics_service.py`，或者保留但标注为"未启用/待重新设计"

---

## 📞 会话总结

### 本次会话的核心成果
✅ **语义层(Semantic Layer) + CTE模板完整集成**

这是一个重要的里程碑，为复杂查询生成提供了强大的支持：
- 6个schema文件全部包含完整的semantic_metrics和cte_templates
- Prompt Builder成功集成语义层展示
- 为Claude提供了可复用的指标定义和查询模板

### 本次会话的重要教训
⚠️ **AI助手的局限性**

尽管AI可以帮助编写技术实现，但**领域知识和业务规则必须由人类专家提供**：
- 性能基准值不能臆想，必须基于实际数据
- 诊断逻辑需要实际运维经验支撑
- 业务规则的准确性直接影响系统价值

### 下一步最重要的工作
1. **测试语义层效果**（立即）
2. **完成API文档**（短期）
3. **评估性能诊断需求**（中期，需要实际数据支撑）

---

**文档生成时间**: 2026-03-26
**文档版本**: 2.0
**本次会话重点**: 语义层集成 ✅ | 性能诊断探讨 ⚠️
**系统状态**: Phase 3完成，等待效果验证和用户反馈
