#!/bin/bash
# =====================================================
# 一键安装和验证脚本
# =====================================================

echo "======================================================"
echo "  Process Engine Performance Analyzer"
echo "  一键安装和验证"
echo "======================================================"
echo ""

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo -e "${RED}❌ 虚拟环境不存在！${NC}"
    echo "请先运行: python3 -m venv venv"
    exit 1
fi

# 激活虚拟环境
echo "🔧 激活虚拟环境..."
source venv/bin/activate

# 安装依赖
echo ""
echo "📦 安装 Python 依赖..."
pip install -r requirements.txt

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ 依赖安装成功${NC}"
else
    echo -e "${RED}❌ 依赖安装失败${NC}"
    exit 1
fi

# 检查 .env 文件
echo ""
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠️  .env 文件不存在，从模板创建...${NC}"
    cp .env.example .env
    echo -e "${GREEN}✅ .env 文件已创建${NC}"
    echo ""
    echo -e "${YELLOW}⚠️  重要：请编辑 .env 文件，设置你的 ANTHROPIC_API_KEY${NC}"
    echo "   vim .env"
    echo ""
else
    echo -e "${GREEN}✅ .env 文件已存在${NC}"
fi

# 运行环境检查
echo ""
echo "🔍 运行环境检查..."
echo ""
python check_environment.py

echo ""
echo "======================================================"
echo "  安装完成！"
echo "======================================================"
echo ""
echo "📝 下一步操作："
echo ""
echo "1. 确认 .env 文件中的 ANTHROPIC_API_KEY 已设置"
echo "   vim .env"
echo ""
echo "2. 确认数据库容器正在运行"
echo "   docker ps | grep postgres"
echo ""
echo "3. 启动服务"
echo "   选项A: 仅启动后端"
echo "     ./start.sh"
echo ""
echo "   选项B: 同时启动后端和前端"
echo "     ./start.sh --with-gradio"
echo ""
echo "   选项C: 仅启动前端 (需要后端已运行)"
echo "     ./gradio/start_gradio.sh"
echo ""
echo "4. 访问应用"
echo "   后端API文档: http://localhost:8000/docs"
echo "   Gradio前端:   http://localhost:7860"
echo ""
echo "======================================================"
