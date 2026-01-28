"""
LLM分析器模块
调用LLM模型进行交易分析
"""

import json
from math import log
import time
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from venv import logger
from openai import OpenAI, AsyncOpenAI
from openai import APIError, APIConnectionError, RateLimitError

from ..utils.logger import LoggerMixin
from ..utils.exceptions import AnalysisError
from ..utils.config_loader import ConfigLoader
from .prompt_templates import PromptTemplates

class LLMAnalyzer(LoggerMixin):
    """
    LLM分析器
    调用多个LLM模型进行交易分析
    """
    
    def __init__(self, config: ConfigLoader):
        super().__init__()
        self.config = config
        self.prompt_templates = PromptTemplates()
        self.clients: Dict[str, OpenAI] = {}
        self.async_clients: Dict[str, AsyncOpenAI] = {}
        self._init_clients()
    
    def __del__(self):
        """析构函数 - 确保资源释放"""
        self.close()
    
    def _init_clients(self):
        """初始化LLM客户端"""
        models_config = self.config.get("models", {})
        
        if not models_config:
            self.logger.warning("未找到模型配置")
            return
        
        for model_name, model_config in models_config.items():
            if not model_config.get("enabled", False):
                self.logger.debug(f"模型 {model_name} 已禁用")
                continue
            
            try:
                api_key = model_config.get("api_key", "")
                base_url = model_config.get("base_url", "")
                
                if not api_key:
                    self.logger.warning(f"跳过 {model_name}: 未配置API密钥")
                    continue
                
                # 创建同步客户端
                client = OpenAI(
                    api_key=api_key,
                    base_url=base_url if base_url else None
                )
                self.clients[model_name] = client
                
                # 创建异步客户端
                async_client = AsyncOpenAI(
                    api_key=api_key,
                    base_url=base_url if base_url else None
                )
                self.async_clients[model_name] = async_client
                
                self.logger.info(f"{model_name} 客户端初始化成功")
                
            except Exception as e:
                self.logger.error(f"{model_name} 客户端初始化失败: {e}", exc_info=True)
    
    def analyze(
        self,
        model_name: str,
        role: str,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        同步调用LLM进行分析
        
        Args:
            model_name: 模型名称
            role: 分析角色 (strategist/technical/risk)
            data: 输入数据
            
        Returns:
            分析结果
        """
        try:
            if model_name not in self.clients:
                raise AnalysisError(f"模型未初始化: {model_name}", model=model_name)
            
            # 获取Prompt
            prompt = self._get_prompt(role, data)
            
            # 获取模型配置
            model_config = self.config.get_model_config(model_name)
            model_id = model_config.get("model_name", "deepseek-coder")
            
            # 打印Prompt日志
            self.logger.info(f"\n" + "="*80)
            self.logger.info(f"LLM调用信息: {model_name} ({model_id}) - {role}")
            self.logger.info("="*80)
            self.logger.info(f"Prompt内容:\n{prompt}")
            self.logger.info("="*80 + "\n")
            
            # 调用LLM
            self.logger.debug(f"调用 {model_name} ({model_id}) 进行 {role} 分析...")
            
            start_time = time.time()
            
            # 根据角色决定输出格式
            if role == "technical":
                # technical角色返回Markdown格式
                response = self.clients[model_name].chat.completions.create(
                    model=model_id,
                    messages=[
                        {"role": "system", "content": "你是专业的数字货币交易分析师，输出详细的Markdown格式技术分析报告。"},
                        {"role": "user", "content": prompt}
                    ],
                    extra_body={"enable_thinking": True},
                    temperature=0.3,
                    max_tokens=4000  # 增加token限制以容纳详细的Markdown报告
                )
                
                result_content = response.choices[0].message.content
                
                # 计算耗时
                elapsed_time = time.time() - start_time
                self.logger.info(f"{model_name} 分析完成，耗时: {elapsed_time:.2f}秒")
                
                # 返回Markdown格式的结果
                result = {
                    "analysis": result_content,
                    "model_name": model_name,
                    "role": role,
                    "analysis_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "response_time_seconds": round(elapsed_time, 2),
                    "format": "markdown"
                }
            else:
                # 其他角色返回JSON格式
                response = self.clients[model_name].chat.completions.create(
                    model=model_id,
                    messages=[
                        {"role": "system", "content": "你是专业的数字货币交易分析师，只输出JSON格式的分析结果。"},
                        {"role": "user", "content": prompt}
                    ],
                    extra_body={"enable_thinking": True},
                    temperature=0.3,
                    max_tokens=2000,
                    response_format={"type": "json_object"}
                )
                
                result_content = response.choices[0].message.content
                result = self.prompt_templates.validate_json_output(result_content)
                
                if result is None:
                    raise AnalysisError(f"{model_name} 返回无效JSON", model=model_name)
                
                # 计算耗时
                elapsed_time = time.time() - start_time
                self.logger.info(f"{model_name} 分析完成，耗时: {elapsed_time:.2f}秒")
                
                # 添加元数据
                result["model_name"] = model_name
                result["role"] = role
                result["analysis_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                result["response_time_seconds"] = round(elapsed_time, 2)
                result["format"] = "json"
            
            return result
            
        except APIError as e:
            raise AnalysisError(f"API错误: {e}", model=model_name)
        except APIConnectionError as e:
            raise AnalysisError(f"连接错误: {e}", model=model_name)
        except RateLimitError as e:
            raise AnalysisError(f"限流错误: {e}", model=model_name)
        except Exception as e:
            raise AnalysisError(f"分析失败: {e}", model=model_name)
    
    async def async_analyze(
        self,
        model_name: str,
        role: str,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        异步调用LLM进行分析
        
        Args:
            model_name: 模型名称
            role: 分析角色
            data: 输入数据
            
        Returns:
            分析结果
        """
        try:
            if model_name not in self.async_clients:
                raise AnalysisError(f"异步客户端未初始化: {model_name}", model=model_name)
            
            prompt = self._get_prompt(role, data)
            model_config = self.config.get_model_config(model_name)
            model_id = model_config.get("model_name", "deepseek-coder")
            
            self.logger.info(f"\n" + "="*80)
            self.logger.info(f"LLM调用信息: {model_name} ({model_id}) - {role}")
            self.logger.info("="*80)
            self.logger.info(f"Prompt内容:\n{prompt}")
            self.logger.info("="*80 + "\n")
            
            self.logger.debug(f"异步调用 {model_name} ({model_id}) 进行 {role} 分析...")
            
            start_time = time.time()
            
            # 根据角色决定输出格式
            if role == "technical":
                # technical角色返回Markdown格式
                response = await self.async_clients[model_name].chat.completions.create(
                    model=model_id,
                    messages=[
                        {"role": "system", "content": "你是专业的数字货币交易分析师，输出详细的Markdown格式技术分析报告。"},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    extra_body={"enable_thinking": True},
                    max_tokens=4000  # 增加token限制以容纳详细的Markdown报告
                )
                
                result_content = response.choices[0].message.content
                
                # 计算耗时
                elapsed_time = time.time() - start_time
                self.logger.info(f"{model_name} 异步分析完成，耗时: {elapsed_time:.2f}秒")
                
                # 返回Markdown格式的结果
                result = {
                    "analysis": result_content,
                    "model_name": model_name,
                    "role": role,
                    "analysis_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "response_time_seconds": round(elapsed_time, 2),
                    "format": "markdown"
                }
            else:
                # 其他角色返回JSON格式
                response = await self.async_clients[model_name].chat.completions.create(
                    model=model_id,
                    messages=[
                        {"role": "system", "content": "你是专业的数字货币交易分析师，只输出JSON格式的分析结果。"},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    extra_body={"enable_thinking": True},
                    max_tokens=2000,
                    response_format={"type": "json_object"}
                )
                
                result_content = response.choices[0].message.content
                result = self.prompt_templates.validate_json_output(result_content)
                
                if result is None:
                    raise AnalysisError(f"{model_name} 返回无效JSON", model=model_name)
                
                # 计算耗时
                elapsed_time = time.time() - start_time
                self.logger.info(f"{model_name} 异步分析完成，耗时: {elapsed_time:.2f}秒")
                
                result["model_name"] = model_name
                result["role"] = role
                result["analysis_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                result["response_time_seconds"] = round(elapsed_time, 2)
                result["format"] = "json"
            
            return result
            
        except Exception as e:
            self.logger.error(f"异步分析失败: {e}", exc_info=True)
            raise AnalysisError(f"异步分析失败: {e}", model=model_name)
    
    async def async_analyze_all(
        self,
        role: str,
        data: Dict[str, Any]
    ) -> Dict[str, Dict[str, Any]]:
        """
        异步调用所有启用的模型进行分析
        
        Args:
            role: 分析角色
            data: 输入数据
            
        Returns:
            所有模型的分析结果
        """
        enabled_models = self.config.get_all_enabled_models()
        
        if not enabled_models:
            raise AnalysisError("没有启用的模型", model="all")
        
        # 过滤掉不可用的模型
        available_models = [
            model_name for model_name in enabled_models.keys()
            if model_name in self.async_clients
        ]
        
        if not available_models:
            raise AnalysisError("没有可用的模型客户端", model="all")
        
        self.logger.info(f"并行分析模型: {available_models}")
        
        tasks = []
        for model_name in available_models:
            task = self.async_analyze(model_name, role, data)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        model_results = {}
        failed_count = 0
        
        for model_name, result in zip(available_models, results):
            if isinstance(result, Exception):
                self.logger.error(f"{model_name} 分析失败: {result}", exc_info=True)
                model_results[model_name] = {
                    "error": str(result),
                    "success": False,
                    "error_type": type(result).__name__
                }
                failed_count += 1
            else:
                model_results[model_name] = result
        
        self.logger.info(f"并行分析完成: {len(available_models)-failed_count}/{len(available_models)} 个模型成功")
        
        return model_results
    
    def _get_prompt(self, role: str, data: Dict[str, Any]) -> str:
        """
        获取对应角色的Prompt
        
        Args:
            role: 分析角色
            data: 输入数据
            
        Returns:
            Prompt字符串
        """
        if role == "strategist":
            return self.prompt_templates.get_strategist_prompt(data)
        elif role == "technical":
            return self.prompt_templates.get_technical_prompt(data)
        elif role == "risk":
            return self.prompt_templates.get_risk_prompt(data)
        else:
            raise AnalysisError(f"未知角色: {role}", model="unknown")
    
    def get_model_weights(self) -> Dict[str, float]:
        """
        获取模型权重配置
        
        Returns:
            模型权重字典
        """
        enabled_models = self.config.get_all_enabled_models()
        weights = {}
        
        for model_name, config in enabled_models.items():
            weights[model_name] = config.get("weight", 0.33)
        
        # 归一化权重
        total_weight = sum(weights.values())
        if total_weight > 0:
            for model_name in weights:
                weights[model_name] /= total_weight
        
        return weights
    
    def is_available(self, model_name: str) -> bool:
        """
        检查模型是否可用
        
        Args:
            model_name: 模型名称
            
        Returns:
            是否可用
        """
        return model_name in self.clients
    
    def get_available_models(self) -> List[str]:
        """
        获取可用模型列表
        
        Returns:
            可用模型名称列表
        """
        return list(self.clients.keys())
    
    def close(self):
        """关闭所有客户端连接（仅同步客户端）"""
        if not self.clients:
            return
        
        closed_count = 0
        for model_name, client in list(self.clients.items()):
            try:
                client.close()
                self.logger.debug(f"{model_name} 客户端已关闭")
                closed_count += 1
            except Exception as e:
                self.logger.error(f"关闭 {model_name} 客户端失败: {e}", exc_info=True)
            finally:
                if model_name in self.clients:
                    del self.clients[model_name]
        
        self.logger.info(f"已关闭 {closed_count} 个同步客户端连接")
    
    async def async_close(self):
        """异步关闭所有客户端连接"""
        if not self.async_clients:
            return
        
        for model_name, client in list(self.async_clients.items()):
            try:
                await client.close()
                self.logger.debug(f"{model_name} 异步客户端已关闭")
            except Exception as e:
                self.logger.error(f"关闭 {model_name} 异步客户端失败: {e}", exc_info=True)
            finally:
                del self.async_clients[model_name]
        
        # 同步关闭剩余的同步客户端
        self.close()
        
        self.logger.info(f"已关闭所有客户端连接")
