# Plan A: Text-to-SQL + AI Analysis 方案

## 方案概述

构建一个自然语言驱动的性能分析系统，让AI理解数据库schema后，根据用户的自然语言查询动态生成SQL并分析结果，替代当前hardcode的查询方式。

## 核心流程

```
用户自然语言查询
  ↓
AI理解意图并解析schema
  ↓
AI生成PostgreSQL查询语句
  ↓
执行SQL查询（带安全验证）
  ↓
AI分析查询结果
  ↓
返回业务洞察和建议
```

## 待办事项清单

### Phase 1: Schema文档与基础架构（预计1-2周）

#### Task 1.1: 编写数据库Schema文档
- [ ] 分析pe_ext_procinst表结构
  - [ ] 记录所有字段的业务含义
  - [ ] 标注索引字段
  - [ ] 编写常见查询示例（5-10个）
  - [ ] 说明status、sub_status等枚举字段的可能值

- [ ] 分析pe_ext_actinst表结构
  - [ ] 记录所有字段的业务含义
  - [ ] 标注索引字段
  - [ ] 编写常见查询示例
  - [ ] 说明与流程实例的关系

- [ ] 分析pe_ext_varinst表结构
  - [ ] 记录所有字段的业务含义
  - [ ] 标注索引字段
  - [ ] 编写常见查询示例
  - [ ] 说明变量存储机制

- [ ] 定义表之间的关系
  - [ ] 流程实例 ↔ 活动实例（一对多）
  - [ ] 流程实例 ↔ 变量实例（一对多）
  - [ ] 流程实例的父子关系（parent_inst_id, root_inst_id）

- [ ] 创建schema文档文件
  - [ ] 选择文档格式（推荐YAML或JSON）
  - [ ] 编写完整的schema.yaml文件
  - [ ] 添加性能优化提示
  - [ ] 添加业务上下文说明

**产出文件**: `schema.yaml` 或 `schema.json`

#### Task 1.2: 设计SQL安全验证机制
- [ ] 实现SQL解析器
  - [ ] 只允许SELECT语句
  - [ ] 禁止DROP、DELETE、UPDATE、INSERT等操作
  - [ ] 禁止执行存储过程或函数

- [ ] 实现查询限制
  - [ ] 设置查询超时时间（如30秒）
  - [ ] 限制结果集大小（如最多10000行）
  - [ ] 限制JOIN的表数量

- [ ] 实现数据库连接隔离
  - [ ] 使用只读数据库用户
  - [ ] 或使用只读事务模式

**产出文件**: `app/security/sql_validator.py`

#### Task 1.3: 设计Prompt模板
- [ ] 编写System Prompt
  - [ ] 定义AI的角色（性能分析专家）
  - [ ] 嵌入schema文档内容
  - [ ] 定义输出格式要求
  - [ ] 添加SQL生成约束条件

- [ ] 编写Few-shot示例
  - [ ] 准备5-10个典型查询示例
  - [ ] 每个示例包含：自然语言 → SQL → 解释

- [ ] 定义输出格式
  - [ ] SQL语句
  - [ ] SQL解释（为什么这样写）
  - [ ] 预期结果说明

**产出文件**: `app/prompts/text_to_sql_prompt.py`

### Phase 2: 核心功能实现（预计1-2周）

#### Task 2.1: 实现动态SQL生成服务
- [ ] 创建TextToSQLService类
  - [ ] 加载schema文档
  - [ ] 构建完整的Prompt
  - [ ] 调用Claude API生成SQL
  - [ ] 解析AI返回的SQL语句

- [ ] 实现SQL验证流程
  - [ ] 调用SQL安全验证器
  - [ ] 处理验证失败的情况
  - [ ] 记录验证日志

**产出文件**: `app/services/text_to_sql_service.py`

#### Task 2.2: 实现动态查询执行
- [ ] 创建DynamicQueryService类
  - [ ] 接收验证后的SQL
  - [ ] 使用asyncpg执行查询
  - [ ] 处理查询超时
  - [ ] 处理查询异常

- [ ] 实现结果格式化
  - [ ] 将查询结果转换为JSON
  - [ ] 处理NULL值
  - [ ] 处理时间戳格式

**产出文件**: `app/services/dynamic_query_service.py`

#### Task 2.3: 实现AI结果分析
- [ ] 创建AIAnalysisService类
  - [ ] 接收SQL查询结果
  - [ ] 构建分析Prompt
  - [ ] 调用Claude API进行分析
  - [ ] 生成业务洞察

- [ ] 设计分析输出格式
  - [ ] 核心发现（Key Findings）
  - [ ] 数据解读（Data Interpretation）
  - [ ] 优化建议（Recommendations）
  - [ ] 可视化建议（Visualization Suggestions）

**产出文件**: `app/services/ai_analysis_service.py`

#### Task 2.4: 创建新的API端点
- [ ] 设计API接口
  - [ ] POST `/api/v1/analysis/query` - 自然语言查询
  - [ ] 请求格式：`{"query": "找出最慢的10个流程"}`
  - [ ] 响应格式：`{sql, explanation, results, analysis, recommendations}`

- [ ] 实现API路由
  - [ ] 参数验证
  - [ ] 调用Text-to-SQL服务
  - [ ] 调用动态查询服务
  - [ ] 调用AI分析服务
  - [ ] 错误处理

**产出文件**: `app/api/v1/endpoints/dynamic_analysis.py`

### Phase 3: 测试与优化（预计1周）

#### Task 3.1: 功能测试
- [ ] 准备测试用例集
  - [ ] 简单查询（单表、单条件）
  - [ ] 中等复杂度查询（多条件、聚合）
  - [ ] 复杂查询（多表JOIN、子查询）
  - [ ] 边界情况（空结果、大结果集）

- [ ] 执行测试
  - [ ] 验证SQL生成准确性
  - [ ] 验证安全验证有效性
  - [ ] 验证查询执行正确性
  - [ ] 验证AI分析质量

**产出文件**: `tests/test_dynamic_analysis.py`

#### Task 3.2: SQL生成优化
- [ ] 分析SQL生成失败案例
  - [ ] 收集AI生成错误SQL的情况
  - [ ] 分析失败原因

- [ ] 优化Prompt
  - [ ] 增加更多Few-shot示例
  - [ ] 改进schema描述
  - [ ] 添加更多约束条件

- [ ] 实现反馈机制
  - [ ] 记录用户对SQL的评价
  - [ ] 保存成功的查询示例
  - [ ] 逐步积累查询知识库

#### Task 3.3: 性能优化
- [ ] 实现查询缓存
  - [ ] 缓存相同的自然语言查询
  - [ ] 设置合理的缓存过期时间

- [ ] 优化AI调用
  - [ ] 减少不必要的Prompt内容
  - [ ] 考虑使用流式响应

- [ ] 数据库查询优化
  - [ ] 分析慢查询
  - [ ] 添加必要的索引建议

### Phase 4: 文档与部署（预计3-5天）

#### Task 4.1: 编写文档
- [ ] API文档
  - [ ] 更新Swagger文档
  - [ ] 添加查询示例
  - [ ] 说明支持的查询类型

- [ ] 用户指南
  - [ ] 如何使用自然语言查询
  - [ ] 查询技巧和最佳实践
  - [ ] 常见问题FAQ

**产出文件**: `docs/text_to_sql_guide.md`

#### Task 4.2: 配置管理
- [ ] 添加配置项
  - [ ] SQL查询超时时间
  - [ ] 结果集大小限制
  - [ ] 缓存配置
  - [ ] AI模型选择（Sonnet vs Opus）

- [ ] 环境变量
  - [ ] 更新.env.example
  - [ ] 说明新增的配置项

#### Task 4.3: 部署与监控
- [ ] 部署准备
  - [ ] 更新依赖项
  - [ ] 测试生产环境

- [ ] 监控指标
  - [ ] SQL生成成功率
  - [ ] 查询执行时间
  - [ ] AI分析响应时间
  - [ ] 错误率统计

## 技术栈

- **Schema文档**: YAML或JSON
- **SQL验证**: sqlparse（Python SQL解析库）
- **AI服务**: Claude API (Anthropic)
- **查询执行**: asyncpg
- **缓存**: Redis（可选，Phase 3）
- **测试**: pytest

## 关键文件结构

```
perfAnls/
├── schema.yaml                          # 数据库schema文档（新增）
├── app/
│   ├── prompts/
│   │   └── text_to_sql_prompt.py       # Prompt模板（新增）
│   ├── security/
│   │   └── sql_validator.py            # SQL安全验证（新增）
│   ├── services/
│   │   ├── text_to_sql_service.py      # Text-to-SQL服务（新增）
│   │   ├── dynamic_query_service.py    # 动态查询服务（新增）
│   │   └── ai_analysis_service.py      # AI分析服务（增强）
│   └── api/v1/endpoints/
│       └── dynamic_analysis.py         # 动态分析API（新增）
├── tests/
│   └── test_dynamic_analysis.py        # 测试用例（新增）
└── docs/
    └── text_to_sql_guide.md            # 用户指南（新增）
```

## 风险与挑战

### 风险1: SQL生成准确性
- **影响**: AI生成错误的SQL导致错误结果
- **缓解**:
  - 高质量的schema文档
  - 充分的Few-shot示例
  - 让AI解释SQL（用户可判断）
  - 实施用户反馈机制

### 风险2: 安全性
- **影响**: 恶意查询或SQL注入
- **缓解**:
  - 严格的SQL验证
  - 只读数据库连接
  - 查询超时和大小限制

### 风险3: 性能
- **影响**: AI生成低效的SQL
- **缓解**:
  - 在schema中标注索引
  - 提供查询优化指南
  - 监控慢查询并优化

### 风险4: 成本
- **影响**: 频繁调用Claude API
- **缓解**:
  - 实施查询缓存
  - 使用合适的模型（Sonnet vs Opus）
  - 优化Prompt大小

## 成功标准

1. **功能完整性**: 能够处理80%以上的常见性能分析查询
2. **准确性**: SQL生成准确率 > 90%
3. **安全性**: 通过所有SQL安全验证测试，零安全事故
4. **性能**: API响应时间 < 5秒（P95）
5. **用户体验**: 用户无需了解SQL即可进行复杂分析

## 下一步行动

**建议立即开始**:
1. Task 1.1: 分析并编写pe_ext_procinst表的schema文档（可以作为示例）
2. 与熟悉业务的同事review schema文档的业务语义
3. 准备5个典型的性能分析问题作为测试用例

**需要决策**:
1. Schema文档格式选择YAML还是JSON？（建议YAML，更易读）
2. 是否需要实施查询缓存？（建议Phase 2就实施）
3. AI分析的详细程度？（建议可配置：简洁/详细/专家模式）
