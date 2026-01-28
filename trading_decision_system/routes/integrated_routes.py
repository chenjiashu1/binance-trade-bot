"""
交易决策系统 - 整合服务
同时运行定时任务和API接口
"""

import asyncio
import json
import logging
import signal
import sys
from pathlib import Path
from typing import Optional, List
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException, APIRouter
from pydantic import BaseModel
from enum import Enum

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from trading_decision_system.utils.logger import setup_logger
from trading_decision_system.utils.config_loader import ConfigLoader
from trading_decision_system.data.data_fetcher import DataFetcher
from trading_decision_system.data.indicator_calculator import IndicatorCalculator
from trading_decision_system.data.account_manager import AccountManager
from trading_decision_system.analysis.llm_analyzer import LLMAnalyzer
from trading_decision_system.decision.decision_aggregator import DecisionAggregator
from trading_decision_system.decision.risk_controller import RiskController
from trading_decision_system.scheduler.task_scheduler import TaskScheduler


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


class RealTimeAnalysisRequest(BaseModel):
    symbol: str
    period: Optional[str] = "1h"
    user_message: Optional[str] = ""
    additional_instructions: Optional[str] = ""


class RealTimeAnalysisResponse(BaseModel):
    success: bool
    message: str
    symbol: str
    period: str
    analysis_time: str
    markdown_report: Optional[str] = None
    model_analyses: Optional[dict] = None
    error: Optional[str] = None


class TradingDecisionEngine:
    """
    交易决策引擎
    封装所有分析逻辑
    """
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or self._get_default_config_path()
        self.logger = self._setup_logger()
        
        self.logger.info("初始化交易决策引擎...")
        self.config = ConfigLoader(self.config_path)
        self._init_modules()
        self.logger.info("交易决策引擎初始化完成")
    
    @staticmethod
    def _get_default_config_path() -> str:
        """获取默认配置文件路径"""
        return str(Path(__file__).parent.parent / "configs" / "config.yaml")
    
    def _setup_logger(self) -> logging.Logger:
        """设置日志系统"""
        log_dir = Path(__file__).parent.parent / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        
        return setup_logger(
            name="trading_decision_engine",
            log_level="INFO",
            log_file=str(log_dir / "integrated.log")
        )
    
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
        
        self.logger.info("初始化决策聚合模块...")
        self.decision_aggregator = DecisionAggregator(self.config)
        
        self.logger.info("初始化风险控制模块...")
        self.risk_controller = RiskController(self.config)
    
    async def analyze_symbol(
        self,
        symbol: str,
        role: str = "technical"
    ) -> dict:
        """
        分析单个交易对
        """
        self.logger.info(f"开始分析: {symbol} ({role})")
        
        try:
            # 步骤1: 获取市场数据
            market_data = await self._fetch_market_data(symbol)
            
            # 步骤2: 计算技术指标
            indicators = await self._calculate_indicators(market_data)
            
            # 步骤3: 获取账户信息
            account_info = await self._get_account_info(symbol)
            
            # 步骤4: 准备LLM输入数据
            llm_input = self._prepare_llm_input(
                symbol,
                market_data['ticker'],
                market_data['ticker_24h'],
                indicators['1h'],
                indicators['4h'],
                indicators['1d'],
                account_info
            )
            
            # 步骤5: 调用LLM分析
            model_results = await self._run_llm_analysis(role, llm_input)
            
            # 步骤6: 聚合决策
            final_decision = await self._aggregate_decisions(model_results, account_info)
            
            # 步骤7: 风险评估
            risk_report = await self._evaluate_risk(
                symbol,
                final_decision,
                account_info,
                market_data['klines_1h'],
                market_data['ticker_24h']
            )
            
            # 步骤8: 生成最终报告
            final_report = self._generate_final_report(
                symbol,
                role,
                market_data,
                indicators,
                account_info,
                model_results,
                final_decision,
                risk_report
            )
            
            # 步骤9: 保存报告
            self._save_report(final_report)
            
            self.logger.info(f"分析完成: {symbol}")
            
            return final_report
            
        except Exception as e:
            self.logger.error(f"分析失败 {symbol}: {e}")
            raise
    
    async def _fetch_market_data(self, symbol: str) -> dict:
        """获取市场数据"""
        try:
            klines_1h = self.data_fetcher.get_klines(symbol, "1h", limit=100)
            klines_4h = self.data_fetcher.get_klines(symbol, "4h", limit=50)
            klines_1d = self.data_fetcher.get_klines(symbol, "1d", limit=30)
            
            ticker = self.data_fetcher.get_symbol_ticker(symbol)
            ticker_24h = self.data_fetcher.get_24h_ticker(symbol)
            
            return {
                'klines_1h': klines_1h,
                'klines_4h': klines_4h,
                'klines_1d': klines_1d,
                'ticker': ticker,
                'ticker_24h': ticker_24h
            }
            
        except Exception as e:
            self.logger.error(f"市场数据获取失败: {e}")
            raise
    
    async def _calculate_indicators(self, market_data: dict) -> dict:
        """计算技术指标"""
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
        """获取账户信息"""
        try:
            account_summary = self.account_manager.get_account_summary(symbol)
            return account_summary
            
        except Exception as e:
            self.logger.error(f"账户信息获取失败: {e}")
            raise
    
    async def _run_llm_analysis(self, role: str, llm_input: dict) -> dict:
        """运行LLM分析"""
        try:
            model_results = await self.llm_analyzer.async_analyze_all(role, llm_input)
            return model_results
            
        except Exception as e:
            self.logger.error(f"LLM分析失败: {e}")
            raise
    
    async def _aggregate_decisions(self, model_results: dict, account_info: dict) -> dict:
        """聚合决策"""
        try:
            weights = self.llm_analyzer.get_model_weights()
            self.decision_aggregator.set_model_weights(weights)
            
            final_decision = self.decision_aggregator.aggregate_decisions(
                model_results,
                account_info
            )
            
            return final_decision
            
        except Exception as e:
            self.logger.error(f"决策聚合失败: {e}")
            raise
    
    async def _evaluate_risk(
        self,
        symbol: str,
        final_decision: dict,
        account_info: dict,
        klines_1h: dict,
        ticker_24h: dict
    ) -> dict:
        """评估风险"""
        try:
            trade_info = {
                "symbol": symbol,
                "position_size": final_decision['final_decision']['recommended_position_size_percent'],
                "entry_price": final_decision['final_decision']['entry_price'],
                "stop_loss": final_decision['final_decision']['stop_loss'],
                "price_change_24h": ticker_24h['price_change_percent']
            }
            
            risk_report = self.risk_controller.generate_risk_report(
                trade_info,
                account_info,
                klines_1h["close"].tolist() if not klines_1h.empty else []
            )
            
            return risk_report
            
        except Exception as e:
            self.logger.error(f"风险评估失败: {e}")
            raise
    
    def _prepare_llm_input(
        self,
        symbol: str,
        ticker: dict,
        ticker_24h: dict,
        indicators_1h: dict,
        indicators_4h: dict,
        indicators_1d: dict,
        account_summary: dict
    ) -> dict:
        """准备LLM输入数据"""
        return {
            "symbol": symbol,
            "current_price": ticker['price'],
            "price_change_24h": ticker_24h['price_change_percent'],
            
            # 1小时数据
            "trend_1h": indicators_1h['trend']['trend'],
            "trend_strength_1h": indicators_1h['trend']['strength'],
            "rsi_1h": indicators_1h['rsi']['value'],
            "rsi_status_1h": indicators_1h['rsi']['status'],
            "macd_1h": indicators_1h['macd']['macd'],
            "signal_1h": indicators_1h['macd']['signal'],
            "histogram_1h": indicators_1h['macd']['histogram'],
            "ma20_1h": indicators_1h['ma']['ma20'],
            "ma50_1h": indicators_1h['ma']['ma50'],
            "bb_upper_1h": indicators_1h['bollinger']['upper'],
            "bb_middle_1h": indicators_1h['bollinger']['middle'],
            "bb_lower_1h": indicators_1h['bollinger']['lower'],
            
            # 4小时数据
            "trend_4h": indicators_4h['trend']['trend'],
            "trend_strength_4h": indicators_4h['trend']['strength'],
            "rsi_4h": indicators_4h['rsi']['value'],
            "rsi_status_4h": indicators_4h['rsi']['status'],
            "macd_4h": indicators_4h['macd']['macd'],
            "signal_4h": indicators_4h['macd']['signal'],
            "histogram_4h": indicators_4h['macd']['histogram'],
            "ma20_4h": indicators_4h['ma']['ma20'],
            "ma50_4h": indicators_4h['ma']['ma50'],
            "ma200_4h": indicators_4h['ma'].get('ma200', 0),
            "bb_upper_4h": indicators_4h['bollinger']['upper'],
            "bb_middle_4h": indicators_4h['bollinger']['middle'],
            "bb_lower_4h": indicators_4h['bollinger']['lower'],
            
            # 日线数据
            "trend_1d": indicators_1d['trend']['trend'],
            "trend_strength_1d": indicators_1d['trend']['strength'],
            "rsi_1d": indicators_1d['rsi']['value'],
            "rsi_status_1d": indicators_1d['rsi']['status'],
            "macd_1d": indicators_1d['macd']['macd'],
            "signal_1d": indicators_1d['macd']['signal'],
            "histogram_1d": indicators_1d['macd']['histogram'],
            "ma20_1d": indicators_1d['ma']['ma20'],
            "ma50_1d": indicators_1d['ma']['ma50'],
            "ma200_1d": indicators_1d['ma'].get('ma200', 0),
            "bb_upper_1d": indicators_1d['bollinger']['upper'],
            "bb_middle_1d": indicators_1d['bollinger']['middle'],
            "bb_lower_1d": indicators_1d['bollinger']['lower'],
            
            # 账户信息
            "total_assets": account_summary['total_assets_usdt'],
            "usdt_balance": account_summary['balances'].get('USDT', 0),
            "current_positions": len(account_summary['balances']),
            "win_rate": account_summary['trade_statistics'].get('win_rate', 0),
            "total_trades": account_summary['trade_statistics'].get('total_trades', 0)
        }
    
    def _generate_final_report(
        self,
        symbol: str,
        role: str,
        market_data: dict,
        indicators: dict,
        account_info: dict,
        model_results: dict,
        final_decision: dict,
        risk_report: dict
    ) -> dict:
        """生成最终报告"""
        from datetime import datetime
        
        final_report = {
            "analysis_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "symbol": symbol,
            "analysis_type": role,
            "market_data": {
                "current_price": market_data['ticker']['price'],
                "price_change_24h": market_data['ticker_24h']['price_change_percent'],
                "indicators_1h": indicators['1h'],
                "indicators_4h": indicators['4h'],
                "indicators_1d": indicators['1d']
            },
            "account_info": account_info,
            "model_analyses": model_results,
            "final_decision": final_decision,
            "risk_assessment": risk_report
        }
        
        return final_report
    
    def _save_report(self, report: dict) -> bool:
        """
        保存分析报告
        
        Returns:
            是否保存成功
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"integrated_analysis_{report['symbol']}_{timestamp}.json"
            
            output_path = Path(__file__).parent.parent / "logs" / "decisions"
            output_path.mkdir(parents=True, exist_ok=True)
            
            file_path = output_path / filename
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2, default=str)
            
            self.logger.info(f"报告已保存: {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"报告保存失败: {e}", exc_info=True)
            return False

    async def analyze_symbol_realtime(
        self,
        symbol: str,
        period: str = "1h",
        user_message: str = "",
        additional_instructions: str = ""
    ) -> dict:
        """
        实时技术分析（方案二）
        根据分析指标和prompt，调用多种模型进行分析，汇总结果输出Markdown文档
        """
        self.logger.info(f"开始实时分析: {symbol} (period={period})")
        
        try:
            # 步骤1: 获取市场数据
            market_data = await self._fetch_market_data(symbol)
            
            # 步骤2: 计算技术指标
            indicators = await self._calculate_indicators(market_data)
            
            # 步骤3: 获取账户信息
            account_info = await self._get_account_info(symbol)
            
            # 步骤4: 准备LLM输入数据
            llm_input = self._prepare_realtime_llm_input(
                symbol,
                period,
                market_data,
                indicators,
                account_info,
                user_message,
                additional_instructions
            )
            
            # 步骤5: 调用多种模型进行分析
            model_results = await self._run_realtime_llm_analysis(llm_input)
            
            # 步骤6: 汇总分析结果
            final_analysis = await self._aggregate_realtime_analysis(model_results, symbol)
            
            # 步骤7: 生成Markdown报告
            markdown_report = self._generate_markdown_report(final_analysis, model_results)
            
            # 步骤8: 保存报告
            self._save_markdown_report(symbol, markdown_report)
            
            self.logger.info(f"实时分析完成: {symbol}")
            
            return {
                "success": True,
                "symbol": symbol,
                "period": period,
                "analysis_time": llm_input['current_time_utc'],
                "markdown_report": markdown_report,
                "model_analyses": model_results
            }
            
        except Exception as e:
            self.logger.error(f"实时分析失败 {symbol}: {e}")
            raise
    
    def _prepare_realtime_llm_input(
        self,
        symbol: str,
        period: str,
        market_data: dict,
        indicators: dict,
        account_info: dict,
        user_message: str,
        additional_instructions: str
    ) -> dict:
        """准备实时分析的LLM输入数据"""
        from datetime import datetime, timezone
        
        current_time_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        
        # K线摘要
        klines_summary = self._generate_klines_summary(market_data['klines_1h'])
        
        # 技术指标摘要
        indicators_summary = self._generate_indicators_summary(indicators, period)
        
        # 资金流指标摘要
        flow_indicators_summary = self._generate_flow_indicators_summary(market_data)
        
        # 持仓情况摘要
        positions_summary = self._generate_positions_summary(account_info, symbol)
        
        # 获取佣金费率
        commission_rates = self.data_fetcher.get_commission_rate(symbol)
        
        return {
            "symbol": symbol,
            "period": period,
            "current_time_utc": current_time_utc,
            "current_price": market_data['ticker']['price'],
            "change_24h": market_data['ticker_24h']['price_change_percent'],
            "volume_24h": market_data['ticker_24h']['volume'],
            "open_interest": "N/A",  # 需要从API获取
            "funding_rate": "N/A",  # 需要从API获取
            "commission_rates": commission_rates,  # 佣金费率
            "kline_count": 20,
            "klines_summary": klines_summary,
            "indicators_summary": indicators_summary,
            "flow_indicators_summary": flow_indicators_summary,
            "positions_summary": positions_summary,
            "user_message": user_message,
            "additional_instructions": additional_instructions
        }
    
    def _generate_klines_summary(self, klines):
        """生成K线摘要"""
        if klines.empty:
            return "暂无K线数据"
        
        summary_lines = []
        recent_klines = klines.tail(20)
        
        for i, (idx, row) in enumerate(recent_klines.iterrows()):
            time_str = idx.strftime("%H:%M")
            candle_type = "🟢" if row['close'] >= row['open'] else "🔴"
            summary_lines.append(f"{time_str}: {candle_type} {row['open']:.4f} → {row['close']:.4f} (高: {row['high']:.4f}, 低: {row['low']:.4f})")
        
        return "\n".join(summary_lines)
    
    def _generate_indicators_summary(self, indicators, period):
        """生成技术指标摘要"""
        period_indicators = indicators.get(period, indicators.get('1h', {}))
        
        summary = []
        
        # 趋势指标
        if 'trend' in period_indicators:
            trend = period_indicators['trend']
            summary.append(f"### 趋势指标")
            summary.append(f"- 趋势方向: {trend.get('trend', '未知')}")
            summary.append(f"- 趋势强度: {trend.get('strength', 0)}/100")
        
        # RSI
        if 'rsi' in period_indicators:
            rsi = period_indicators['rsi']
            summary.append(f"\n### RSI")
            summary.append(f"- RSI数值: {rsi.get('value', 0):.2f}")
            summary.append(f"- RSI状态: {rsi.get('status', '未知')}")
        
        # MACD
        if 'macd' in period_indicators:
            macd = period_indicators['macd']
            summary.append(f"\n### MACD")
            summary.append(f"- MACD线: {macd.get('macd', 0):.4f}")
            summary.append(f"- 信号线: {macd.get('signal', 0):.4f}")
            summary.append(f"- 柱状图: {macd.get('histogram', 0):.4f}")
        
        # 均线
        if 'ma' in period_indicators:
            ma = period_indicators['ma']
            summary.append(f"\n### 均线")
            for key, value in ma.items():
                if value:
                    summary.append(f"- {key.upper()}: {value:.4f}")
        
        # 布林带
        if 'bollinger' in period_indicators:
            bb = period_indicators['bollinger']
            summary.append(f"\n### 布林带")
            summary.append(f"- 上轨: {bb.get('upper', 0):.4f}")
            summary.append(f"- 中轨: {bb.get('middle', 0):.4f}")
            summary.append(f"- 下轨: {bb.get('lower', 0):.4f}")
        
        return "\n".join(summary)
    
    def _generate_flow_indicators_summary(self, market_data):
        """生成资金流指标摘要"""
        ticker_24h = market_data.get('ticker_24h', {})
        
        summary = []
        summary.append(f"- 24小时成交量: {ticker_24h.get('volume', 0):.2f}")
        summary.append(f"- 24小时成交额: {ticker_24h.get('quote_volume', 0):.2f} USDT")
        summary.append(f"- 最高价: {ticker_24h.get('high_price', 0):.4f}")
        summary.append(f"- 最低价: {ticker_24h.get('low_price', 0):.4f}")
        
        return "\n".join(summary)
    
    def _generate_positions_summary(self, account_info: dict, symbol: str):
        """生成持仓情况摘要"""
        balances = account_info.get('balances', {})
        base_asset = symbol.replace('USDT', '')
        
        summary = []
        summary.append(f"- 可用USDT余额: {balances.get('USDT', 0):.4f}")
        summary.append(f"- 可用{base_asset}余额: {balances.get(base_asset, 0):.6f}")
        summary.append(f"- 总资产(USDT): {account_info.get('total_assets_usdt', 0):.4f}")
        
        trade_stats = account_info.get('trade_statistics', {})
        if trade_stats:
            summary.append(f"\n- 总交易次数: {trade_stats.get('total_trades', 0)}")
            summary.append(f"- 胜率: {trade_stats.get('win_rate', 0):.2f}%")
        
        return "\n".join(summary)
    
    async def _run_realtime_llm_analysis(self, llm_input: dict) -> dict:
        """运行实时分析的LLM调用"""
        try:
            # 使用所有可用模型进行分析
            model_results = await self.llm_analyzer.async_analyze_all("technical", llm_input)
            
            # 处理Markdown格式的返回结果
            # 现在LLM已经直接返回Markdown格式，不需要额外处理
            processed_results = {}
            for model_name, result in model_results.items():
                if isinstance(result, dict) and not result.get("error"):
                    # LLM已直接返回Markdown格式
                    processed_results[model_name] = {
                        "markdown_analysis": result.get("analysis", ""),
                        "structured_result": result,
                        "success": True,
                        "format": result.get("format", "markdown")
                    }
                else:
                    processed_results[model_name] = result
            
            return processed_results
            
        except Exception as e:
            self.logger.error(f"实时LLM分析失败: {e}")
            raise
    
    async def _aggregate_realtime_analysis(self, model_results: dict, symbol: str) -> str:
        """汇总多个模型的分析结果"""
        try:
            # 准备汇总prompt
            aggregate_prompt = self._prepare_aggregate_prompt(model_results, symbol)
            
            # 获取第一个可用的模型进行汇总分析
            enabled_models = self.llm_analyzer.config.get_all_enabled_models()
            if enabled_models:
                primary_model = next(iter(enabled_models.keys()))
                self.logger.info(f"使用 {primary_model} 进行汇总分析")
                
                # 使用async_analyze方法进行汇总
                aggregated_result = await self.llm_analyzer.async_analyze(
                    primary_model, 
                    "technical",  # 使用technical角色进行汇总
                    aggregate_prompt
                )
                
                return aggregated_result.get("analysis", aggregated_result.get("response", ""))
            else:
                self.logger.warning("没有可用的模型进行汇总分析")
                raise Exception("没有可用的模型")
            
        except Exception as e:
            self.logger.error(f"汇总分析失败: {e}")
            # 如果汇总失败，返回第一个模型的Markdown分析结果
            if model_results:
                first_model = next(iter(model_results.keys()))
                first_result = model_results[first_model]
                if isinstance(first_result, dict) and not first_result.get("error"):
                    return first_result.get("markdown_analysis", first_result.get("analysis", ""))
                return str(first_result)
            return ""
    
    def _prepare_aggregate_prompt(self, model_results: dict, symbol: str) -> dict:
        """准备汇总分析的prompt"""
        from datetime import datetime, timezone
        
        current_time_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        
        # 收集所有模型的Markdown分析结果
        analyses_summary = []
        for model_name, result in model_results.items():
            if isinstance(result, dict) and not result.get("error"):
                # 提取Markdown分析内容
                markdown_analysis = result.get("markdown_analysis", 
                                            result.get("analysis", 
                                            result.get("response", "")))
                analyses_summary.append(f"\n## {model_name.upper()} 分析结果\n{markdown_analysis}")
        
        return {
            "symbol": symbol,
            "current_time_utc": current_time_utc,
            "model_analyses": "\n".join(analyses_summary),
            "user_message": "请汇总以下多个AI模型对同一交易标的的技术分析结果，综合各模型的观点，输出最终的统一分析报告。"
        }
    
    def _generate_markdown_report(self, final_analysis: str, model_results: dict) -> str:
        """生成最终的Markdown报告"""
        report_parts = [
            "# 📈 加密货币技术分析报告",
            "---",
            "",
            "## 📋 报告摘要",
            "本报告基于多个AI模型的技术分析结果汇总而成，为您提供全面的市场洞察和交易建议。",
            "",
            "---",
            "",
            "## 🎯 综合分析结论",
            final_analysis,
            "",
            "---",
            "",
            "## 🤖 各模型分析详情",
            ""
        ]
        
        # 添加各模型的详细分析（提取Markdown内容）
        for model_name, result in model_results.items():
            if isinstance(result, dict) and not result.get("error"):
                # 提取Markdown分析内容
                markdown_analysis = result.get("markdown_analysis", 
                                            result.get("analysis", 
                                            result.get("response", "")))
                report_parts.append(f"### {model_name.upper()}")
                report_parts.append(markdown_analysis)
                report_parts.append("")
            else:
                # 处理错误情况
                report_parts.append(f"### {model_name.upper()}")
                report_parts.append(f"❌ 分析失败: {result.get('error', '未知错误') if isinstance(result, dict) else str(result)}")
                report_parts.append("")
        
        # 添加免责声明
        report_parts.append("---")
        report_parts.append("## ⚠️ 免责声明")
        report_parts.append("本报告仅供参考，不构成任何投资建议。加密货币交易存在高风险，请谨慎决策。")
        report_parts.append("")
        report_parts.append("*报告生成时间: " + datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC") + "*")
        
        return "\n".join(report_parts)
    
    def _save_markdown_report(self, symbol: str, markdown_report: str):
        """保存Markdown报告"""
        try:
            from datetime import datetime
            from pathlib import Path
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"realtime_analysis_{symbol}_{timestamp}.md"
            
            output_path = Path("./trading_decision_system/logs/reports/")
            output_path.mkdir(parents=True, exist_ok=True)
            
            file_path = output_path / filename
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(markdown_report)
            
            self.logger.info(f"Markdown报告已保存: {file_path}")
            
        except Exception as e:
            self.logger.error(f"Markdown报告保存失败: {e}")


# 全局变量
engine: Optional[TradingDecisionEngine] = None
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
    global engine
    
    logger = setup_logger(
        name="integrated_service",
        log_level="INFO",
        log_file="./trading_decision_system/logs/integrated_service.log"
    )
    
    logger.info("启动整合服务...")
    
    try:
        engine = TradingDecisionEngine()
        logger.info("交易决策引擎初始化成功")
    except Exception as e:
        logger.error(f"交易决策引擎初始化失败: {e}")
        raise


@health_router.get("/")
async def root():
    return {
        "message": "交易决策系统 - 整合服务运行中",
        "version": "1.0.0",
        "features": [
            "定时任务 (每5分钟)",
            "API接口触发分析 (方案一)",
            "实时技术分析 (方案二)"
        ],
        "endpoints": [
            "/health - 健康检查",
            "/api/v1/analyze - 触发分析决策 (方案一)",
            "/api/v1/analyze-realtime - 实时技术分析 (方案二)"
        ]
    }


@health_router.get("/health")
async def health_check():
    """健康检查接口"""
    if engine:
        return {
            "status": "healthy",
            "message": "整合服务运行正常",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    else:
        raise HTTPException(status_code=503, detail="服务未初始化")


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
        if not engine:
            raise HTTPException(status_code=503, detail="分析引擎未初始化")
        
        if not request.symbols:
            raise HTTPException(status_code=400, detail="交易对列表不能为空")
        
        engine.logger.info(f"收到分析请求: symbols={request.symbols}, role={request.role}")
        
        results = {}
        errors = {}
        
        for symbol in request.symbols:
            try:
                result = await engine.analyze_symbol(symbol, request.role.value)
                results[symbol] = {
                    "success": True,
                    "decision": result['final_decision']['final_decision']['action'].upper(),
                    "confidence": result['final_decision']['final_decision']['confidence_score'],
                    "entry_price": result['final_decision']['final_decision']['entry_price'],
                    "stop_loss": result['final_decision']['final_decision']['stop_loss']
                }
            except Exception as e:
                errors[symbol] = str(e)
                engine.logger.error(f"分析 {symbol} 失败: {e}")
        
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
        if engine:
            engine.logger.error(f"API请求处理失败: {e}")
        raise HTTPException(status_code=500, detail=f"服务器错误: {str(e)}")


@analysis_router.post("/analyze-realtime", response_model=RealTimeAnalysisResponse)
async def trigger_realtime_analysis(request: RealTimeAnalysisRequest):
    """
    触发实时技术分析接口（方案二）
    
    Args:
        symbol: 要分析的交易对
        period: 分析周期 (1h, 4h, 1d)
        user_message: 用户自定义问题
        additional_instructions: 额外分析要求
        
    Returns:
        实时分析结果（包含Markdown报告）
    """
    try:
        if not engine:
            raise HTTPException(status_code=503, detail="分析引擎未初始化")
        
        if not request.symbol:
            raise HTTPException(status_code=400, detail="交易对不能为空")
        
        engine.logger.info(f"收到实时分析请求: symbol={request.symbol}, period={request.period}")
        
        result = await engine.analyze_symbol_realtime(
            symbol=request.symbol,
            period=request.period,
            user_message=request.user_message,
            additional_instructions=request.additional_instructions
        )
        
        return RealTimeAnalysisResponse(
            success=True,
            message="实时分析完成",
            symbol=result['symbol'],
            period=result['period'],
            analysis_time=result['analysis_time'],
            markdown_report=result['markdown_report'],
            model_analyses=result['model_analyses']
        )
            
    except HTTPException:
        raise
    except Exception as e:
        if engine:
            engine.logger.error(f"实时分析请求处理失败: {e}")
        return RealTimeAnalysisResponse(
            success=False,
            message="实时分析失败",
            symbol=request.symbol,
            period=request.period,
            analysis_time=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
            error=str(e)
        )


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
        
        # 初始化引擎
        self.engine = TradingDecisionEngine()
        
        # 初始化调度器
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
                    await self.engine.analyze_symbol(symbol, role)
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


# 注册路由
app.include_router(health_router)
app.include_router(analysis_router)



