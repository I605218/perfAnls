#!/bin/bash
# =====================================================
# Gradio Frontend 启动脚本
# =====================================================

set -e  # 遇到错误立即退出

echo "======================================================"
echo "  Process Engine Performance Analyzer"
echo "  Gradio Frontend 启动"
echo "======================================================"
echo ""

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 获取脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

cd "$PROJECT_ROOT"

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo -e "${RED}❌ 虚拟环境不存在！${NC}"
    echo "请先运行: python3 -m venv venv"
    exit 1
fi

# 激活虚拟环境
echo "🔧 激活虚拟环境..."
source venv/bin/activate

# 检查 gradio 是否已安装
echo "🔍 检查依赖..."
if ! python -c "import gradio" 2>/dev/null; then
    echo -e "${YELLOW}⚠️  Gradio 未安装，正在安装依赖...${NC}"
    pip install -r requirements.txt
    echo -e "${GREEN}✅ 依赖安装完成${NC}"
else
    echo -e "${GREEN}✅ Gradio 已安装${NC}"
fi

# 检查后端是否运行
echo ""
echo "🔍 检查后端状态..."
if curl -s http://localhost:8000/ping > /dev/null 2>&1; then
    echo -e "${GREEN}✅ 后端服务正在运行${NC}"
else
    echo -e "${YELLOW}⚠️  后端服务未运行${NC}"
    echo ""
    echo "请在另一个终端启动后端："
    echo "  ./start.sh"
    echo "  或"
    echo "  python -m app.main"
    echo ""
    read -p "按回车键继续启动 Gradio (将无法连接后端)，或 Ctrl+C 退出..."
fi

echo ""
echo "======================================================"
echo "  🚀 启动 Gradio 前端..."
echo "======================================================"
echo ""
echo "📡 后端API地址: http://localhost:8000"
echo "🌐 前端界面地址: http://localhost:7860"
echo ""
echo "💡 使用 Ctrl+C 停止服务"
echo ""
echo "======================================================"
echo ""

# 启动 Gradio
cd "$SCRIPT_DIR"
python app.py
