"""
交易决策系统 - API路由
只包含接口定义，业务逻辑由服务层处理
"""

import sys
from pathlib import Path
from typing import Optional, List
from fastapi import FastAPI, HTTPException, APIRouter
from pydantic import BaseModel
from enum import Enum

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime, timezone
from trading_decision_system.utils.config_loader import ConfigLoader
from trading_decision_system.services.analysis_strategy import AnalysisStrategyFactory


class AnalysisRole(str, Enum):
    STRATEGIST = "strategist"
    TECHNICAL = "technical"
    RISK_ASSESSOR = "risk_assessor"


class AnalysisRequest(BaseModel):
    symbols: List[str]
    role: Optional[AnalysisRole] = AnalysisRole.TECHNICAL


class AnalysisResponse(BaseModel):
    success: bool
    message: str
    data: Optional[dict] = None
    error: Optional[str] = None


class CommonTechnicalAnalysisRequest(BaseModel):
    symbol: str
    user_message: Optional[str] = ""
    additional_instructions: Optional[str] = ""


class CommonTechnicalAnalysisResponse(BaseModel):
    success: bool
    message: str
    symbol: str
    analysis_time: str
    markdown_report: Optional[str] = None
    model_analyses: Optional[dict] = None
    error: Optional[str] = None


# 服务初始化
config = ConfigLoader()

# 策略实例缓存
strategy_instances = {}

async def get_strategy(strategy_type: str):
    """
    获取策略实例
    
    Args:
        strategy_type: 策略类型
        
    Returns:
        策略实例
    """
    if strategy_type not in strategy_instances:
        strategy_instances[strategy_type] = AnalysisStrategyFactory.get_strategy(strategy_type, config)
    return strategy_instances[strategy_type]


app = FastAPI(
    title="交易决策系统 API",
    description="整合定时任务和API接口的交易决策系统",
    version="1.0.0"
)

# 创建API路由
health_router = APIRouter(prefix="", tags=["健康检查"])
analysis_router = APIRouter(prefix="/api/v1", tags=["分析决策"])


@app.on_event("startup")
async def startup_event():
    from trading_decision_system.utils.logger import setup_logger
    
    logger = setup_logger(
        name="integrated_service",
        log_level="INFO",
        log_file="./trading_decision_system/logs/integrated_service.log"
    )
    
    logger.info("启动整合服务...")
    
    try:
        # 预加载策略实例
        await get_strategy("standard")
        await get_strategy("common_technical")
        logger.info("策略实例初始化成功")
    except Exception as e:
        logger.error(f"服务初始化失败: {e}")
        raise


@health_router.get("/")
async def root():
    return {
        "message": "交易决策系统 - 整合服务运行中",
        "version": "1.0.0",
        "features": [
            "定时任务 (每5分钟)",
            "API接口触发分析 (方案一)",
            "通用技术分析 (方案二)"
        ],
        "endpoints": [
            "/health - 健康检查",
            "/api/v1/analyze - 触发分析决策 (方案一)",
            "/api/v1/analyze-common-technical - 通用技术分析 (方案二)"
        ]
    }


@health_router.get("/health")
async def health_check():
    """健康检查接口"""
    try:
        # 检查策略实例是否可以正常获取
        await get_strategy("standard")
        await get_strategy("common_technical")
        return {
            "status": "healthy",
            "message": "整合服务运行正常",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"服务未初始化: {str(e)}")


@analysis_router.post("/analyze", response_model=AnalysisResponse)
async def trigger_analysis(request: AnalysisRequest):
    """
    触发分析决策接口（方案一）
    
    Args:
        symbols: 要分析的交易对列表
        role: 分析角色
        
    Returns:
        分析结果
    """
    try:
        from trading_decision_system.utils.logger import setup_logger
        
        logger = setup_logger(
            name="analyze_endpoint",
            log_level="INFO",
            log_file="./trading_decision_system/logs/api.log"
        )
        
        if not request.symbols:
            raise HTTPException(status_code=400, detail="交易对列表不能为空")
        
        logger.info(f"收到分析请求: symbols={request.symbols}, role={request.role}")
        
        # 获取标准分析策略
        strategy = await get_strategy("standard")
        
        results = {}
        errors = {}
        
        for symbol in request.symbols:
            try:
                result = await strategy.execute(symbol, request.role.value)
                results[symbol] = {
                    "success": True,
                    "decision": result['final_decision']['final_decision']['action'].upper(),
                    "confidence": result['final_decision']['final_decision']['confidence_score'],
                    "entry_price": result['final_decision']['final_decision']['entry_price'],
                    "stop_loss": result['final_decision']['final_decision']['stop_loss']
                }
            except Exception as e:
                errors[symbol] = str(e)
                logger.error(f"分析 {symbol} 失败: {e}")
        
        if results:
            return AnalysisResponse(
                success=True,
                message=f"分析完成: {len(results)}个成功, {len(errors)}个失败",
                data={
                    "results": results,
                    "errors": errors
                }
            )
        else:
            raise HTTPException(status_code=500, detail=f"所有分析均失败: {errors}")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"服务器错误: {str(e)}")


@analysis_router.post("/analyze-common-technical", response_model=CommonTechnicalAnalysisResponse)
async def trigger_common_technical_analysis(request: CommonTechnicalAnalysisRequest):
    """
    触发通用技术分析接口（方案二）
    
    Args:
        symbol: 要分析的交易对
        user_message: 用户自定义问题
        additional_instructions: 额外分析要求
        
    Returns:
        通用技术分析结果（包含Markdown报告）
    """
    try:
        from trading_decision_system.utils.logger import setup_logger
        from datetime import datetime, timezone
        
        logger = setup_logger(
            name="common_technical_endpoint",
            log_level="INFO",
            log_file="./trading_decision_system/logs/api.log"
        )
        
        if not request.symbol:
            raise HTTPException(status_code=400, detail="交易对不能为空")
        
        logger.info(f"收到通用技术分析请求: symbol={request.symbol}")
        
        # 获取通用技术分析策略
        strategy = await get_strategy("common_technical")
        
        result = await strategy.execute(
            symbol=request.symbol,
            user_message=request.user_message,
            additional_instructions=request.additional_instructions
        )
        
        return CommonTechnicalAnalysisResponse(
            success=True,
            message="通用技术分析完成",
            symbol=result['symbol'],
            analysis_time=result['analysis_time'],
            markdown_report=result['markdown_report'],
            model_analyses=result['model_analyses']
        )
            
    except HTTPException:
        raise
    except Exception as e:
        from datetime import datetime, timezone
        
        return CommonTechnicalAnalysisResponse(
            success=False,
            message="通用技术分析失败",
            symbol=request.symbol,
            analysis_time=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
            error=str(e)
        )





# 注册路由
app.include_router(health_router)
app.include_router(analysis_router)



