"""
自定义异常类
"""

class TradingSystemError(Exception):
    """交易系统基础异常"""
    
    def __init__(self, message: str, error_code: str = "TS_ERROR"):
        self.message = message
        self.error_code = error_code
        super().__init__(f"[{error_code}] {message}")


class DataFetchError(TradingSystemError):
    """数据获取异常"""
    
    def __init__(self, message: str, source: str = "unknown"):
        self.source = source
        super().__init__(f"[{source}] {message}", "DATA_ERROR")


class AnalysisError(TradingSystemError):
    """分析异常"""
    
    def __init__(self, message: str, model: str = "unknown"):
        self.model = model
        super().__init__(f"[{model}] {message}", "ANALYSIS_ERROR")


class DecisionError(TradingSystemError):
    """决策异常"""
    
    def __init__(self, message: str, stage: str = "unknown"):
        self.stage = stage
        super().__init__(f"[{stage}] {message}", "DECISION_ERROR")


class RiskControlError(TradingSystemError):
    """风险控制异常"""
    
    def __init__(self, message: str, risk_type: str = "unknown"):
        self.risk_type = risk_type
        super().__init__(f"[{risk_type}] {message}", "RISK_ERROR")


class ConfigurationError(TradingSystemError):
    """配置异常"""
    
    def __init__(self, message: str, config_key: str = "unknown"):
        self.config_key = config_key
        super().__init__(f"[{config_key}] {message}", "CONFIG_ERROR")
