"""
日志模块
提供系统日志功能
"""

import logging
import os
import traceback
from logging.handlers import RotatingFileHandler
from typing import Optional, Dict, Any
from pathlib import Path

def get_log_dir() -> str:
    """
    获取日志目录路径
    
    Returns:
        日志目录路径
    """
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")

def setup_logger(
    name: str = "trading_decision_system",
    log_level: str = "INFO",
    log_format: str = "%(asctime)s.%(msecs)03d - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
    log_file: Optional[str] = None,
    max_file_size: int = 10 * 1024 * 1024,
    backup_count: int = 5
) -> logging.Logger:
    """
    设置日志记录器
    
    Args:
        name: 日志记录器名称
        log_level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: 日志格式
        log_file: 日志文件路径 (None 则使用默认路径)
        max_file_size: 日志文件最大大小 (字节)
        backup_count: 备份文件数量
    
    Returns:
        配置好的日志记录器
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # 避免重复添加处理器
    if logger.handlers:
        return logger
    
    # 创建格式化器
    formatter = logging.Formatter(log_format, datefmt="%Y-%m-%d %H:%M:%S")
    
    # 添加控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 添加文件处理器
    if log_file is None:
        log_file = os.path.join(get_log_dir(), f"{name}.log")
    
    # 确保日志目录存在
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
    
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=max_file_size,
        backupCount=backup_count,
        encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger


def log_exceptions(func):
    """
    异常日志装饰器
    
    Args:
        func: 被装饰的函数
    
    Returns:
        装饰后的函数
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # 获取类实例的logger或创建默认logger
            logger = None
            if args and hasattr(args[0], 'logger'):
                logger = args[0].logger
            else:
                logger = setup_logger(func.__name__)
            
            logger.error(f"函数 {func.__name__} 执行失败: {e}")
            logger.error(f"异常堆栈: {traceback.format_exc()}")
            raise
    return wrapper


class LoggerMixin:
    """
    日志混合类
    为其他类提供日志功能
    """
    
    def __init__(self, logger_name: Optional[str] = None):
        self.logger = setup_logger(logger_name or self.__class__.__name__)
    
    def _log_with_context(self, level: int, message: str, **context: Dict[str, Any]):
        """
        带上下文的日志记录
        
        Args:
            level: 日志级别
            message: 日志消息
            **context: 上下文信息
        """
        if context:
            context_str = " | ".join([f"{k}={v}" for k, v in context.items()])
            full_message = f"{message} | {context_str}"
        else:
            full_message = message
        self.logger.log(level, full_message)
    
    def debug(self, message: str, **context: Dict[str, Any]):
        """
        记录调试级别的日志
        
        Args:
            message: 日志消息
            **context: 上下文信息
        """
        self._log_with_context(logging.DEBUG, message, **context)
    
    def info(self, message: str, **context: Dict[str, Any]):
        """
        记录信息级别的日志
        
        Args:
            message: 日志消息
            **context: 上下文信息
        """
        self._log_with_context(logging.INFO, message, **context)
    
    def warning(self, message: str, **context: Dict[str, Any]):
        """
        记录警告级别的日志
        
        Args:
            message: 日志消息
            **context: 上下文信息
        """
        self._log_with_context(logging.WARNING, message, **context)
    
    def error(self, message: str, **context: Dict[str, Any]):
        """
        记录错误级别的日志
        
        Args:
            message: 日志消息
            **context: 上下文信息
        """
        self._log_with_context(logging.ERROR, message, **context)
    
    def critical(self, message: str, **context: Dict[str, Any]):
        """
        记录严重错误级别的日志
        
        Args:
            message: 日志消息
            **context: 上下文信息
        """
        self._log_with_context(logging.CRITICAL, message, **context)
