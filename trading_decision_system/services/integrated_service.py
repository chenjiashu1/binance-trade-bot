"""
整合服务
同时运行定时任务和API接口
"""

import logging
import asyncio
import signal
from pathlib import Path

from trading_decision_system.utils.config_loader import ConfigLoader
from trading_decision_system.utils.logger import setup_logger
from trading_decision_system.services.analysis_strategy import AnalysisStrategyFactory


class IntegratedService:
    """
    整合服务
    同时运行定时任务和API接口
    """
    
    def __init__(self, config_path: str = "./trading_decision_system/configs/config.yaml"):
        self.logger = setup_logger(
            name="integrated_service_main",
            log_level="INFO",
            log_file="./trading_decision_system/logs/integrated_main.log"
        )
        
        self.logger.info("="*80)
        self.logger.info("交易决策系统 - 整合服务")
        self.logger.info("="*80)
        
        self.config = ConfigLoader(config_path)
        self.is_running = False
        self._shutdown_event = asyncio.Event()
        
        # 初始化策略
        self.logger.info("初始化分析策略...")
        self.standard_strategy = AnalysisStrategyFactory.get_strategy("standard", self.config)
        self.realtime_strategy = AnalysisStrategyFactory.get_strategy("realtime", self.config)
        
        # 初始化调度器
        self.logger.info("初始化任务调度器...")
        from trading_decision_system.scheduler.task_scheduler import TaskScheduler
        self.scheduler = TaskScheduler(self.config)
        self.scheduler.set_task_executor(self._execute_scheduled_task)
        
        self.logger.info("整合服务初始化完成")
    
    async def start(self, api_port: int = 8000):
        """启动整合服务"""
        self.logger.info("\n" + "="*80)
        self.logger.info("启动整合服务...")
        self.logger.info("="*80)
        
        try:
            # 启动调度器
            self.scheduler.start()
            
            # 注册信号处理器
            self._setup_signal_handlers()
            
            self.is_running = True
            
            self.logger.info("\n" + "="*80)
            self.logger.info("✅ 整合服务已启动")
            self.logger.info("="*80 + "\n")
            
            # 启动API服务
            import uvicorn
            
            config = uvicorn.Config(
                "trading_decision_system.routes.integrated_routes:app",
                host="0.0.0.0",
                port=api_port,
                log_level="info"
            )
            
            server = uvicorn.Server(config)
            
            # 运行API服务
            await server.serve()
            
        except Exception as e:
            self.logger.error("\n" + "="*80)
            self.logger.error("❌ 服务启动失败!")
            self.logger.error(f"错误信息: {e}")
            self.logger.error("="*80 + "\n")
            raise
    
    async def stop(self):
        """停止服务"""
        self.logger.info("\n" + "="*80)
        self.logger.info("正在停止服务...")
        self.logger.info("="*80)
        
        try:
            self.is_running = False
            
            # 停止调度器
            self.scheduler.stop()
            
            # 设置关闭事件
            self._shutdown_event.set()
            
            self.logger.info("\n" + "="*80)
            self.logger.info("✅ 服务已停止")
            self.logger.info("="*80 + "\n")
            
        except Exception as e:
            self.logger.error(f"停止服务失败: {e}")
            raise
    
    def _setup_signal_handlers(self):
        """设置信号处理器"""
        try:
            loop = asyncio.get_running_loop()
            
            # 尝试使用 add_signal_handler (Unix/Linux)
            for sig in [signal.SIGINT, signal.SIGTERM]:
                loop.add_signal_handler(
                    sig,
                    lambda s=sig: asyncio.create_task(self._handle_signal(s))
                )
            
            self.logger.info("信号处理器已注册 (Ctrl+C 停止服务)")
            
        except NotImplementedError:
            # Windows 系统不支持 add_signal_handler
            self.logger.warning("Windows 系统: 使用替代方式处理信号")
            
            async def check_shutdown():
                while not self._shutdown_event.is_set():
                    await asyncio.sleep(0.5)
            
            asyncio.create_task(check_shutdown())
            self.logger.info("Windows 模式: 按 Ctrl+C 停止服务")
    
    async def _handle_signal(self, sig):
        """处理系统信号"""
        self.logger.info(f"\n收到信号: {signal.Signals(sig).name}")
        await self.stop()
    
    async def _execute_scheduled_task(self, task_type: str):
        """
        执行定时任务
        """
        self.logger.info("\n" + "="*80)
        self.logger.info(f"开始执行定时任务: {task_type}")
        self.logger.info("="*80)
        
        try:
            # 获取配置的交易对
            symbols = self.config.get("exchange.symbols", [])
            
            if not symbols:
                self.logger.warning("未配置交易对，跳过任务")
                return
            
            # 根据任务类型确定分析角色
            role_map = {
                "strategic": "strategist",
                "technical": "technical",
                "risk": "risk_assessor"
            }
            
            role = role_map.get(task_type, "strategist")
            
            # 对每个交易对执行分析
            for symbol in symbols:
                self.logger.info(f"\n{'='*80}")
                self.logger.info(f"分析交易对: {symbol}")
                self.logger.info(f"{'='*80}")
                
                try:
                    await self.standard_strategy.execute(symbol, role)
                except Exception as e:
                    self.logger.error(f"分析 {symbol} 失败: {e}")
                    continue
            
            self.logger.info(f"\n{'='*80}")
            self.logger.info(f"✅ 定时任务完成: {task_type}")
            self.logger.info(f"{'='*80}\n")
            
        except Exception as e:
            self.logger.error(f"\n{'='*80}")
            self.logger.error(f"❌ 定时任务执行失败: {task_type}")
            self.logger.error(f"错误信息: {e}")
            self.logger.error(f"{'='*80}\n")
