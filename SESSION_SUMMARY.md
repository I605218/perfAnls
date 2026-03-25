# Session Summary - Text-to-SQL Project Implementation

**Date**: 2026-03-25
**Project**: perfAnls (Process Engine Performance Analyzer)
**Goal**: 实现基于 AI 的 Text-to-SQL 动态查询系统

---

## 📋 项目概述

本项目将 SAP Digital Manufacturing Process Engine 的性能分析工具从**硬编码 SQL 查询**升级为 **AI 驱动的动态 SQL 生成系统**，支持用户通过自然语言查询数据库。

### 核心技术栈
- **Backend**: FastAPI (Python 3.11)
- **Database**: PostgreSQL 9.6 (asyncpg)
- **AI Model**: Claude Sonnet 4.6 (via SAP AI Core)
- **Architecture**: Text-to-SQL + SQL Validation + Query Execution + AI Analysis

---

## ✅ 已完成的工作 (Phase 1 & 2)

### Phase 1: Schema + Security + Prompts

#### 1.1 SQL Security Validator ✅
**文件**: `app/security/sql_validator.py`

**功能**:
- 白名单验证：只允许查询 3 张表 (`pe_ext_procinst`, `pe_ext_actinst`, `pe_ext_varinst`)
- 阻止危险操作：DROP, DELETE, UPDATE, INSERT, EXECUTE, TRUNCATE 等
- SQL 注入检测：识别常见注入模式
- CTE 支持：正确识别 WITH 子句中的临时表名
- 复杂度评估：表数量、JOIN、子查询统计

**测试**: 35 个单元测试全部通过

---

#### 1.2 Database Schema Documentation ✅
**文件**:
- `schema/pe_ext_procinst.json` (流程实例表)
- `schema/pe_ext_actinst.json` (活动实例表)
- `schema/pe_ext_varinst.json` (变量实例表)

**内容**:
- 每个字段的业务含义和技术描述
- 索引信息和性能优化建议
- 枚举值详细说明（如 status, activity_type）
- 8 个常见查询示例（每个表）
- 表关系和 JOIN 示例
- **重要**: 包含 PostgreSQL 9.6 特定语法提示

**PostgreSQL 9.6 兼容性**:
```sql
❌ 错误: ROUND(EXTRACT(EPOCH FROM (end_time - start_time)), 2)
✅ 正确: ROUND(EXTRACT(EPOCH FROM (end_time - start_time))::numeric, 2)
```

---

#### 1.3 Text-to-SQL Prompt Engineering ✅
**文件**: `app/prompts/text_to_sql_prompt.py`

**功能**:
- 构建系统 Prompt（包含 schema 和约束）
- 8 个 Few-shot 示例：
  1. 聚合查询（TOP K 最慢流程）
  2. 简单过滤（按状态查询）
  3. 活动分析（JOIN 查询）
  4. 深入分析（多条件）
  5. 时间对比（周对周）
  6. 变量分析
  7. 时间序列
  8. 子流程分析（CTE）

**测试**: 23 个单元测试全部通过

---

### Phase 2: Core Services

#### 2.1 Text-to-SQL Service ✅
**文件**: `app/services/text_to_sql_service.py`

**功能**:
1. 加载 schema 文件
2. 构建 system prompt 和 user prompt
3. 调用 Claude API (model: `claude-sonnet-4-6`)
4. 解析 JSON 响应
5. 验证生成的 SQL
6. 返回 `SQLGenerationResult`

**配置**:
- Model: `claude-sonnet-4-6` (已从 `claude-opus-4-20250514` 修正)
- Temperature: 0.0 (确保确定性)
- Max tokens: 4096

**测试**: 18 个单元测试全部通过

---

#### 2.2 Dynamic Query Service ✅
**文件**: `app/services/dynamic_query_service.py`

**功能**:
- 异步连接池管理 (asyncpg)
- 查询执行（带超时保护）
- 只读事务（安全措施）
- 结果格式化：
  - datetime → ISO 8601
  - Decimal → float
  - NULL 保留
  - Binary → `<binary data>`
- **PostgreSQL 语法自动修复** (重要!)

**PostgreSQL 9.6 语法修复**:
```python
def _fix_postgresql_round_syntax(self, sql: str) -> str:
    """
    自动在所有 EXTRACT(EPOCH FROM ...) 后添加 ::numeric 类型转换
    解决 PostgreSQL 9.6 的 ROUND 函数类型兼容问题
    """
```

**连接池配置**:
- min_size: 2
- max_size: 10
- query_timeout: 30s
- max_rows: 1000

**测试**: 20 个单元测试全部通过

---

#### 2.3 AI Analysis Service ✅
**文件**: `app/services/ai_analysis_service.py`

**功能**:
- 分析 SQL 查询结果
- 生成业务洞察和建议
- 使用 Claude Sonnet 4.6 (节省成本)
- Temperature: 0.3 (平衡创造力)

**返回结构**:
```json
{
  "summary": "执行摘要",
  "key_findings": ["发现1", "发现2"],
  "interpretation": "数据解读",
  "recommendations": ["建议1", "建议2"],
  "visualization_suggestions": [
    {
      "chart_type": "bar chart",
      "title": "图表标题",
      "x_axis": "X轴",
      "y_axis": "Y轴"
    }
  ]
}
```

**测试**: 17 个单元测试全部通过

---

#### 2.4 Dynamic Query API Endpoint ✅
**文件**: `app/api/v1/endpoints/dynamic_analysis.py`

**API 端点**:
- `POST /api/v1/analysis/query` - 自然语言查询
- `GET /api/v1/analysis/schema` - 获取 schema 信息

**请求格式**:
```json
{
  "query": "找出最慢的10个流程",
  "context": {
    "tenant_id": "optional",
    "time_range": "last 7 days"
  }
}
```

**响应格式**:
```json
{
  "success": true,
  "sql": "生成的 SQL",
  "explanation": "SQL 解释",
  "reasoning": "生成原因",
  "validation": {
    "is_valid": true,
    "security_level": "SAFE",
    "complexity": {"tables": 1, "subqueries": 0}
  },
  "results": [...],
  "row_count": 10,
  "execution_time_ms": 45.2,
  "analysis": {
    "summary": "...",
    "key_findings": [...],
    "recommendations": [...]
  }
}
```

**服务初始化**:
- 在 `app/main.py` 的 `lifespan` 中初始化连接池
- 应用关闭时自动清理资源

---

## 🐛 已修复的关键问题

### 1. PostgreSQL 9.6 ROUND 语法兼容性 ⚠️ **最重要**

**问题**:
```
UndefinedFunctionError: function round(double precision, integer) does not exist
```

**根本原因**:
PostgreSQL 9.6 的 ROUND 函数不支持直接对 `double precision` 类型使用精度参数，必须先转换为 `numeric` 类型。

**解决方案 (三层防护)**:

1. **Schema 文档** (`schema/*.json`)
   - 在 `ai_analysis_guidelines` 中添加：
   ```
   **CRITICAL**: PostgreSQL 9.6的ROUND函数必须显式转换类型：
   ROUND(EXTRACT(EPOCH FROM (end_time - start_time))::numeric, 2)
   ```

2. **动态修复** (`app/services/dynamic_query_service.py`)
   ```python
   def _fix_postgresql_round_syntax(self, sql: str) -> str:
       """在查询执行前自动修复 ROUND 语法"""
       # 在所有 EXTRACT(EPOCH FROM ...) 后添加 ::numeric
   ```

3. **示例修复** (待完成)
   - Schema 中的 `common_queries` 示例也需要更新
   - 使用正确的语法避免 Claude 模仿错误示例

---

### 2. 数据库连接池未初始化

**问题**:
```
Database connection pool not initialized
```

**解决方案**:
在 `app/main.py` 的 `lifespan` 函数中添加：
```python
await dynamic_analysis.initialize_services()
# 关闭时
await dynamic_analysis.shutdown_services()
```

---

### 3. CTE 验证问题

**问题**:
SQL Validator 将 CTE (WITH 子句) 中的临时表名误判为未授权表

**解决方案**:
在 `sql_validator.py` 中提取 CTE 名称并排除：
```python
cte_pattern = r'WITH\s+([a-zA-Z_][a-zA-Z0-9_]*)\s+AS'
cte_matches = re.findall(cte_pattern, sql, re.IGNORECASE)
# 验证时跳过 CTE 名称
```

---

### 4. 模型名称错误

**问题**:
```
Invalid model specified. The model claude-opus-4-20250514 is not supported
```

**解决方案**:
更新为 SAP AI Core 支持的模型：
- `text_to_sql_service.py`: `claude-opus-4-20250514` → `claude-sonnet-4-6`
- `ai_analysis_service.py`: `claude-sonnet-4-20250514` → `claude-sonnet-4-6`

---

## 🧪 测试结果

### 单元测试 (全部通过 ✅)
- SQL Validator: 35 tests
- Text-to-SQL Prompt: 23 tests
- Text-to-SQL Service: 18 tests
- Dynamic Query Service: 20 tests
- AI Analysis Service: 17 tests
- **Total: 113 tests ✅**

### 集成测试 (部分通过)
**执行时间**: 约 2-3 分钟 (因为需要多次 AI API 调用)

**测试用例**: 12 个
- ✅ 通过: 4 个 (33.3%)
- ❌ 失败: 8 个 (66.7%)

**失败原因分析**:
1. **PostgreSQL ROUND 语法** (6 个失败)
   - Claude 有时会忘记添加 `::numeric`
   - 解决方案：动态修复函数已实现

2. **CTE 验证误报** (1 个失败)
   - `ranked_activities` 被误判为未授权表

3. **JSON 解析错误** (1 个失败)
   - 偶发，Claude 响应格式问题

**成功的测试展示了**:
- ✅ Text-to-SQL 生成能力
- ✅ SQL 安全验证
- ✅ 查询执行
- ✅ AI 结果分析（高质量）

---

## 🎯 手动测试指南

### 启动应用
```bash
./start.sh
```

### 访问 Swagger UI
http://localhost:8000/docs

### 预期启动日志
```
🚀 Process Engine Performance Analyzer v0.1.0
==============================================================
✅ 数据库连接成功
📊 数据库: localhost:5432/process-engine
✅ 动态查询服务初始化成功  ← 重要！
🤖 AI 模型: claude-sonnet-4-6
🌐 服务端口: 8000
📖 API 文档: http://localhost:8000/docs
==============================================================
```

### 测试用例

#### Test 1: 健康检查 ✅
```
GET /api/v1/analysis/health
```
**预期**: 返回服务状态和数据库连接信息

---

#### Test 2: 获取 Schema ✅
```
GET /api/v1/analysis/schema
```
**预期**: 返回 3 张表的完整 schema

---

#### Test 3: 简单统计查询 ✅ (保证成功)
```json
POST /api/v1/analysis/query
{
  "query": "统计流程实例总数"
}
```
**预期结果**:
```json
{
  "success": true,
  "sql": "SELECT COUNT(*) as total_count FROM pe_ext_procinst",
  "results": [{"total_count": 0}],
  "analysis": {
    "summary": "查询返回流程实例总数为0...",
    "recommendations": [...]
  }
}
```

---

#### Test 4: 带过滤条件的查询 (测试 ROUND 修复)
```json
POST /api/v1/analysis/query
{
  "query": "查询状态为 COMPLETED 的流程实例数量"
}
```
**关键**: 如果 SQL 包含 duration 计算，应该自动修复 ROUND 语法

**终端应显示**:
```
INFO: Fixed PostgreSQL ROUND syntax in SQL query
```

---

#### Test 5: 英文查询 ✅
```json
POST /api/v1/analysis/query
{
  "query": "Show me the total number of process instances"
}
```
**预期**: 支持中英文双语

---

#### Test 6: 带上下文的查询
```json
POST /api/v1/analysis/query
{
  "query": "统计流程实例数量",
  "context": {
    "tenant_id": "tenant_001",
    "time_range": "last 7 days"
  }
}
```
**预期**: SQL 应包含 context 中的条件

---

## 📁 项目文件结构

```
perfAnls/
├── app/
│   ├── main.py                          # FastAPI 应用入口 ✅ 已更新
│   ├── config.py                        # 配置管理
│   ├── api/
│   │   └── v1/
│   │       ├── __init__.py              # ✅ 已更新（注册动态查询端点）
│   │       ├── analysis.py              # 原有端点
│   │       └── endpoints/
│   │           └── dynamic_analysis.py  # ✅ 新增（动态查询端点）
│   ├── services/
│   │   ├── text_to_sql_service.py       # ✅ Text-to-SQL 服务
│   │   ├── dynamic_query_service.py     # ✅ 查询执行服务（含语法修复）
│   │   └── ai_analysis_service.py       # ✅ AI 分析服务
│   ├── security/
│   │   └── sql_validator.py             # ✅ SQL 安全验证器
│   └── prompts/
│       └── text_to_sql_prompt.py        # ✅ Prompt 构建器
├── schema/
│   ├── pe_ext_procinst.json             # ✅ 流程实例表 schema
│   ├── pe_ext_actinst.json              # ✅ 活动实例表 schema
│   └── pe_ext_varinst.json              # ✅ 变量实例表 schema
├── tests/
│   ├── test_sql_validator.py            # ✅ 35 tests
│   ├── test_text_to_sql_prompt.py       # ✅ 23 tests
│   ├── test_text_to_sql_service.py      # ✅ 18 tests
│   ├── test_dynamic_query_service.py    # ✅ 20 tests
│   ├── test_ai_analysis_service.py      # ✅ 17 tests
│   ├── test_dynamic_analysis_endpoint.py # ⚠️ 需要改进（mock 问题）
│   └── integration/
│       └── test_text_to_sql_integration.py # ✅ 集成测试（33% 通过率）
├── .env                                 # ✅ 已配置（API key, 数据库）
├── planA.md                             # ✅ 实施计划
├── start.sh                             # ✅ 启动脚本
└── SESSION_SUMMARY.md                   # ✅ 本文档
```

---

## 🔧 配置文件 (.env)

```bash
# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/process-engine

# Anthropic API
ANTHROPIC_API_KEY=b8cc8d4d-baf8-4ed5-9081-272a098fc964
BASE_URL=http://localhost:6655/anthropic
CLAUDE_MODEL=claude-sonnet-4-6

# Application
APP_PORT=8000
LOG_LEVEL=INFO

# Analysis Settings
DEFAULT_TOP_K=10
DEFAULT_TIME_RANGE_DAYS=7
MAX_QUERY_RESULTS=1000
```

---

## ⚠️ 已知问题和待优化

### 1. PostgreSQL 9.6 ROUND 语法 (高优先级)
**状态**: 已实现动态修复，但仍需优化

**问题**:
- Claude 有时会生成错误语法
- Schema 示例中也包含错误语法

**解决方案**:
1. ✅ 已实现：动态修复函数
2. ⚠️ 待完成：更新所有 schema 示例
3. ⚠️ 待完成：改进 prompt 强调语法要求

---

### 2. JSON 解析错误 (中优先级)
**问题**:
偶尔 Claude 返回的 JSON 格式有问题

**解决方案**:
- 添加更严格的 JSON 解析和错误恢复
- 在 prompt 中明确要求标准 JSON 格式

---

### 3. CTE 验证误报 (低优先级)
**问题**:
复杂 CTE (如嵌套) 可能被误判

**解决方案**:
- 改进 CTE 名称提取的正则表达式
- 支持递归 CTE

---

### 4. 集成测试通过率 (中优先级)
**当前**: 33.3% (4/12)

**目标**: 80%+

**行动**:
1. 修复 ROUND 语法问题
2. 优化 few-shot 示例
3. 改进 schema 文档

---

## 📝 下一步工作 (Phase 3 & 4)

### Phase 3: 测试与优化
- [ ] 修复所有 schema 示例中的 ROUND 语法
- [ ] 提高集成测试通过率到 80%+
- [ ] 优化 SQL 生成质量
- [ ] 性能测试和优化
- [ ] 错误处理优化

### Phase 4: 文档与部署
- [ ] API 文档完善
- [ ] 用户手册
- [ ] 部署指南
- [ ] 监控和日志配置

---

## 💡 重要提示

### 1. 每次重启应用时检查
```bash
./start.sh
```
**必须看到**:
```
✅ 动态查询服务初始化成功
```

### 2. 如果遇到 ROUND 语法错误
**不要惊慌**！动态修复函数会处理大部分情况。

**检查终端是否显示**:
```
INFO: Fixed PostgreSQL ROUND syntax in SQL query
```

### 3. 数据库为空是正常的
当前测试环境的 `pe_ext_procinst` 表是空的（0 条记录）。

这不影响功能测试，AI 会针对空结果给出建议。

---

## 🎉 项目亮点

### 1. 安全优先
- SQL 白名单验证
- 只读事务
- SQL 注入防护
- 查询超时保护

### 2. 高质量 AI 分析
- Few-shot learning (8 个示例)
- 业务上下文理解
- 可操作的建议
- 可视化建议

### 3. 完善的错误处理
- 分阶段错误报告 (sql_generation, validation, execution, analysis)
- 详细的错误信息
- 优雅降级（分析失败不影响查询结果）

### 4. PostgreSQL 兼容性
- 自动语法修复
- 支持 PostgreSQL 9.6 特性
- 详细的兼容性文档

---

## 📞 联系和支持

### 项目信息
- **项目名**: perfAnls
- **版本**: 0.1.0
- **Python**: 3.11
- **数据库**: PostgreSQL 9.6

### 文档位置
- 实施计划: `planA.md`
- API 文档: http://localhost:8000/docs
- 本总结: `SESSION_SUMMARY.md`

---

## 🔄 会话恢复提示

如果需要继续开发，重点关注：

1. **PostgreSQL ROUND 语法修复**: 这是当前最重要的问题
   - 检查 `dynamic_query_service.py` 的 `_fix_postgresql_round_syntax()` 方法
   - 测试各种 SQL 模式：AVG, MAX, SUM 等聚合函数

2. **集成测试优化**: 提高通过率
   - 分析失败的 8 个测试用例
   - 改进 few-shot 示例
   - 优化 prompt engineering

3. **Schema 示例更新**: 确保所有示例使用正确语法
   - `schema/pe_ext_procinst.json`
   - `schema/pe_ext_actinst.json`
   - `schema/pe_ext_varinst.json`

---

**文档生成时间**: 2026-03-25
**文档版本**: 1.0
**状态**: Phase 2 完成，Phase 3 进行中
