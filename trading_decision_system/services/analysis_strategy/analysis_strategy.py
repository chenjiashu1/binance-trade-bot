"""
分析策略接口
定义不同分析策略的统一接口
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional


class AnalysisStrategy(ABC):
    """
    分析策略基类
    """
    
    @abstractmethod
    async def execute(self, *args, **kwargs) -> Dict:
        """
        执行分析
        
        Returns:
            分析结果
        """
        pass


class AnalysisStrategyFactory:
    """
    分析策略工厂
    """
    
    # 已注册的策略类
    _registered_strategies = {}
    
    @classmethod
    def register_strategy(cls, strategy_class):
        """
        注册策略类
        
        Args:
            strategy_class: 策略类
        """
        strategy_name = strategy_class.get_strategy_name()
        cls._registered_strategies[strategy_name] = strategy_class
        
    @classmethod
    def get_strategy(cls, strategy_type: str, config=None):
        """
        获取分析策略实例
        
        Args:
            strategy_type: 策略类型
            config: 配置对象
            
        Returns:
            分析策略实例
        """
        # 确保策略已注册
        if not cls._registered_strategies:
            cls._discover_strategies()
        
        # 获取策略类
        strategy_class = cls._registered_strategies.get(strategy_type)
        if not strategy_class:
            raise ValueError(f"Unknown strategy type: {strategy_type}")
        
        # 创建并返回策略实例
        return strategy_class(config)
    
    @classmethod
    def _discover_strategies(cls):
        """
        自动发现策略类
        """
        import importlib
        import pkgutil
        from pathlib import Path
        
        # 获取 services 目录
        services_dir = Path(__file__).parent
        
        # 遍历 services 目录下的所有模块
        for _, module_name, is_pkg in pkgutil.iter_modules([str(services_dir)]):
            if is_pkg:
                continue
            
            # 跳过非策略模块
            if module_name in ['analysis_strategy', 'base_analysis_strategy']:
                continue
            
            # 导入模块
            try:
                module = importlib.import_module(f'.{module_name}', package='trading_decision_system.services.analysis_strategy')
                
                # 遍历模块中的所有类
                for name, obj in module.__dict__.items():
                    if (
                        isinstance(obj, type) and 
                        hasattr(obj, 'get_strategy_name') and 
                        obj != BaseAnalysisStrategy
                    ):
                        # 注册策略类
                        cls.register_strategy(obj)
                        
            except Exception as e:
                # 忽略导入错误
                pass

# 导入 BaseAnalysisStrategy
from .base_analysis_strategy import BaseAnalysisStrategy

# 初始化时自动发现策略
AnalysisStrategyFactory._discover_strategies()
