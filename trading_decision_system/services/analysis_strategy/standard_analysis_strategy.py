"""
标准分析策略
实现标准分析决策功能
"""

import logging
import json
from typing import Dict, List, Optional
from pathlib import Path

from trading_decision_system.utils.config_loader import ConfigLoader
from trading_decision_system.services.analysis_strategy.base_analysis_strategy import BaseAnalysisStrategy
from trading_decision_system.decision.decision_aggregator import DecisionAggregator
from trading_decision_system.decision.risk_controller import RiskController


class StandardAnalysisStrategy(BaseAnalysisStrategy):
    """
    标准分析策略
    """
    
    def __init__(self, config=None):
        """
        初始化标准分析策略
        
        Args:
            config: 配置对象
        """
        super().__init__(config)
        self._init_additional_modules()
    
    def _init_additional_modules(self):
        """初始化额外模块"""
        self.logger.info("初始化决策聚合模块...")
        self.decision_aggregator = DecisionAggregator(self.config)
        
        self.logger.info("初始化风险控制模块...")
        self.risk_controller = RiskController(self.config)
    
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
    
    async def execute(self, symbol: str, role: str = "technical") -> Dict:
        """
        执行标准分析
        
        Args:
            symbol: 交易对
            role: 分析角色
            
        Returns:
            分析结果
        """
        self.logger.info(f"开始分析: {symbol} ({role})")
        
        try:
            # 步骤1: 获取市场数据
            self.logger.info(f"步骤1: 获取市场数据 - {symbol}")
            market_data = await self._fetch_market_data(symbol)
            self.logger.info(f"市场数据获取完成: {symbol}, 包含1h/4h/1d K线数据")
            
            # 步骤2: 计算技术指标
            self.logger.info(f"步骤2: 计算技术指标 - {symbol}")
            indicators = await self._calculate_indicators(market_data)
            self.logger.info(f"技术指标计算完成: {symbol}, 包含趋势/RSI/MACD/均线/布林带等指标")
            
            # 步骤3: 获取账户信息
            self.logger.info(f"步骤3: 获取账户信息 - {symbol}")
            account_info = await self._get_account_info(symbol)
            self.logger.info(f"账户信息获取完成: {symbol}, 总资产: {account_info.get('total_assets_usdt', 0):.2f} USDT")
            
            # 步骤4: 准备LLM输入数据
            self.logger.info(f"步骤4: 准备LLM输入数据 - {symbol}")
            llm_input = self._prepare_llm_input(
                symbol,
                market_data['ticker'],
                market_data['ticker_24h'],
                indicators['1h'],
                indicators['4h'],
                indicators['1d'],
                account_info
            )
            self.logger.info(f"LLM输入数据准备完成: {symbol}, 包含价格/趋势/指标等数据")
            
            # 步骤5: 调用LLM分析
            self.logger.info(f"步骤5: 调用LLM分析 - {symbol}, 角色: {role}")
            model_results = await self._run_llm_analysis(role, llm_input)
            self.logger.info(f"LLM分析完成: {symbol}, 分析模型数量: {len(model_results)}")
            
            # 步骤6: 聚合决策
            self.logger.info(f"步骤6: 聚合决策 - {symbol}")
            final_decision = await self._aggregate_decisions(model_results, account_info)
            action = final_decision.get('final_decision', {}).get('action', 'hold').upper()
            confidence = final_decision.get('final_decision', {}).get('confidence_score', 0)
            self.logger.info(f"决策聚合完成: {symbol}, 决策: {action}, 置信度: {confidence:.2f}")
            
            # 步骤7: 风险评估
            self.logger.info(f"步骤7: 风险评估 - {symbol}")
            risk_report = await self._evaluate_risk(
                symbol,
                final_decision,
                account_info,
                market_data['klines_1h'],
                market_data['ticker_24h']
            )
            risk_level = risk_report.get('risk_level', 'unknown')
            self.logger.info(f"风险评估完成: {symbol}, 风险等级: {risk_level}")
            
            # 步骤8: 生成最终报告
            self.logger.info(f"步骤8: 生成最终报告 - {symbol}")
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
            self.logger.info(f"最终报告生成完成: {symbol}")
            
            # 步骤9: 保存报告
            self.logger.info(f"步骤9: 保存报告 - {symbol}")
            self._save_report(final_report)
            self.logger.info(f"报告保存完成: {symbol}")
            
            self.logger.info(f"分析完成: {symbol}")
            
            return final_report
            
        except Exception as e:
            self.logger.error(f"分析失败 {symbol}: {e}")
            self.logger.error(f"错误详情: {str(e)}", exc_info=True)
            raise


# 导入datetime模块
from datetime import datetime
