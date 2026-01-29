"""
基础分析策略
实现所有分析策略的公共方法
"""

import logging
from typing import Dict, Optional
from abc import ABC, abstractmethod

from trading_decision_system.utils.config_loader import ConfigLoader
from trading_decision_system.services.analysis_strategy.analysis_strategy import AnalysisStrategy
from trading_decision_system.data.data_fetcher import DataFetcher
from trading_decision_system.data.indicator_calculator import IndicatorCalculator
from trading_decision_system.data.account_manager import AccountManager
from trading_decision_system.analysis.llm_analyzer import LLMAnalyzer


class BaseAnalysisStrategy(AnalysisStrategy):
    """
    基础分析策略
    实现所有分析策略的公共方法
    """
    
    def __init__(self, config=None):
        """
        初始化基础分析策略
        
        Args:
            config: 配置对象
        """
        self.config = config or ConfigLoader()
        self.logger = self._setup_logger()
        self._init_modules()
    
    def _setup_logger(self) -> logging.Logger:
        """设置日志系统"""
        logger = logging.getLogger(self.__class__.__name__)
        logger.setLevel(logging.INFO)
        return logger
    
    def _init_modules(self):
        """初始化各个模块"""
        self.logger.info("初始化数据采集模块...")
        self.data_fetcher = DataFetcher(self.config)
        
        self.logger.info("初始化指标计算模块...")
        self.indicator_calculator = IndicatorCalculator()
        
        self.logger.info("初始化账户管理模块...")
        self.account_manager = AccountManager(self.data_fetcher.client)
        
        self.logger.info("初始化LLM分析模块...")
        self.llm_analyzer = LLMAnalyzer(self.config)
    
    async def _fetch_market_data(self, symbol: str) -> dict:
        """
        获取市场数据
        
        Args:
            symbol: 交易对
            
        Returns:
            市场数据字典
        """
        try:
            klines_1h = self.data_fetcher.get_klines(symbol, "1h", limit=100)
            klines_4h = self.data_fetcher.get_klines(symbol, "4h", limit=50)
            klines_1d = self.data_fetcher.get_klines(symbol, "1d", limit=30)
            
            ticker = self.data_fetcher.get_symbol_ticker(symbol)
            ticker_24h = self.data_fetcher.get_24h_ticker(symbol)
            
            # 获取佣金费率
            commission_rates = self.data_fetcher.get_commission_rate(symbol)
            
            return {
                'klines_1h': klines_1h,
                'klines_4h': klines_4h,
                'klines_1d': klines_1d,
                'ticker': ticker,
                'ticker_24h': ticker_24h,
                'commission_rates': commission_rates
            }
            
        except Exception as e:
            self.logger.error(f"市场数据获取失败: {e}")
            raise
    
    async def _calculate_indicators(self, market_data: dict) -> dict:
        """
        计算技术指标
        
        Args:
            market_data: 市场数据
            
        Returns:
            技术指标字典
        """
        try:
            indicators_1h = self.indicator_calculator.calculate_all_indicators(market_data['klines_1h'])
            indicators_4h = self.indicator_calculator.calculate_all_indicators(market_data['klines_4h'])
            indicators_1d = self.indicator_calculator.calculate_all_indicators(market_data['klines_1d'])
            
            return {
                '1h': indicators_1h,
                '4h': indicators_4h,
                '1d': indicators_1d
            }
            
        except Exception as e:
            self.logger.error(f"技术指标计算失败: {e}")
            raise
    
    async def _get_account_info(self, symbol: str) -> dict:
        """
        获取账户信息
        
        Args:
            symbol: 交易对
            
        Returns:
            账户信息字典
        """
        try:
            account_summary = self.account_manager.get_account_summary(symbol)
            return account_summary
            
        except Exception as e:
            self.logger.error(f"账户信息获取失败: {e}")
            raise
    
    @classmethod
    def get_strategy_name(cls) -> str:
        """
        获取策略名称
        
        Returns:
            策略名称
        """
        # 默认返回类名的小写形式，提取策略类型部分
        class_name = cls.__name__
        
        # 去除 Strategy 后缀
        if class_name.endswith("Strategy"):
            class_name = class_name[:-8]
        
        # 提取策略类型
        # 对于 StandardAnalysisStrategy，提取为 standard
        # 对于 RealTimeAnalysisStrategy，提取为 realtime
        if class_name == "StandardAnalysis":
            return "standard"
        elif class_name == "RealTimeAnalysis":
            return "realtime"
        else:
            # 默认返回类名的小写形式
            return class_name.lower()
