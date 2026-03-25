"""
API v1 路由聚合
"""
from fastapi import APIRouter
from app.api.v1 import analysis
from app.api.v1.endpoints import dynamic_analysis

# 创建 v1 路由器
router = APIRouter()

# 注册子路由
router.include_router(analysis.router)
router.include_router(dynamic_analysis.router)

# 后期可以添加更多路由
# from app.api.v1 import query, reports
# router.include_router(query.router)
# router.include_router(reports.router)
