"""
任务调度系统
定时执行分析任务
"""

import json
import time
import asyncio
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from ..utils.logger import LoggerMixin
from ..utils.config_loader import ConfigLoader

class TaskScheduler(LoggerMixin):
    """
    任务调度器
    定时执行交易分析任务
    """
    
    def __init__(self, config: ConfigLoader):
        super().__init__()
        self.config = config
        self.scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")
        self.jobs: Dict[str, Any] = {}
        self.is_running = False
        self.task_executor = None
    
    def start(self):
        """启动调度器"""
        try:
            self.scheduler.start()
            self.is_running = True
            self.logger.info("任务调度器已启动")
            
            # 加载定时任务
            self._load_scheduled_tasks()
            
        except Exception as e:
            self.logger.error(f"调度器启动失败: {e}")
            raise
    
    def stop(self):
        """停止调度器"""
        try:
            self.scheduler.shutdown()
            self.is_running = False
            self.logger.info("任务调度器已停止")
            
        except Exception as e:
            self.logger.error(f"调度器停止失败: {e}")
    
    def _load_scheduled_tasks(self):
        """加载配置中的定时任务"""
        schedule_config = self.config.get("analysis.schedule", [])
        
        for task_config in schedule_config:
            if not task_config.get("enabled", True):
                continue
            
            task_time = task_config.get("time", "")
            task_type = task_config.get("type", "strategic")
            
            try:
                trigger = self._parse_time_expression(task_time)
                
                if trigger:
                    job_id = f"{task_type}_task_{task_time}"
                    self.scheduler.add_job(
                        self._execute_task,
                        trigger=trigger,
                        args=[task_type],
                        id=job_id,
                        name=f"{task_type} analysis at {task_time}",
                        replace_existing=True
                    )
                    self.jobs[job_id] = {
                        "type": task_type,
                        "time": task_time,
                        "status": "active"
                    }
                    self.logger.info(f"已添加定时任务: {task_type} at {task_time}")
                    
            except Exception as e:
                self.logger.error(f"添加定时任务失败 {task_type} at {task_time}: {e}")
    
    def _parse_time_expression(self, time_expr: str) -> Optional[Any]:
        """
        解析时间表达式
        
        支持格式:
        - "HH:MM" (每天)
        - "*:MM" (每小时)
        - "HH:*" (每分钟)
        - "*/5:00" (每5分钟)
        - "HH:MM:SS" (精确到秒)
        
        Args:
            time_expr: 时间表达式
            
        Returns:
            APScheduler trigger
        """
        if not time_expr:
            return None
        
        parts = time_expr.split(":")
        
        if len(parts) == 2:
            hour, minute = parts
            
            if hour == "*" and minute == "*":
                # 每分钟
                return IntervalTrigger(minutes=1)
            
            elif hour == "*" or hour.startswith("*/"):
                # 每小时的第X分钟，或每N分钟
                try:
                    # 检查是否是 */N 格式
                    if hour.startswith("*/"):
                        # 每N分钟
                        interval = int(hour[2:])
                        return IntervalTrigger(minutes=interval)
                    
                    minute_int = int(minute)
                    return CronTrigger(minute=minute_int, second=0)
                except ValueError:
                    return None
                    
            elif minute == "*":
                # 每小时
                try:
                    hour_int = int(hour)
                    return CronTrigger(hour=hour_int, minute=0, second=0)
                except ValueError:
                    return None
                    
            else:
                # 每天的HH:MM
                try:
                    hour_int = int(hour)
                    minute_int = int(minute)
                    return CronTrigger(hour=hour_int, minute=minute_int, second=0)
                except ValueError:
                    return None
                    
        elif len(parts) == 3:
            # HH:MM:SS
            try:
                hour = int(parts[0]) if parts[0] != "*" else "*"
                minute = int(parts[1]) if parts[1] != "*" else "*"
                second = int(parts[2]) if parts[2] != "*" else "*"
                return CronTrigger(hour=hour, minute=minute, second=second)
            except ValueError:
                return None
                
        return None
    
    def add_interval_task(
        self,
        task_id: str,
        func: Callable,
        minutes: int,
        *args,
        **kwargs
    ):
        """
        添加间隔任务
        
        Args:
            task_id: 任务ID
            func: 任务函数
            minutes: 间隔分钟数
            args: 函数参数
            kwargs: 函数关键字参数
        """
        try:
            self.scheduler.add_job(
                func,
                trigger=IntervalTrigger(minutes=minutes),
                args=args,
                kwargs=kwargs,
                id=task_id,
                name=f"Interval task: {task_id}",
                replace_existing=True
            )
            self.jobs[task_id] = {
                "type": "interval",
                "interval_minutes": minutes,
                "status": "active"
            }
            self.logger.info(f"已添加间隔任务: {task_id} (每{minutes}分钟)")
            
        except Exception as e:
            self.logger.error(f"添加间隔任务失败 {task_id}: {e}")
    
    def add_cron_task(
        self,
        task_id: str,
        func: Callable,
        hour: Optional[int] = None,
        minute: Optional[int] = None,
        second: int = 0,
        *args,
        **kwargs
    ):
        """
        添加Cron任务
        
        Args:
            task_id: 任务ID
            func: 任务函数
            hour: 小时
            minute: 分钟
            second: 秒
            args: 函数参数
            kwargs: 函数关键字参数
        """
        try:
            self.scheduler.add_job(
                func,
                trigger=CronTrigger(hour=hour, minute=minute, second=second),
                args=args,
                kwargs=kwargs,
                id=task_id,
                name=f"Cron task: {task_id}",
                replace_existing=True
            )
            self.jobs[task_id] = {
                "type": "cron",
                "hour": hour,
                "minute": minute,
                "second": second,
                "status": "active"
            }
            self.logger.info(f"已添加Cron任务: {task_id} (hour={hour}, minute={minute}, second={second})")
            
        except Exception as e:
            self.logger.error(f"添加Cron任务失败 {task_id}: {e}")
    
    def remove_task(self, task_id: str):
        """
        移除任务
        
        Args:
            task_id: 任务ID
        """
        try:
            self.scheduler.remove_job(task_id)
            if task_id in self.jobs:
                del self.jobs[task_id]
            self.logger.info(f"已移除任务: {task_id}")
            
        except Exception as e:
            self.logger.error(f"移除任务失败 {task_id}: {e}")
    
    def pause_task(self, task_id: str):
        """
        暂停任务
        
        Args:
            task_id: 任务ID
        """
        try:
            self.scheduler.pause_job(task_id)
            if task_id in self.jobs:
                self.jobs[task_id]["status"] = "paused"
            self.logger.info(f"已暂停任务: {task_id}")
            
        except Exception as e:
            self.logger.error(f"暂停任务失败 {task_id}: {e}")
    
    def resume_task(self, task_id: str):
        """
        恢复任务
        
        Args:
            task_id: 任务ID
        """
        try:
            self.scheduler.resume_job(task_id)
            if task_id in self.jobs:
                self.jobs[task_id]["status"] = "active"
            self.logger.info(f"已恢复任务: {task_id}")
            
        except Exception as e:
            self.logger.error(f"恢复任务失败 {task_id}: {e}")
    
    def get_jobs(self) -> Dict[str, Any]:
        """
        获取所有任务
        
        Returns:
            任务字典
        """
        return self.jobs
    
    def set_task_executor(self, executor: Callable):
        """
        设置任务执行器
        
        Args:
            executor: 任务执行函数
        """
        self.task_executor = executor
        self.logger.info("任务执行器已设置")
    
    async def _execute_task(self, task_type: str):
        """
        执行任务
        
        Args:
            task_type: 任务类型
        """
        self.logger.info(f"开始执行任务: {task_type} at {datetime.now()}")
        
        if self.task_executor:
            try:
                await self.task_executor(task_type)
            except Exception as e:
                self.logger.error(f"任务执行失败 {task_type}: {e}")
        else:
            self.logger.warning(f"任务执行器未设置，跳过任务: {task_type}")
        
        try:
            # 这里会调用实际的分析逻辑
            # 暂时记录日志，后续会集成完整的分析流程
            
            self.logger.info(f"任务 {task_type} 执行成功")
            
        except Exception as e:
            self.logger.error(f"任务 {task_type} 执行失败: {e}")
    
    def run_now(self, task_type: str):
        """
        立即执行任务
        
        Args:
            task_type: 任务类型
        """
        self.logger.info(f"立即执行任务: {task_type}")
        
        # 创建异步任务并立即执行
        if self.is_running:
            asyncio.create_task(self._execute_task(task_type))
        else:
            # 如果调度器未启动，直接执行
            asyncio.run(self._execute_task(task_type))
    
    def schedule_immediate_analysis(
        self,
        symbol: str,
        analysis_type: str = "strategic"
    ):
        """
        调度立即分析
        
        Args:
            symbol: 交易对
            analysis_type: 分析类型
        """
        task_id = f"immediate_{analysis_type}_{symbol}_{int(time.time())}"
        
        async def immediate_task():
            await self._execute_task(f"{analysis_type}_{symbol}")
        
        if self.is_running:
            asyncio.create_task(immediate_task())
        else:
            asyncio.run(immediate_task())
        
        self.logger.info(f"已调度立即分析: {symbol} ({analysis_type})")
