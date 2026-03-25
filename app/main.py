"""
FastAPI 应用主入口
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from datetime import datetime

from app.config import get_settings
from app.repositories.database import db
from app.api.v1 import router as api_v1_router
from app.api.v1.endpoints import dynamic_analysis

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理

    启动时初始化资源，关闭时清理资源
    """
    # 启动时：初始化数据库连接池
    print("\n" + "=" * 60)
    print(f"🚀 {settings.app_name} v{settings.app_version}")
    print("=" * 60)

    try:
        await db.connect()
        print(f"✅ 数据库连接成功")
        print(f"📊 数据库: {settings.database_url.split('@')[-1]}")  # 隐藏密码

        # 初始化动态查询服务的连接池
        await dynamic_analysis.initialize_services()
        print(f"✅ 动态查询服务初始化成功")

        print(f"🤖 AI 模型: {settings.claude_model}")
        print(f"🌐 服务端口: {settings.app_port}")
        print(f"📖 API 文档: http://localhost:{settings.app_port}/docs")
        print("=" * 60 + "\n")

    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        print("⚠️  请检查配置和连接状态")
        raise

    yield

    # 关闭时：清理资源
    print("\n正在关闭服务...")
    await dynamic_analysis.shutdown_services()
    await db.disconnect()
    print("👋 服务已停止\n")


# 创建 FastAPI 应用
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="""
    ## 基于 AI 的流程引擎性能分析工具

    本工具用于分析 SAP Digital Manufacturing Cloud Process Engine 的性能数据。

    ### 主要功能

    - **Top K 最慢流程分析**：识别执行时间最长的流程实例
    - **最频繁运行流程分析**：统计运行次数最多的流程定义
    - **AI 深度分析**：使用 Claude AI 提供性能优化建议

    ### 数据源

    - `pe_ext_procinst` - 流程实例扩展表
    - `pe_ext_actinst` - 活动实例扩展表
    - `act_re_procdef` - 流程定义表
    - `act_re_deployment` - 部署表

    ### 开发者信息

    - **后端框架**：FastAPI
    - **AI 模型**：Claude Sonnet 4.6
    - **数据库**：PostgreSQL
    """,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# CORS 配置（允许跨域请求）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 全局异常处理
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理器"""
    return JSONResponse(
        status_code=500,
        content={
            "error": "InternalServerError",
            "message": str(exc),
            "detail": f"请求路径: {request.url.path}",
            "timestamp": datetime.now().isoformat()
        }
    )


# 注册 API 路由
app.include_router(api_v1_router, prefix="/api/v1")


@app.get(
    "/",
    summary="根路径",
    description="返回 API 基本信息和文档链接"
)
async def root():
    """根路径 - API 信息"""
    return {
        "message": f"{settings.app_name} v{settings.app_version}",
        "status": "running",
        "documentation": {
            "swagger_ui": f"http://localhost:{settings.app_port}/docs",
            "redoc": f"http://localhost:{settings.app_port}/redoc",
            "openapi_json": f"http://localhost:{settings.app_port}/openapi.json"
        },
        "endpoints": {
            "health": "/api/v1/analysis/health",
            "stats": "/api/v1/analysis/stats/summary",
            "top_slowest": "/api/v1/analysis/top-slowest",
            "most_frequent": "/api/v1/analysis/most-frequent",
            "dynamic_query": "/api/v1/analysis/query",
            "schema": "/api/v1/analysis/schema"
        },
        "timestamp": datetime.now().isoformat()
    }


@app.get("/ping", summary="Ping", description="简单的健康检查")
async def ping():
    """简单的 Ping 接口"""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.app_port,
        reload=True,  # 开发模式热重载
        log_level=settings.log_level.lower()
    )
