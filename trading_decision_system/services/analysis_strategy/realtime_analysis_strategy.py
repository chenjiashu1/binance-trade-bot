"""
实时分析策略
实现实时技术分析功能
"""

import logging
from typing import Dict, Optional
from pathlib import Path

from trading_decision_system.utils.config_loader import ConfigLoader
from trading_decision_system.services.analysis_strategy.base_analysis_strategy import BaseAnalysisStrategy


class RealTimeAnalysisStrategy(BaseAnalysisStrategy):
    """
    实时分析策略
    """
    
    def __init__(self, config=None):
        """
        初始化实时分析策略
        
        Args:
            config: 配置对象
        """
        super().__init__(config)
    
    def _generate_klines_summary(self, klines, time_frame: str) -> str:
        """生成K线摘要"""
        if klines.empty:
            return f"暂无{time_frame}K线数据"
        
        summary = []
        summary.append(f"**{time_frame}图K线摘要:**")
        
        # 最近20根K线
        recent_klines = klines.tail(20)
        
        # 统计信息
        total_candles = len(recent_klines)
        bull_candles = len(recent_klines[recent_klines['close'] > recent_klines['open']])
        bear_candles = len(recent_klines[recent_klines['close'] < recent_klines['open']])
        
        summary.append(f"- 总K线数: {total_candles}")
        summary.append(f"- 阳线: {bull_candles}")
        summary.append(f"- 阴线: {bear_candles}")
        
        # 最近几根K线的具体情况
        for i in range(min(5, total_candles)):
            kline = recent_klines.iloc[-(i+1)]
            open_price = kline['open']
            close_price = kline['close']
            high_price = kline['high']
            low_price = kline['low']
            volume = kline['volume']
            
            candle_type = "阳线" if close_price > open_price else "阴线" if close_price < open_price else "十字星"
            change_percent = ((close_price - open_price) / open_price) * 100
            
            summary.append(f"- 最近第{i+1}根({candle_type}): 开 {open_price:.4f}, 收 {close_price:.4f}, "
                          f"高 {high_price:.4f}, 低 {low_price:.4f}, 涨跌幅 {change_percent:.2f}%")
        
        return "\n".join(summary)
    
    def _generate_indicators_summary(self, indicators: dict) -> str:
        """生成指标摘要"""
        if not indicators:
            return "暂无指标数据"
        
        summary = []
        
        # 趋势指标
        if 'trend' in indicators:
            trend = indicators['trend']
            summary.append(f"**趋势:**")
            summary.append(f"- 方向: {trend.get('trend', 'sideways')}")
            summary.append(f"- 强度: {trend.get('strength', 0)}")
        
        # RSI
        if 'rsi' in indicators:
            rsi = indicators['rsi']
            summary.append(f"\n**RSI:**")
            summary.append(f"- 值: {rsi.get('value', 0):.2f}")
            summary.append(f"- 状态: {rsi.get('status', 'neutral')}")
        
        # MACD
        if 'macd' in indicators:
            macd = indicators['macd']
            summary.append(f"\n**MACD:**")
            summary.append(f"- MACD: {macd.get('macd', 0):.4f}")
            summary.append(f"- Signal: {macd.get('signal', 0):.4f}")
            summary.append(f"- Histogram: {macd.get('histogram', 0):.4f}")
        
        # 均线
        if 'ma' in indicators:
            ma = indicators['ma']
            summary.append(f"\n**均线:**")
            for key, value in ma.items():
                if value:
                    summary.append(f"- {key.upper()}: {value:.4f}")
        
        # 布林带
        if 'bollinger' in indicators:
            bb = indicators['bollinger']
            summary.append(f"\n**布林带:**")
            summary.append(f"- 上轨: {bb.get('upper', 0):.4f}")
            summary.append(f"- 中轨: {bb.get('middle', 0):.4f}")
            summary.append(f"- 下轨: {bb.get('lower', 0):.4f}")
        
        return "\n".join(summary)
    
    def _prepare_realtime_llm_input(
        self,
        symbol: str,
        market_data: dict,
        indicators: dict,
        account_info: dict,
        user_message: str,
        additional_instructions: str
    ) -> dict:
        """准备实时分析LLM输入数据"""
        from datetime import datetime, timezone
        
        current_time_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        
        # 生成三个时间维度的K线摘要
        klines_summary_1h = self._generate_klines_summary(market_data['klines_1h'], "1小时")
        klines_summary_4h = self._generate_klines_summary(market_data['klines_4h'], "4小时")
        klines_summary_1d = self._generate_klines_summary(market_data['klines_1d'], "日线")
        
        # 生成三个时间维度的指标摘要
        indicators_summary_1h = self._generate_indicators_summary(indicators['1h'])
        indicators_summary_4h = self._generate_indicators_summary(indicators['4h'])
        indicators_summary_1d = self._generate_indicators_summary(indicators['1d'])
        
        # 资金流指标摘要
        flow_indicators_summary = "暂无资金流数据"
        
        # 持仓情况摘要
        positions_summary = f"""**持仓情况:**
- 总资产: {account_info.get('total_assets_usdt', 0):.2f} USDT
- USDT余额: {account_info.get('balances', {}).get('USDT', 0):.2f}
- 当前持仓数: {len(account_info.get('balances', {}))}
- 胜率: {account_info.get('trade_statistics', {}).get('win_rate', 0):.2f}%
- 总交易次数: {account_info.get('trade_statistics', {}).get('total_trades', 0)}
"""
        
        return {
            "symbol": symbol,
            "current_time_utc": current_time_utc,
            "current_price": market_data['ticker']['price'],
            "change_24h": market_data['ticker_24h']['price_change_percent'],
            "volume_24h": market_data['ticker_24h']['volume'],
            "open_interest": "N/A",
            "funding_rate": "N/A",
            "commission_rates": market_data['commission_rates'],
            "klines_summary_1h": klines_summary_1h,
            "klines_summary_4h": klines_summary_4h,
            "klines_summary_1d": klines_summary_1d,
            "indicators_summary_1h": indicators_summary_1h,
            "indicators_summary_4h": indicators_summary_4h,
            "indicators_summary_1d": indicators_summary_1d,
            "flow_indicators_summary": flow_indicators_summary,
            "positions_summary": positions_summary,
            "user_message": user_message,
            "additional_instructions": additional_instructions
        }
    
    async def _run_realtime_llm_analysis(self, llm_input: dict) -> dict:
        """运行实时LLM分析"""
        try:
            model_results = await self.llm_analyzer.async_analyze_all("technical", llm_input)
            return model_results
            
        except Exception as e:
            self.logger.error(f"LLM分析失败: {e}")
            raise
    
    async def _aggregate_realtime_analysis(self, model_results: dict, symbol: str) -> dict:
        """聚合实时分析结果"""
        if not model_results:
            return {"error": "没有分析结果"}
        
        # 简单聚合：取第一个成功的结果
        for model_name, result in model_results.items():
            if result.get('success'):
                return {
                    "model": model_name,
                    "analysis": result.get('analysis', {}),
                    "recommendation": result.get('recommendation', {})
                }
        
        return {"error": "所有模型分析失败"}
    
    def _generate_markdown_report(self, final_analysis: dict, model_results: dict) -> str:
        """生成Markdown报告"""
        if not final_analysis:
            return "# 分析失败\n\n没有可用的分析结果"
        
        report = []
        report.append("# 实时技术分析报告")
        report.append("")
        
        # 分析摘要
        report.append("## 📊 分析摘要")
        report.append(f"- 分析模型: {final_analysis.get('model', 'Unknown')}")
        report.append("")
        
        # 详细分析
        if 'analysis' in final_analysis:
            analysis = final_analysis['analysis']
            report.append("## 📈 详细分析")
            report.append(f"{analysis}")
            report.append("")
        
        # 交易建议
        if 'recommendation' in final_analysis:
            recommendation = final_analysis['recommendation']
            report.append("## 💡 交易建议")
            report.append(f"- 操作: {recommendation.get('action', 'hold')}")
            report.append(f"- 置信度: {recommendation.get('confidence', 0)}")
            report.append("")
        
        # 模型对比
        report.append("## 🤖 模型对比")
        for model_name, result in model_results.items():
            if result.get('success'):
                action = result.get('recommendation', {}).get('action', 'hold')
                confidence = result.get('recommendation', {}).get('confidence', 0)
                report.append(f"- **{model_name}**: {action} (置信度: {confidence})")
            else:
                report.append(f"- **{model_name}**: 失败 ({result.get('error', 'Unknown error')})")
        
        return "\n".join(report)
    
    def _save_markdown_report(self, symbol: str, report: str) -> bool:
        """保存Markdown报告"""
        try:
            from datetime import datetime
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"realtime_analysis_{symbol}_{timestamp}.md"
            
            output_path = Path(__file__).parent.parent / "logs" / "realtime"
            output_path.mkdir(parents=True, exist_ok=True)
            
            file_path = output_path / filename
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(report)
            
            self.logger.info(f"报告已保存: {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"报告保存失败: {e}")
            return False
    
    async def execute(self, symbol: str, user_message: str = "", additional_instructions: str = "") -> Dict:
        """
        执行实时分析
        
        Args:
            symbol: 交易对
            user_message: 用户消息
            additional_instructions: 额外指令
            
        Returns:
            分析结果
        """
        self.logger.info(f"开始实时分析: {symbol} (1h/4h/1d 多时间维度)")
        self.logger.info(f"用户消息: {user_message}")
        self.logger.info(f"额外指令: {additional_instructions}")
        
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
            llm_input = self._prepare_realtime_llm_input(
                symbol,
                market_data,
                indicators,
                account_info,
                user_message,
                additional_instructions
            )
            self.logger.info(f"LLM输入数据准备完成: {symbol}, 包含K线摘要和指标摘要")
            
            # 步骤5: 调用多种模型进行分析
            self.logger.info(f"步骤5: 调用多种模型进行分析 - {symbol}")
            model_results = await self._run_realtime_llm_analysis(llm_input)
            self.logger.info(f"模型分析完成: {symbol}, 分析模型结果: {model_results}")
            
            # 步骤6: 汇总分析结果
            self.logger.info(f"步骤6: 汇总分析结果 - {symbol}")
            final_analysis = await self._aggregate_realtime_analysis(model_results, symbol)
            self.logger.info(f"分析结果汇总完成: {symbol}, 选中模型: {final_analysis.get('model', 'Unknown')}")
            
            # 步骤7: 生成Markdown报告
            self.logger.info(f"步骤7: 生成Markdown报告 - {symbol}")
            markdown_report = self._generate_markdown_report(final_analysis, model_results)
            self.logger.info(f"Markdown报告生成完成: {symbol}, 报告长度: {len(markdown_report)} 字符")
            
            # 步骤8: 保存报告
            self.logger.info(f"步骤8: 保存报告 - {symbol}")
            self._save_markdown_report(symbol, markdown_report)
            self.logger.info(f"报告保存完成: {symbol}")
            
            self.logger.info(f"实时分析完成: {symbol}")
            
            return {
                "success": True,
                "symbol": symbol,
                "analysis_time": llm_input['current_time_utc'],
                "markdown_report": markdown_report,
                "model_analyses": model_results
            }
            
        except Exception as e:
            self.logger.error(f"实时分析失败 {symbol}: {e}")
            self.logger.error(f"错误详情: {str(e)}", exc_info=True)
            raise
