# Process Engine Performance Analyzer

基于 AI 的流程引擎性能分析工具，用于分析 SAP Digital Manufacturing Cloud Process Engine 的性能数据。

## 🎯 功能特性

- ✅ **Top K 最慢流程分析** - 识别执行时间最长的流程实例
- ✅ **最频繁运行流程分析** - 统计运行次数最多的流程定义
- ✅ **AI 深度分析** - 使用 Claude AI 提供性能洞察和优化建议
- ✅ **自动生成 API 文档** - Swagger UI 和 ReDoc

## 🏗️ 技术栈

- **后端框架**: FastAPI 0.115+
- **数据库**: PostgreSQL 9.6+
- **AI**: Claude Sonnet 4.6 (Anthropic)
- **Python**: 3.11+
- **数据分析**: pandas, numpy

## 📦 快速开始

### 1. 环境准备

```bash
# 克隆项目（如果是新环境）
cd /Users/I605218/projects/perfAnls

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，设置你的 API Key
# vim .env 或使用其他编辑器
```

**必须配置的变量：**
```env
# 在 .env 文件中设置
ANTHROPIC_API_KEY=sk-ant-api03-xxxxxxxxxxxx  # 你的 Claude API Key
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/process-engine
```

**获取 Claude API Key：**
- 访问 https://console.anthropic.com/
- 注册/登录账号
- 在 API Keys 页面创建新的 Key

### 3. 启动数据库

确保 Process Engine 的 PostgreSQL 容器正在运行：

```bash
# 检查容器状态
docker ps | grep postgres

# 如果未运行，启动容器
cd /Users/I605218/projects/fnd-processengine-ms
docker-compose up -d postgres
```

### 4. 启动应用

```bash
# 确保虚拟环境已激活
source venv/bin/activate

# 启动开发服务器（支持热重载）
uvicorn app.main:app --reload --port 8000

# 或者直接运行
python -m app.main
```

### 5. 访问 API 文档

服务启动后，访问以下地址：

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **根路径**: http://localhost:8000/

## 📚 API 端点

### 分析接口

| 方法 | 路径 | 描述 |
|-----|------|------|
| GET | `/api/v1/analysis/top-slowest` | Top K 最慢流程分析 |
| GET | `/api/v1/analysis/most-frequent` | 最频繁运行流程分析 |
| GET | `/api/v1/analysis/health` | 健康检查 |
| GET | `/api/v1/analysis/stats/summary` | 数据库统计摘要 |

### 使用示例

#### 1. 查询 Top 10 最慢流程（最近7天）

```bash
curl "http://localhost:8000/api/v1/analysis/top-slowest?k=10"
```

#### 2. 查询指定时间范围的最慢流程

```bash
curl "http://localhost:8000/api/v1/analysis/top-slowest?k=5&start_time=2026-03-01T00:00:00&end_time=2026-03-23T23:59:59"
```

#### 3. 查询最频繁运行的流程（最近30天）

```bash
# 注意：需要先在 .env 中设置 DEFAULT_TIME_RANGE_DAYS，或者显式指定时间范围
curl "http://localhost:8000/api/v1/analysis/most-frequent?limit=10"
```

#### 4. 健康检查

```bash
curl "http://localhost:8000/api/v1/analysis/health"
```

#### 5. 数据库统计摘要

```bash
curl "http://localhost:8000/api/v1/analysis/stats/summary"
```

## 🗂️ 项目结构

```
perfAnls/
├── .env                          # 环境变量配置（需要创建）
├── .env.example                  # 环境变量模板
├── .gitignore                    # Git 忽略文件
├── requirements.txt              # Python 依赖
├── README.md                     # 项目文档
├── check_environment.py          # 环境检查脚本
├── ENVIRONMENT_SETUP.md          # 环境配置指南
│
├── app/
│   ├── main.py                  # FastAPI 应用入口
│   ├── config.py                # 配置管理
│   │
│   ├── api/                     # API 层
│   │   ├── v1/
│   │   │   ├── __init__.py      # 路由聚合
│   │   │   └── analysis.py      # 分析接口
│   │   └── models/
│   │       └── responses.py     # 响应模型
│   │
│   ├── services/                # 服务层
│   │   ├── analysis_service.py  # 分析服务
│   │   └── ai_service.py        # AI 服务
│   │
│   ├── repositories/            # 数据访问层
│   │   ├── database.py          # 数据库连接
│   │   └── performance_repo.py  # 性能查询仓库
│   │
│   └── models/                  # 领域模型
│       └── process.py           # 流程模型
│
└── tests/                       # 测试
    └── __init__.py
```

## 🔧 开发指南

### 运行环境检查

在开始开发前，运行环境检查脚本：

```bash
python3 check_environment.py
```

该脚本会检查：
- Python 版本
- 数据库连接
- 必需的 Python 包
- 环境变量配置

### 开发模式

```bash
# 激活虚拟环境
source venv/bin/activate

# 启动开发服务器（支持代码热重载）
uvicorn app.main:app --reload --port 8000

# 查看日志
# 日志会直接输出到终端
```

### 测试 API

使用 Swagger UI 进行交互式测试：

1. 访问 http://localhost:8000/docs
2. 点击 `/api/v1/analysis/stats/summary` 查看数据库统计
3. 如果有数据，尝试 `/api/v1/analysis/top-slowest`
4. 查看 AI 分析结果

### 添加新功能

1. **添加新的查询**：在 `app/repositories/performance_repo.py` 中添加方法
2. **添加新的分析逻辑**：在 `app/services/analysis_service.py` 中实现
3. **添加新的 API 端点**：在 `app/api/v1/analysis.py` 中定义路由
4. **添加新的数据模型**：在 `app/models/` 中定义 Pydantic 模型

## 📊 数据库表说明

### 核心表

- **pe_ext_procinst** - 流程实例扩展表
  - 包含流程执行时间、状态、层级关系等信息
  - 关键字段：id, start_time, end_time, status, proc_def_id

- **pe_ext_actinst** - 活动实例扩展表
  - 包含流程中每个活动的执行信息
  - 用于分析流程内部的性能瓶颈

- **act_re_procdef** - 流程定义表
  - Flowable 标准表，存储流程定义元数据
  - 关键字段：key_, name_, version_

- **act_re_deployment** - 部署表
  - 流程定义的部署信息

## 🔍 故障排查

### 问题 1: 数据库连接失败

```bash
# 检查 PostgreSQL 容器
docker ps | grep postgres

# 如果未运行，启动容器
cd /Users/I605218/projects/fnd-processengine-ms
docker-compose up -d postgres

# 查看容器日志
docker logs fnd-processengine-ms-postgres-1
```

### 问题 2: API Key 错误

```bash
# 检查 .env 文件
cat .env | grep ANTHROPIC_API_KEY

# 确认格式正确（不要有引号或多余空格）
# 正确: ANTHROPIC_API_KEY=sk-ant-api03-xxx
# 错误: ANTHROPIC_API_KEY="sk-ant-api03-xxx"
```

### 问题 3: 端口被占用

```bash
# 查找占用 8000 端口的进程
lsof -i :8000

# 停止进程或使用其他端口
uvicorn app.main:app --reload --port 8001

# 或在 .env 中修改
echo "APP_PORT=8001" >> .env
```

### 问题 4: 数据库没有数据

```bash
# 运行统计摘要检查
curl "http://localhost:8000/api/v1/analysis/stats/summary"

# 如果数据库为空，需要先运行 Process Engine 生成数据
# 或者查看 sql/sample_data.sql 插入测试数据
```

## 🚀 后续扩展

### Phase 2 - 增强分析功能

- [ ] 活动级别性能分析
- [ ] 变量大小对性能的影响分析
- [ ] 流程版本对比分析
- [ ] 时间序列趋势分析

### Phase 3 - AI 生成查询

- [ ] 自然语言转 SQL
- [ ] 查询安全验证
- [ ] 查询结果可视化

### Phase 4 - Web 界面

- [ ] Streamlit 仪表板
- [ ] 交互式图表
- [ ] 报告导出（PDF/Excel）

## 📝 License

内部项目

## 👥 Contact

如有问题，请联系项目维护者。
