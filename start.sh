#!/bin/bash
# =====================================================
# 启动脚本 - Process Engine Performance Analyzer
# =====================================================

set -e  # 遇到错误立即退出

echo "======================================================"
echo "  Process Engine Performance Analyzer"
echo "  启动脚本"
echo "======================================================"
echo ""

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "❌ 虚拟环境不存在！"
    echo "请先运行: python3 -m venv venv"
    exit 1
fi

# 激活虚拟环境
echo "🔧 激活虚拟环境..."
source venv/bin/activate

# 检查 .env 文件
if [ ! -f ".env" ]; then
    echo "⚠️  .env 文件不存在！"
    echo "正在从 .env.example 创建..."
    cp .env.example .env
    echo "✅ .env 文件已创建"
    echo ""
    echo "⚠️  请编辑 .env 文件，设置你的 ANTHROPIC_API_KEY"
    echo "   vim .env"
    echo ""
    read -p "按回车键继续，或 Ctrl+C 退出..."
fi

# 检查依赖是否已安装
echo "🔍 检查依赖..."
if ! python -c "import fastapi" 2>/dev/null; then
    echo "⚠️  依赖未安装，正在安装..."
    pip install -r requirements.txt
    echo "✅ 依赖安装完成"
else
    echo "✅ 依赖已安装"
fi

echo ""
echo "🚀 启动服务..."
echo ""

# 启动应用
python -m app.main
