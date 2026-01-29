"""
API路由模块
提供交易决策系统的API接口
"""

from .integrated_routes import app, health_router, analysis_router

__all__ = ["app", "health_router", "analysis_router"]
