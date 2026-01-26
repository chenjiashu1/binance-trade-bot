"""
配置加载模块
加载和管理系统配置
"""

import os
import yaml
from typing import Dict, Any, Optional
from pathlib import Path

class ConfigLoader:
    """
    配置加载器
    支持环境变量替换和配置合并
    """
    
    def __init__(self, config_path: str = "./trading_decision_system/configs/config.yaml"):
        self.config_path = Path(config_path)
        self.config: Dict[str, Any] = {}
        self._load_config()
    
    def _load_config(self):
        """加载配置文件"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {self.config_path}")
        
        with open(self.config_path, "r", encoding="utf-8") as f:
            config_content = f.read()
        
        # 替换环境变量
        config_content = self._replace_env_vars(config_content)
        
        self.config = yaml.safe_load(config_content)
    
    def _replace_env_vars(self, content: str) -> str:
        """替换配置中的环境变量"""
        for key, value in os.environ.items():
            placeholder = f"${{{key}}}"
            content = content.replace(placeholder, value)
        return content
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值
        
        Args:
            key: 配置键，支持点分隔 (如 "exchange.api_key")
            default: 默认值
            
        Returns:
            配置值
        """
        keys = key.split(".")
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def get_exchange_config(self) -> Dict[str, Any]:
        """获取交易所配置"""
        return self.get("exchange", {})
    
    def get_model_config(self, model_name: str) -> Dict[str, Any]:
        """获取指定模型的配置"""
        models = self.get("models", {})
        return models.get(model_name, {})
    
    def get_all_enabled_models(self) -> Dict[str, Dict[str, Any]]:
        """获取所有启用的模型"""
        models = self.get("models", {})
        return {name: config for name, config in models.items() if config.get("enabled", False)}
    
    def get_analysis_config(self) -> Dict[str, Any]:
        """获取分析配置"""
        return self.get("analysis", {})
    
    def get_output_config(self) -> Dict[str, Any]:
        """获取输出配置"""
        return self.get("output", {})
    
    def get_logging_config(self) -> Dict[str, Any]:
        """获取日志配置"""
        return self.get("logging", {})
    
    def reload(self):
        """重新加载配置"""
        self._load_config()
    
    def __getitem__(self, key: str) -> Any:
        return self.get(key)
    
    def __contains__(self, key: str) -> bool:
        keys = key.split(".")
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return False
        
        return True
