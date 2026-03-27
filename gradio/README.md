# Gradio Frontend

## 简介

这是 Process Engine Performance Analyzer 的 Gradio 前端界面，提供友好的自然语言查询交互。

## 功能特性

- 🎯 自然语言输入，自动生成SQL
- 📊 数据表格展示（支持HTML渲染）
- 🧠 AI智能分析和优化建议
- 📈 可视化建议
- 🔍 预设查询示例
- ⚡ 实时连接状态检测

## 快速启动

### 方式1: 使用启动脚本（推荐）

```bash
cd /Users/I605218/projects/perfAnls
./gradio/start_gradio.sh
```

### 方式2: 手动启动

```bash
# 1. 激活虚拟环境
source venv/bin/activate

# 2. 确保后端已启动
python -m app.main  # 在另一个终端

# 3. 启动Gradio前端
cd gradio
python app.py
```

### 方式3: 使用主启动脚本

```bash
# 同时启动后端和前端
./start.sh --with-gradio
```

## 访问地址

启动成功后，访问：

- **Gradio界面**: http://localhost:7860
- **后端API文档**: http://localhost:8000/docs

## 配置

### 环境变量

可以在 `.env` 文件中配置：

```env
# 后端API地址（默认 http://localhost:8000）
API_BASE_URL=http://localhost:8000
```

### 端口配置

如果 7860 端口被占用，可以修改 `app.py` 中的端口：

```python
demo.launch(
    server_port=7861,  # 改为其他端口
    ...
)
```

## 使用说明

### 1. 输入查询

在输入框中输入自然语言查询，例如：
- "显示过去7天失败率最高的5个流程"
- "按小时分析流程执行的时间序列趋势"
- "对比昨天和今天的流程执行情况"

### 2. 查看结果

结果分为两个标签页：

**📊 SQL & 数据**
- 生成的SQL查询
- 查询结果表格

**🧠 AI分析**
- 执行摘要
- 关键发现
- 优化建议
- 可视化建议

### 3. 使用示例

点击底部的示例查询，可以快速填充常用查询。

## 故障排查

### 连接失败

**问题**: ❌ 无法连接到后端API

**解决方案**:
1. 确保后端服务已启动
   ```bash
   ./start.sh
   ```
2. 检查 `.env` 中的 `API_BASE_URL` 配置
3. 检查端口 8000 是否被占用
   ```bash
   lsof -i :8000
   ```

### 端口被占用

**问题**: 7860 端口被占用

**解决方案**:
```bash
# 查找占用进程
lsof -i :7860

# 杀死进程
kill -9 <PID>

# 或修改 app.py 中的端口
```

### 查询超时

**问题**: 查询执行时间超过60秒

**解决方案**:
1. 简化查询条件（缩小时间范围）
2. 检查数据库连接状态
3. 增加超时时间（修改 `app.py` 中的 `timeout=60`）

## 依赖

Gradio 前端依赖以下Python包：

```
gradio>=4.0.0
requests>=2.31.0
pandas>=2.0.0
python-dotenv>=1.0.0
```

这些依赖已包含在根目录的 `requirements.txt` 中。

## 开发说明

### 文件结构

```
gradio/
├── app.py              # 主应用文件
├── README.md           # 本文件
└── start_gradio.sh     # 启动脚本
```

### 修改界面

编辑 `app.py` 文件，主要区域：

- **查询逻辑**: `query_analysis()` 函数
- **UI布局**: `gr.Blocks()` 代码块
- **样式**: `custom_css` 变量
- **示例**: `EXAMPLES` 列表

### 主题定制

Gradio 支持多种主题，可以修改：

```python
with gr.Blocks(theme=gr.themes.Soft()) as demo:
    # 其他主题：
    # theme=gr.themes.Default()
    # theme=gr.themes.Glass()
    # theme=gr.themes.Monochrome()
```

## 版本历史

- **v1.0.0** (2026-03-27)
  - 初始版本
  - 支持自然语言查询
  - SQL生成和数据展示
  - AI分析功能
  - 预设查询示例

## 相关链接

- [Gradio 文档](https://www.gradio.app/docs)
- [FastAPI 后端](../app/)
- [项目主 README](../README.md)
