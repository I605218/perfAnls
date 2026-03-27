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

# 检查命令行参数
WITH_GRADIO=false
if [ "$1" == "--with-gradio" ]; then
    WITH_GRADIO=true
    echo "🎨 将同时启动 Gradio 前端"
    echo ""
fi

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

# 如果需要启动 Gradio
if [ "$WITH_GRADIO" = true ]; then
    echo "======================================================"
    echo "  启动模式: 后端 + Gradio 前端"
    echo "======================================================"
    echo ""
    echo "📡 后端API: http://localhost:8000"
    echo "🌐 Gradio前端: http://localhost:7860"
    echo ""
    echo "💡 使用 Ctrl+C 停止所有服务"
    echo ""

    # 在后台启动后端
    echo "🔧 启动后端服务..."
    python -m app.main &
    BACKEND_PID=$!

    # 等待后端启动
    echo "⏳ 等待后端服务就绪..."
    for i in {1..30}; do
        if curl -s http://localhost:8000/ping > /dev/null 2>&1; then
            echo "✅ 后端服务已就绪"
            break
        fi
        if [ $i -eq 30 ]; then
            echo "❌ 后端服务启动超时"
            kill $BACKEND_PID 2>/dev/null || true
            exit 1
        fi
        sleep 1
    done

    # 启动 Gradio
    echo ""
    echo "🎨 启动 Gradio 前端..."
    cd gradio
    python app.py &
    GRADIO_PID=$!

    # 等待用户中断
    echo ""
    echo "======================================================"
    echo "  ✅ 所有服务已启动"
    echo "======================================================"

    # 捕获 Ctrl+C
    trap "echo ''; echo '🛑 正在停止所有服务...'; kill $BACKEND_PID $GRADIO_PID 2>/dev/null || true; exit 0" INT

    # 等待进程
    wait $BACKEND_PID $GRADIO_PID
else
    echo "======================================================"
    echo "  启动模式: 仅后端"
    echo "======================================================"
    echo ""
    echo "📡 后端API: http://localhost:8000"
    echo "📚 API文档: http://localhost:8000/docs"
    echo ""
    echo "💡 如需启动前端，运行:"
    echo "   ./start.sh --with-gradio"
    echo "   或"
    echo "   ./gradio/start_gradio.sh"
    echo ""

    # 启动应用
    python -m app.main
fi
