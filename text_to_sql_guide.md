# Text-to-SQL 用户指南

## 目录
- [简介](#简介)
- [快速开始](#快速开始)
- [支持的查询类型](#支持的查询类型)
- [查询技巧与最佳实践](#查询技巧与最佳实践)
- [常见问题 FAQ](#常见问题-faq)
- [查询示例库](#查询示例库)
- [API 参考](#api-参考)

---

## 简介

Process Engine Performance Analyzer 的 Text-to-SQL 功能允许您使用**自然语言**（中文或英文）直接查询流程引擎的性能数据，无需编写 SQL 语句。

### 核心优势

- **零 SQL 门槛**：使用日常语言描述您想要的数据
- **智能分析**：AI 自动分析查询结果并提供业务洞察
- **安全可靠**：自动验证 SQL 安全性，只读查询，超时保护
- **双语支持**：支持中文和英文查询
- **可视化建议**：自动推荐最适合的图表类型

### 数据源

系统查询三张核心表：

| 表名 | 说明 | 主要用途 |
|------|------|---------|
| `pe_ext_procinst` | 流程实例表 | 流程级别性能分析（整体执行时长、状态、触发方式） |
| `pe_ext_actinst` | 活动实例表 | 活动级别性能分析（具体环节耗时、瓶颈定位） |
| `pe_ext_varinst` | 变量实例表 | 变量影响分析（大字段、序列化开销） |

---

## 快速开始

### 1. 启动服务

```bash
./start.sh
```

确保看到以下启动日志：
```
✅ 动态查询服务初始化成功
🤖 AI 模型: claude-sonnet-4-6
🌐 服务端口: 8000
📖 API 文档: http://localhost:8000/docs
```

### 2. 访问 API 文档

在浏览器中打开：http://localhost:8000/docs

### 3. 执行第一个查询

#### 使用 Swagger UI

1. 找到 `POST /api/v1/analysis/query` 端点
2. 点击 "Try it out"
3. 输入请求体：
```json
{
  "query": "统计流程实例总数"
}
```
4. 点击 "Execute"

#### 使用 curl

```bash
curl -X POST "http://localhost:8000/api/v1/analysis/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "统计流程实例总数"
  }'
```

### 4. 理解响应

响应包含四个关键部分：

```json
{
  "success": true,
  "sql": "生成的 SQL 查询",           // 1. SQL 生成
  "explanation": "SQL 解释",
  "validation": {                     // 2. 安全验证
    "is_valid": true,
    "security_level": "SAFE"
  },
  "results": [...],                   // 3. 查询结果
  "row_count": 10,
  "execution_time_ms": 45.2,
  "analysis": {                       // 4. AI 分析
    "summary": "执行摘要",
    "key_findings": ["发现1", "发现2"],
    "recommendations": ["建议1", "建议2"],
    "visualization_suggestions": [...]
  }
}
```

---

## 支持的查询类型

### 1. 统计聚合查询

用于获取总数、平均值、最大/最小值等统计指标。

**适用场景：**
- 统计流程实例总数
- 计算平均执行时长
- 查找最慢/最快的流程

**查询示例：**
```
"统计流程实例总数"
"计算已完成流程的平均执行时长"
"找出执行时间最长的10个流程"
"What is the total number of failed processes?"
```

---

### 2. 时间范围查询

用于分析特定时间段内的数据。

**适用场景：**
- 查询最近 N 天的数据
- 对比不同时间段的性能
- 分析趋势变化

**查询示例：**
```
"查询过去7天内完成的流程数量"
"Show me failed processes in the last 30 days"
"对比本周和上周的流程性能"
"统计最近24小时每小时的流程执行量"
```

**提示：** 可以使用 context 参数指定时间范围：
```json
{
  "query": "统计完成的流程数量",
  "context": {
    "time_range": "last 7 days"
  }
}
```

---

### 3. 分组统计查询

用于按某个维度分组统计。

**适用场景：**
- 按流程定义分组统计
- 按状态分组统计
- 按活动类型分组统计

**查询示例：**
```
"统计每个流程定义的执行次数"
"按状态分组统计流程实例数量"
"计算各流程定义的平均执行时长"
"Group processes by trigger mode and count"
```

---

### 4. 排序和 Top K 查询

用于找出最值或排名。

**适用场景：**
- 找出最慢/最快的流程
- 查找失败率最高的流程
- 识别性能瓶颈活动

**查询示例：**
```
"找出最慢的10个流程实例"
"查询失败率最高的5个流程定义"
"Which 20 activities take the longest time?"
"显示执行次数最多的流程定义"
```

---

### 5. 过滤条件查询

用于按特定条件筛选数据。

**适用场景：**
- 查询特定状态的流程
- 筛选特定流程定义
- 过滤异常数据

**查询示例：**
```
"查询状态为 COMPLETED 的流程实例"
"Show me all failed processes with error messages"
"查找执行时长超过300秒的流程"
"查询流程定义为 OrderProcess 的所有实例"
```

---

### 6. JOIN 关联查询

用于关联多张表进行复杂分析。

**适用场景：**
- 分析流程与活动的关系
- 关联变量与流程性能
- 父子流程分析

**查询示例：**
```
"查询流程实例及其包含的所有活动"
"分析变量大小对流程性能的影响"
"查找包含子流程的流程实例及其性能"
"Show me processes with their failed activities"
```

---

### 7. 高级分析查询

用于复杂的性能分析和诊断。

**适用场景：**
- 性能瓶颈分析
- 失败原因分析
- 性能趋势分析
- 异常检测

**查询示例：**
```
"分析最近7天各流程定义的失败率和性能"
"找出导致流程变慢的活动"
"对比同步和异步触发模式的性能差异"
"分析哪些变量导致流程性能下降"
```

---

## 查询技巧与最佳实践

### 1. 如何写出好的查询

#### ✅ 推荐做法

**明确查询目标：**
```
✅ "查询过去30天内状态为COMPLETED的流程实例，按执行时长降序排列，取前10条"
❌ "看看流程"
```

**使用具体的时间范围：**
```
✅ "查询最近7天内完成的流程数量"
❌ "查询最近的流程"
```

**指定返回的字段：**
```
✅ "查询流程实例的ID、流程定义、状态和执行时长"
❌ "查询流程信息"
```

**使用业务术语：**
```
✅ "统计用户任务的平均等待时间"
✅ "分析服务任务的执行性能"
```

#### ❌ 避免的做法

**避免过于模糊：**
```
❌ "看看数据"
❌ "查询一些流程"
```

**避免包含非 SELECT 操作：**
```
❌ "删除失败的流程"
❌ "更新流程状态"
❌ "修改变量值"
```

**避免请求系统表：**
```
❌ "查询所有数据库表"
❌ "显示数据库配置"
```

---

### 2. 性能优化建议

#### 总是指定时间范围

```
✅ "查询最近30天内完成的流程"
❌ "查询所有完成的流程"  # 可能扫描全表
```

**原因：** `start_time` 和 `end_time` 字段有索引，限制时间范围可以显著提升查询速度。

#### 使用索引字段过滤

有索引的字段：
- `pe_ext_procinst`: `id`, `start_time`, `end_time`, `parent_inst_id`, `root_inst_id`
- `pe_ext_actinst`: `id`, `proc_inst_id`, `start_time`, `end_time`, `call_proc_inst_id`
- `pe_ext_varinst`: `id`, `proc_inst_id`, `name`, `create_time`

```
✅ "查询 proc_inst_id = 'xxx' 的活动实例"
✅ "按 name 分组统计变量"
```

#### 限制结果集大小

```
✅ "查询最慢的10个流程"
✅ "显示前20条失败的流程"
❌ "显示所有流程"  # 可能返回数十万条记录
```

**系统限制：** 最多返回 1000 行结果

#### 过滤低频数据

```
✅ "统计执行次数大于10的流程定义的平均时长"
❌ "统计所有流程定义的平均时长"  # 包含只执行1-2次的流程，统计意义有限
```

---

### 3. 使用 Context 参数

`context` 参数可以提供额外的查询上下文：

#### 指定租户（多租户环境）

```json
{
  "query": "统计流程实例数量",
  "context": {
    "tenant_id": "tenant_123"
  }
}
```

#### 指定时间范围

```json
{
  "query": "查询完成的流程",
  "context": {
    "time_range": "last 7 days"
  }
}
```

#### 添加额外过滤条件

```json
{
  "query": "统计流程数量",
  "context": {
    "additional_filters": "proc_def_id LIKE 'Order%'"
  }
}
```

---

### 4. 理解 AI 生成的 SQL

系统会返回生成的 SQL 及其解释，您可以：

1. **查看 `sql` 字段**：了解实际执行的查询
2. **阅读 `explanation` 字段**：理解查询逻辑
3. **检查 `reasoning` 字段**：了解为什么这样设计
4. **注意 `caveats` 字段**：了解查询的限制和假设

示例：
```json
{
  "sql": "SELECT COUNT(*) as total FROM pe_ext_procinst WHERE status = 'COMPLETED'",
  "explanation": "This query counts completed process instances",
  "reasoning": "Filtered by COMPLETED status to exclude running or failed processes",
  "caveats": ["Does not include processes that ended with errors"]
}
```

---

### 5. 利用 AI 分析结果

查询结果会自动进行 AI 分析，包括：

#### Summary（执行摘要）
快速了解查询结果的整体情况

#### Key Findings（关键发现）
数据中的重要发现和异常点

#### Interpretation（数据解读）
从业务角度解释数据含义

#### Recommendations（优化建议）
可操作的性能优化建议

#### Visualization Suggestions（可视化建议）
推荐的图表类型和展示方式

**示例：**
```json
{
  "analysis": {
    "summary": "查询返回10个最慢的流程，平均执行时长为320秒",
    "key_findings": [
      "OrderProcess 流程占据了最慢流程的60%",
      "失败流程的平均时长是成功流程的2.5倍"
    ],
    "recommendations": [
      "优化 OrderProcess 的审批环节，减少人工等待时间",
      "检查数据库索引是否正确使用",
      "考虑将耗时的服务调用改为异步执行"
    ],
    "visualization_suggestions": [
      {
        "chart_type": "bar chart",
        "title": "Top 10 最慢流程",
        "x_axis": "流程实例ID",
        "y_axis": "执行时长（秒）"
      }
    ]
  }
}
```

---

## 常见问题 FAQ

### Q1: 支持哪些语言的查询？

**A:** 支持中文和英文查询，系统会自动识别语言并生成对应的 SQL。

**示例：**
```
中文: "查询最近7天内失败的流程"
English: "Show me failed processes in the last 7 days"
```

---

### Q2: 可以修改或删除数据吗？

**A:** **不可以**。系统只允许 SELECT 查询，不支持 INSERT、UPDATE、DELETE、DROP 等操作。这是出于数据安全考虑。

**错误示例：**
```
❌ "删除失败的流程"
❌ "更新流程状态为COMPLETED"
```

---

### Q3: 查询超时时间是多少？

**A:** 默认超时时间为 **30 秒**。如果查询执行超过30秒，系统会自动终止查询并返回超时错误。

**建议：** 添加时间范围过滤和 LIMIT 子句来避免超时。

---

### Q4: 最多可以返回多少行数据？

**A:** 系统限制最多返回 **1000 行**数据。如果查询结果超过1000行，只返回前1000行。

**建议：** 使用聚合查询或添加 TOP K 限制。

---

### Q5: 为什么生成的 SQL 与我预期的不同？

**A:** AI 会根据以下因素生成 SQL：
- 数据库 schema 和索引信息
- 性能优化最佳实践
- 安全性考虑

如果生成的 SQL 不符合预期，可以：
1. 更详细地描述查询需求
2. 在查询中明确指定字段名或条件
3. 使用 context 参数提供额外信息

---

### Q6: 查询失败了怎么办？

**A:** 响应中的 `error_stage` 字段会告诉您失败发生在哪个阶段：

| error_stage | 说明 | 解决方法 |
|------------|------|---------|
| `sql_generation` | SQL 生成失败 | 检查查询是否清晰明确 |
| `validation` | SQL 验证失败 | 查询可能包含不安全的操作 |
| `execution` | SQL 执行失败 | 可能是语法错误或数据库问题 |
| `analysis` | AI 分析失败 | 不影响查询结果，可以忽略 |

**常见错误：**
```json
{
  "success": false,
  "error": "Query timeout after 30 seconds",
  "error_stage": "execution"
}
```

**解决方法：** 添加时间范围过滤，减少查询数据量。

---

### Q7: 数据库是空的，查询会返回什么？

**A:** 如果查询的表是空的，系统会：
1. 返回空结果集 `results: []`
2. AI 分析会提示数据为空
3. 给出如何填充测试数据的建议

---

### Q8: 可以查询实时数据吗？

**A:** 可以。系统直接查询数据库，不使用缓存，所以查询结果是实时的。

---

### Q9: 支持复杂的 SQL 吗（子查询、CTE、窗口函数）？

**A:** 支持！AI 会根据查询复杂度自动生成：
- 子查询（Subquery）
- CTE（Common Table Expression，WITH 子句）
- 窗口函数（Window Functions）
- JOIN（LEFT JOIN, INNER JOIN）

**示例：**
```
"对比本周和上周的流程性能"
→ 生成包含两个 CTE 的复杂查询
```

---

### Q10: 如何提高查询准确性？

**A:** 遵循以下建议：

1. **使用业务术语**：使用表结构中定义的字段名
2. **明确时间范围**：指定具体的时间段
3. **提供足够上下文**：描述清楚想要什么数据
4. **检查生成的 SQL**：查看 `explanation` 字段确认理解正确

---

## 查询示例库

### 基础查询

#### 1. 统计总数
```json
{
  "query": "统计流程实例总数"
}
```

#### 2. 按状态统计
```json
{
  "query": "按状态分组统计流程实例数量"
}
```

#### 3. 查询特定状态
```json
{
  "query": "查询状态为 COMPLETED 的流程实例数量"
}
```

---

### 性能分析

#### 4. 最慢流程 Top 10
```json
{
  "query": "找出最慢的10个流程实例，显示流程定义和执行时长"
}
```

#### 5. 平均执行时长
```json
{
  "query": "计算已完成流程的平均执行时长（秒），保留2位小数"
}
```

#### 6. 流程定义性能对比
```json
{
  "query": "统计每个流程定义的执行次数和平均执行时长，按执行次数降序排列"
}
```

#### 7. P95 执行时长
```json
{
  "query": "计算已完成流程的P95执行时长（95%分位数）"
}
```

---

### 时间范围分析

#### 8. 最近7天的流程统计
```json
{
  "query": "查询最近7天内完成的流程实例数量"
}
```

#### 9. 每小时执行趋势
```json
{
  "query": "统计最近24小时每小时的流程执行量和成功率"
}
```

#### 10. 周对周性能对比
```json
{
  "query": "对比本周和上周的流程平均执行时长"
}
```

---

### 失败分析

#### 11. 失败流程查询
```json
{
  "query": "查询最近7天内失败的流程，显示错误消息"
}
```

#### 12. 失败率统计
```json
{
  "query": "统计每个流程定义的失败率，按失败率降序排列"
}
```

#### 13. 失败原因分析
```json
{
  "query": "按错误消息分组统计失败流程数量"
}
```

---

### 活动分析

#### 14. 最慢活动 Top 20
```json
{
  "query": "查询平均执行时间最长的20个活动类型"
}
```

#### 15. 用户任务等待时间
```json
{
  "query": "统计用户任务的平均等待时间"
}
```

#### 16. 服务任务性能分析
```json
{
  "query": "分析服务任务的执行性能，包括平均时长和最大时长"
}
```

---

### 变量分析

#### 17. 大字段变量查询
```json
{
  "query": "查询使用外部存储的变量统计，按流程平均时长排序"
}
```

#### 18. 变量对性能的影响
```json
{
  "query": "分析变量大小与流程执行时长的关系"
}
```

#### 19. 频繁更新的变量
```json
{
  "query": "查询被频繁更新的变量及其更新间隔"
}
```

---

### 子流程分析

#### 20. 子流程性能影响
```json
{
  "query": "分析包含子流程的流程实例，统计子流程耗时占比"
}
```

#### 21. 父子流程关联查询
```json
{
  "query": "查询父流程及其所有子流程的执行情况"
}
```

---

### 高级分析

#### 22. 性能瓶颈识别
```json
{
  "query": "找出导致流程变慢的TOP 5活动"
}
```

#### 23. 同步vs异步性能对比
```json
{
  "query": "对比同步触发和异步触发的流程性能差异"
}
```

#### 24. 异常检测
```json
{
  "query": "找出执行时长超过P95的异常流程实例"
}
```

#### 25. 综合性能报告
```json
{
  "query": "生成最近30天的综合性能报告，包括执行量、成功率、平均时长和失败原因"
}
```

---

## API 参考

### 端点

#### POST /api/v1/analysis/query

执行自然语言查询

**请求体：**
```json
{
  "query": "string",
  "context": {
    "tenant_id": "string (optional)",
    "time_range": "string (optional)",
    "additional_filters": "string (optional)"
  }
}
```

**响应：**
```json
{
  "success": true,
  "sql": "string",
  "explanation": "string",
  "reasoning": "string",
  "caveats": ["string"],
  "performance_notes": "string",
  "validation": {
    "is_valid": true,
    "security_level": "SAFE",
    "issues": [],
    "complexity": {
      "tables": 1,
      "subqueries": 0
    }
  },
  "results": [{}],
  "row_count": 0,
  "columns": ["string"],
  "execution_time_ms": 0.0,
  "analysis": {
    "summary": "string",
    "key_findings": ["string"],
    "interpretation": "string",
    "recommendations": ["string"],
    "visualization_suggestions": [
      {
        "chart_type": "string",
        "title": "string",
        "x_axis": "string",
        "y_axis": "string"
      }
    ]
  },
  "timestamp": "2026-03-25T10:00:00"
}
```

---

#### GET /api/v1/analysis/schema

获取数据库 schema 信息

**响应：**
```json
{
  "success": true,
  "schema": {
    "pe_ext_procinst": {
      "description": "流程实例表",
      "columns_count": 20,
      "indexes_count": 5
    },
    "pe_ext_actinst": {...},
    "pe_ext_varinst": {...}
  },
  "timestamp": "2026-03-25T10:00:00"
}
```

---

## 技术支持

### 查看日志

如果遇到问题，可以查看服务日志：

```bash
# 查看实时日志
tail -f logs/app.log

# 查看错误日志
grep ERROR logs/app.log
```

### 常见日志信息

**成功查询：**
```
INFO: Query executed successfully: 10 rows in 45.23ms
```

**PostgreSQL 语法修复：**
```
INFO: Fixed PostgreSQL ROUND syntax in SQL query
```

**查询超时：**
```
ERROR: Query timeout after 30s
```

---

## 更新日志

**Version 0.1.0** (2026-03-25)
- ✅ 初始版本发布
- ✅ 支持中英文自然语言查询
- ✅ 三张核心表查询支持
- ✅ AI 结果分析
- ✅ PostgreSQL 9.6 兼容性

---

## 反馈与建议

如果您有任何问题或建议，欢迎通过以下方式联系我们：

- 项目 GitHub: [待补充]
- 邮件: [待补充]
- Issue Tracker: [待补充]

---

**文档版本**: 1.0
**最后更新**: 2026-03-25
