"""
实时分析策略
实现实时技术分析功能
"""

from typing import Dict, Optional
from pathlib import Path

from trading_decision_system.utils.config_loader import ConfigLoader
from trading_decision_system.services.analysis_strategy.base_analysis_strategy import BaseAnalysisStrategy
from trading_decision_system.utils.logger import log_exceptions


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
    
    @log_exceptions
    async def _run_realtime_llm_analysis(self, llm_input: dict) -> dict:
        """运行实时LLM分析"""
        self.info("开始运行实时LLM分析", symbol=llm_input.get('symbol', 'Unknown'))
        
        model_results = await self.llm_analyzer.async_analyze_all("technical", llm_input)
        
        self.debug("实时LLM分析完成", 
                  symbol=llm_input.get('symbol', 'Unknown'), 
                  model_count=len(model_results))
        
        return model_results
    
    @log_exceptions
    async def _aggregate_realtime_analysis(self, model_results: dict, symbol: str) -> dict:
        """聚合实时分析结果"""
        if not model_results:
            raise Exception("没有分析结果")
        
        # 简单聚合：取第一个成功的结果作为临时聚合结果
        temporary_result = None
        for model_name, result in model_results.items():
            # 检查模型是否分析成功：如果结果中没有 success 字段或者 success 字段为 True，则认为分析成功
            if not result.get('success') is False:
                temporary_result = {
                    "model": model_name,
                    "analysis": result.get('analysis', {}),
                    "recommendation": result.get('recommendation', {})
                }
                break
        
        if not temporary_result:
            raise Exception("所有模型分析失败")
        
        # 使用 deepseek-r1 聚合分析各个模型的结果
        self.info("使用 deepseek-r1 聚合分析模型结果", symbol=symbol, model_count=len(model_results))
        
        # 准备聚合分析的 prompt
        prompt = f"【角色】你是专业的交易策略分析师，拥有10年以上交易经验\n"
        prompt += f"【任务】分析以下多个AI模型对同一交易对的分析结果，然后给出最终的综合分析和交易建议\n\n"
        prompt += f"=== 分析背景 ===\n"
        prompt += f"交易标的：{symbol}\n\n"
        prompt += f"=== 任务要求 ===\n"
        prompt += "请作为专业的交易策略分析师，分析以下多个AI模型对同一交易对的分析结果，然后给出最终的综合分析和交易建议。\n\n"
        prompt += "分析要求：\n"
        prompt += "1. 详细分析每个模型的观点和理由\n"
        prompt += "2. 比较不同模型之间的异同点\n"
        prompt += "3. 基于所有模型的分析，给出最终的综合分析\n"
        prompt += "4. 提供明确的交易建议，包括买入/卖出/持有决策\n"
        prompt += "5. 分析交易的风险和潜在收益\n"
        prompt += "6. 给出具体的入场点、止损点和止盈点建议\n\n"
        prompt += "=== 模型分析结果 ===\n"
        
        for model_name, result in model_results.items():
            prompt += f"### {model_name}\n"
            prompt += f"- 状态: 成功\n"
            if 'analysis' in result:
                analysis_content = result['analysis']
                prompt += f"- 分析: {analysis_content}\n"
            prompt += "\n"
        
        self.info("聚合分析prompt准备完成", symbol=symbol, prompt=prompt)
        # 调用 deepseek-r1 模型进行聚合分析
        deepseek_result = await self.llm_analyzer.async_analyze("deepseek", "technical", prompt)
        
        # 检查 deepseek-r1 分析是否成功：如果结果中没有 success 字段或者 success 字段为 True，则认为分析成功
        if not deepseek_result.get('success') is False:
            self.info("deepseek-r1 聚合分析完成", symbol=symbol)
            return {
                "model": "deepseek-r1 (聚合分析)",
                "analysis": deepseek_result.get('analysis', {}),
                "recommendation": deepseek_result.get('recommendation', {})
            }
        else:
            self.warning("deepseek-r1 聚合分析失败，使用临时聚合结果", symbol=symbol)
            return temporary_result
    
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
        if 'recommendation' in final_analysis:
            recommendation = final_analysis['recommendation']
            report.append(f"- 最终建议: {recommendation.get('action', 'hold')}")
            report.append(f"- 置信度: {recommendation.get('confidence', 0)}")
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
            report.append(f"- 分析理由: {recommendation.get('reason', '无详细理由')}")
            report.append("")
        
        # 模型详细结果
        report.append("## 🤖 模型详细结果")
        for model_name, result in model_results.items():
            report.append(f"### {model_name}")
            if result.get('success'):
                report.append(f"- 状态: 成功")
                if 'analysis' in result:
                    report.append(f"- 分析: {result['analysis']}")
                if 'recommendation' in result:
                    recommendation = result['recommendation']
                    report.append(f"- 建议: {recommendation.get('action', 'hold')}")
                    report.append(f"- 置信度: {recommendation.get('confidence', 0)}")
                    if 'reason' in recommendation:
                        report.append(f"- 理由: {recommendation['reason']}")
            else:
                report.append(f"- 状态: 失败")
                report.append(f"- 错误: {result.get('error', 'Unknown error')}")
            report.append("")
        
        # 风险分析
        report.append("## ⚠️ 风险分析")
        report.append("- 市场风险: 加密货币市场波动较大，请谨慎交易")
        report.append("- 模型风险: AI模型分析基于历史数据，可能无法预测突发市场事件")
        report.append("- 执行风险: 交易执行价格可能与分析时的价格存在差异")
        report.append("")
        
        # 交易策略建议
        report.append("## 📝 交易策略建议")
        report.append("1. **资金管理**: 建议使用不超过总资金20%的资金进行单笔交易")
        report.append("2. **止损设置**: 建议设置5-10%的止损位，控制单笔交易风险")
        report.append("3. **止盈设置**: 建议设置15-30%的止盈位，确保收益")
        report.append("4. **仓位管理**: 根据市场波动性调整仓位大小")
        report.append("5. **监控频率**: 建议至少每4小时监控一次交易情况")
        report.append("")
        
        # 免责声明
        report.append("## 📄 免责声明")
        report.append("本分析报告仅供参考，不构成任何投资建议。")
        report.append("交易决策请结合个人风险承受能力和市场实际情况。")
        report.append("过往表现不代表未来结果，投资有风险，入市需谨慎。")
        
        return "\n".join(report)
    
    @log_exceptions
    def _save_markdown_report(self, symbol: str, report: str) -> bool:
        """保存Markdown报告"""
        from datetime import datetime
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"realtime_analysis_{symbol}_{timestamp}.md"
        
        output_path = Path(__file__).parent.parent / "logs" / "realtime"
        output_path.mkdir(parents=True, exist_ok=True)
        
        file_path = output_path / filename
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(report)
        
        self.info("报告已保存", symbol=symbol, file_path=str(file_path))
        return True
    
    @log_exceptions
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
        self.info("开始实时分析", 
                 symbol=symbol, 
                 timeframes=["1h", "4h", "1d"],
                 user_message=user_message[:100] + "..." if len(user_message) > 100 else user_message)
        
        # 步骤1: 获取市场数据
        self.info("步骤1: 获取市场数据", symbol=symbol)
        market_data = await self._fetch_market_data(symbol)
        self.info("市场数据获取完成", 
                  symbol=symbol, 
                  data_types=["1h K线", "4h K线", "1d K线", "ticker", "24h ticker", "commission rates"])
        
        # 步骤2: 计算技术指标
        self.info("步骤2: 计算技术指标", symbol=symbol)
        indicators = await self._calculate_indicators(market_data)
        self.info("技术指标计算完成", 
                  symbol=symbol, 
                  indicators=["趋势", "RSI", "MACD", "均线", "布林带"])
        
        # 步骤3: 获取账户信息
        self.info("步骤3: 获取账户信息", symbol=symbol)
        account_info = await self._get_account_info(symbol)
        self.info("账户信息获取完成", 
                  symbol=symbol, 
                  total_assets=account_info.get('total_assets_usdt', 0))
        
        # 步骤4: 准备LLM输入数据
        self.info("步骤4: 准备LLM输入数据", symbol=symbol)
        llm_input = self._prepare_realtime_llm_input(
            symbol,
            market_data,
            indicators,
            account_info,
            user_message,
            additional_instructions
        )
        self.debug("LLM输入数据准备完成", 
                  symbol=symbol, 
                  input_size=len(str(llm_input)))
        
        # 步骤5: 调用多种模型进行分析
        self.info("步骤5: 调用多种模型进行分析", symbol=symbol)
        model_results = await self._run_realtime_llm_analysis(llm_input)
        self.debug("模型分析完成", 
                  symbol=symbol, 
                  model_count=len(model_results))
        
        # 步骤6: 汇总分析结果
        self.info("步骤6: 汇总分析结果", symbol=symbol)
        final_analysis = await self._aggregate_realtime_analysis(model_results, symbol)
        self.info("分析结果汇总完成", 
                  symbol=symbol, 
                  final_model=final_analysis.get('model', 'Unknown'))
        
        # 步骤7: 生成Markdown报告
        self.info("步骤7: 生成Markdown报告", symbol=symbol)
        markdown_report = self._generate_markdown_report(final_analysis, model_results)
        self.debug("Markdown报告生成完成", 
                  symbol=symbol, 
                  report_length=len(markdown_report))
        
        # 步骤8: 保存报告
        self.info("步骤8: 保存报告", symbol=symbol)
        self._save_markdown_report(symbol, markdown_report)
        self.info("报告保存完成", symbol=symbol)
        
        self.info("实时分析完成", symbol=symbol)
        
        return {
            "success": True,
            "symbol": symbol,
            "analysis_time": llm_input['current_time_utc'],
            "markdown_report": markdown_report,
            "model_analyses": model_results
        }
