"""
多模型数字货币智能决策系统 - 主程序
"""

import asyncio
import json
from math import log
import sys
from datetime import datetime
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from trading_decision_system.utils.logger import setup_logger
from trading_decision_system.utils.config_loader import ConfigLoader
from trading_decision_system.data.data_fetcher import DataFetcher
from trading_decision_system.data.indicator_calculator import IndicatorCalculator
from trading_decision_system.data.account_manager import AccountManager
from trading_decision_system.analysis.llm_analyzer import LLMAnalyzer
from trading_decision_system.analysis.prompt_templates import PromptTemplates
from trading_decision_system.decision.decision_aggregator import DecisionAggregator
from trading_decision_system.decision.risk_controller import RiskController
from trading_decision_system.scheduler.task_scheduler import TaskScheduler

class TradingDecisionSystem:
    """
    多模型数字货币智能决策系统
    """
    
    def __init__(self, config_path: str = "./trading_decision_system/configs/config.yaml"):
        # 初始化日志
        self.logger = setup_logger(
            name="trading_decision_system",
            log_level="INFO",
            log_file="./trading_decision_system/logs/system.log"
        )
        
        self.logger.info("="*60)
        self.logger.info("多模型数字货币智能决策系统")
        self.logger.info("="*60)
        
        # 加载配置
        self.logger.info("加载配置文件...")
        self.config = ConfigLoader(config_path)
        
        # 初始化模块
        self._init_modules()
        
        self.logger.info("系统初始化完成")
    
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
        
        self.logger.info("初始化任务调度模块...")
        self.task_scheduler = TaskScheduler(self.config)
    
    async def run_analysis(
        self,
        symbol: str,
        role: str = "strategist"
    ) -> dict:
        """
        执行完整分析流程
        
        Args:
            symbol: 交易对
            role: 分析角色 (strategist/technical/risk)
            
        Returns:
            分析结果
        """
        self.logger.info(f"\n{'='*80}")
        self.logger.info(f"开始分析: {symbol} ({role})")
        self.logger.info(f"{'='*80}\n")
        
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
            self.logger.info(f"LLM分析结果: {model_results}")
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
            
            # 分析完成
            self.logger.info("\n" + "="*80)
            self.logger.info("✅ 分析完成!")
            self.logger.info(f"交易对: {symbol}")
            self.logger.info(f"分析角色: {role}")
            self.logger.info(f"最终决策: {final_decision['final_decision']['action'].upper()}")
            self.logger.info(f"信心度: {final_decision['final_decision']['confidence_score']}/100")
            self.logger.info("="*80 + "\n")
            
            return final_report
            
        except Exception as e:
            self.logger.error("\n" + "="*80)
            self.logger.error("❌ 分析失败!")
            self.logger.error(f"交易对: {symbol}")
            self.logger.error(f"分析角色: {role}")
            self.logger.error(f"错误信息: {e}")
            self.logger.error("="*80 + "\n")
            raise
    
    async def _fetch_market_data(self, symbol: str) -> dict:
        """获取市场数据"""
        self.logger.info("\n" + "-"*80)
        self.logger.info("步骤1: 获取市场数据")
        self.logger.info("-"*80)
        
        try:
            # 并行获取不同时间周期的K线数据
            klines_1h = self.data_fetcher.get_klines(symbol, "1h", limit=100)
            klines_4h = self.data_fetcher.get_klines(symbol, "4h", limit=50)
            klines_1d = self.data_fetcher.get_klines(symbol, "1d", limit=30)
            
            ticker = self.data_fetcher.get_symbol_ticker(symbol)
            ticker_24h = self.data_fetcher.get_24h_ticker(symbol)
            
            self.logger.info(f"  ✓ K线数据: 1h({len(klines_1h)}), 4h({len(klines_4h)}), 1d({len(klines_1d)})")
            self.logger.info(f"  ✓ 当前价格: {ticker['price']} USDT")
            self.logger.info(f"  ✓ 24h涨跌幅: {ticker_24h['price_change_percent']}%")
            self.logger.info(f"  ✓ 24h成交量: {ticker_24h['volume']}")
            self.logger.info(f"  ✓ 24h最高价: {ticker_24h['high_price']}")
            self.logger.info(f"  ✓ 24h最低价: {ticker_24h['low_price']}")
            
            return {
                'klines_1h': klines_1h,
                'klines_4h': klines_4h,
                'klines_1d': klines_1d,
                'ticker': ticker,
                'ticker_24h': ticker_24h
            }
            
        except Exception as e:
            self.logger.error(f"  ❌ 市场数据获取失败: {e}")
            raise
    
    async def _calculate_indicators(self, market_data: dict) -> dict:
        """计算技术指标"""
        self.logger.info("\n" + "-"*80)
        self.logger.info("步骤2: 计算技术指标")
        self.logger.info("-"*80)
        
        try:
            # 并行计算不同时间周期的指标
            indicators_1h = self.indicator_calculator.calculate_all_indicators(market_data['klines_1h'])
            indicators_4h = self.indicator_calculator.calculate_all_indicators(market_data['klines_4h'])
            indicators_1d = self.indicator_calculator.calculate_all_indicators(market_data['klines_1d'])
            
            self._log_indicators("1小时", indicators_1h)
            self._log_indicators("4小时", indicators_4h)
            self._log_indicators("日线", indicators_1d)
            
            return {
                '1h': indicators_1h,
                '4h': indicators_4h,
                '1d': indicators_1d
            }
            
        except Exception as e:
            self.logger.error(f"  ❌ 技术指标计算失败: {e}")
            raise
    
    def _log_indicators(self, timeframe: str, indicators: dict):
        """记录指标日志"""
        self.logger.info(f"  ✓ {timeframe}指标:")
        self.logger.info(f"    • RSI: {indicators['rsi']['value']} ({indicators['rsi']['status']})")
        self.logger.info(f"    • MACD: {indicators['macd']['macd']} (Signal: {indicators['macd']['signal']})")
        self.logger.info(f"    • 趋势: {indicators['trend']['trend']} (强度: {indicators['trend']['strength']}%)")
        self.logger.info(f"    • 布林带位置: {indicators['bollinger']['position']}")
    
    async def _get_account_info(self, symbol: str) -> dict:
        """获取账户信息"""
        self.logger.info("\n" + "-"*80)
        self.logger.info("步骤3: 获取账户信息")
        self.logger.info("-"*80)
        
        try:
            account_summary = self.account_manager.get_account_summary(symbol)
            
            self.logger.info(f"  ✓ 总资产: {account_summary['total_assets_usdt']} USDT")
            self.logger.info(f"  ✓ USDT余额: {account_summary['balances'].get('USDT', 0)} USDT")
            self.logger.info(f"  ✓ 持仓币种数量: {len(account_summary['balances'])}")
            self.logger.info(f"  ✓ 交易统计: {account_summary['trade_statistics']}")
            
            return account_summary
            
        except Exception as e:
            self.logger.error(f"  ❌ 账户信息获取失败: {e}")
            raise
    
    async def _run_llm_analysis(self, role: str, llm_input: dict) -> dict:
        """运行LLM分析"""
        self.logger.info("\n" + "-"*80)
        self.logger.info("步骤5: 调用LLM分析")
        self.logger.info("-"*80)
        
        try:
            model_results = await self.llm_analyzer.async_analyze_all(role, llm_input)
            
            self.logger.info(f"  ✓ 模型分析完成: {len(model_results)} 个模型")
            
            for model_name, result in model_results.items():
                if result.get("success", True):
                    self.logger.info(f"    • {model_name}:")
                    self.logger.info(f"      - 信心度: {result.get('confidence_score', 0)}/100")
                    self.logger.info(f"      - 建议动作: {result.get('action', 'N/A')}")
                    self.logger.info(f"      - 趋势判断: {result.get('bias', 'N/A')}")
                    self.logger.info(f"      - 响应时间: {result.get('response_time_seconds', 0)}秒")
                else:
                    self.logger.warning(f"    • {model_name}: 失败 - {result.get('error')}")
            
            return model_results
            
        except Exception as e:
            self.logger.error(f"  ❌ LLM分析失败: {e}")
            raise
    
    async def _aggregate_decisions(self, model_results: dict, account_info: dict) -> dict:
        """聚合决策"""
        self.logger.info("\n" + "-"*80)
        self.logger.info("步骤6: 聚合决策")
        self.logger.info("-"*80)
        
        try:
            # 设置模型权重
            weights = self.llm_analyzer.get_model_weights()
            self.decision_aggregator.set_model_weights(weights)
            
            self.logger.info(f"  ✓ 模型权重配置:")
            for model_name, weight in weights.items():
                self.logger.info(f"    • {model_name}: {weight*100:.0f}%")
            
            final_decision = self.decision_aggregator.aggregate_decisions(
                model_results,
                account_info
            )
            
            decision = final_decision['final_decision']
            consensus = final_decision['model_consensus']
            
            self.logger.info(f"  ✓ 最终决策:")
            self.logger.info(f"    • 动作: {decision['action'].upper()}")
            self.logger.info(f"    • 趋势: {decision['bias'].upper()}")
            self.logger.info(f"    • 信心度: {decision['confidence_score']}/100")
            self.logger.info(f"    • 建议仓位: {decision['recommended_position_size_percent']}%")
            self.logger.info(f"    • 建议仓位价值: {decision['recommended_position_value_usdt']} USDT")
            self.logger.info(f"    • 入场价: {decision['entry_price']}")
            self.logger.info(f"    • 止损价: {decision['stop_loss']}")
            self.logger.info(f"    • 止盈价: {decision['take_profit_levels']}")
            
            self.logger.info(f"  ✓ 模型一致性:")
            self.logger.info(f"    • 一致性级别: {consensus['agreement_level'].upper()}")
            self.logger.info(f"    • 一致性分数: {consensus['agreement_score']}")
            self.logger.info(f"    • 模型数量: {consensus['models_count']}")
            self.logger.info(f"    • 平均信心度: {consensus['avg_confidence']}")
            
            return final_decision
            
        except Exception as e:
            self.logger.error(f"  ❌ 决策聚合失败: {e}")
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
        self.logger.info("\n" + "-"*80)
        self.logger.info("步骤7: 风险评估")
        self.logger.info("-"*80)
        
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
            
            risk = risk_report['validation_result']
            
            self.logger.info(f"  ✓ 风险评估结果:")
            self.logger.info(f"    • 风险级别: {risk['risk_level'].upper()}")
            self.logger.info(f"    • 风险分数: {risk['risk_score']}/100")
            
            if risk.get('errors'):
                self.logger.error(f"  ⚠️  风险错误:")
                for error in risk['errors']:
                    self.logger.error(f"    • {error}")
            
            if risk.get('warnings'):
                self.logger.warning(f"  ⚠️  风险警告:")
                for warning in risk['warnings']:
                    self.logger.warning(f"    • {warning}")
            
            return risk_report
            
        except Exception as e:
            self.logger.error(f"  ❌ 风险评估失败: {e}")
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
        self.logger.info("\n" + "-"*80)
        self.logger.info("步骤8: 生成最终报告")
        self.logger.info("-"*80)
        
        try:
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
                "risk_assessment": risk_report,
                "summary": self._generate_summary(final_decision, risk_report)
            }
            
            self.logger.info(f"  ✓ 最终报告已生成")
            
            return final_report
            
        except Exception as e:
            self.logger.error(f"  ❌ 最终报告生成失败: {e}")
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
    
    def _generate_summary(
        self,
        final_decision: dict,
        risk_report: dict
    ) -> str:
        """生成总结"""
        decision = final_decision['final_decision']
        consensus = final_decision['model_consensus']
        risk = risk_report['validation_result']
        
        summary = f"""\n📊 交易决策总结\n{"="*40}\n
"""
        summary += f"交易对: {final_decision['symbol']}\n"
        summary += f"分析时间: {final_decision['datetime']}\n\n"
        
        summary += f"🎯 最终决策\n{'='*30}\n"
        summary += f"动作: {decision['action'].upper()}\n"
        summary += f"趋势: {decision['bias'].upper()}\n"
        summary += f"信心度: {decision['confidence_score']}/100\n"
        summary += f"建议仓位: {decision['recommended_position_size_percent']}%\n"
        summary += f"仓位价值: {decision['recommended_position_value_usdt']} USDT\n\n"
        
        if decision['entry_price'] > 0:
            summary += f"📈 入场参考\n{'-'*30}\n"
            summary += f"建议入场价: {decision['entry_price']}\n"
            if decision['stop_loss'] > 0:
                summary += f"止损价: {decision['stop_loss']}\n"
            if decision['take_profit_levels']:
                for i, tp in enumerate(decision['take_profit_levels'][:3], 1):
                    summary += f"止盈 {i}: {tp}\n"
            summary += "\n"
        
        summary += f"🤝 模型一致性\n{'-'*30}\n"
        summary += f"一致性级别: {consensus['agreement_level'].upper()}\n"
        summary += f"一致性分数: {consensus['agreement_score']}\n"
        summary += f"模型数量: {consensus['models_count']}\n"
        summary += f"平均信心度: {consensus['avg_confidence']}\n\n"
        
        summary += f"⚠️  风险评估\n{'-'*30}\n"
        summary += f"风险级别: {risk['risk_level'].upper()}\n"
        summary += f"风险分数: {risk['risk_score']}/100\n"
        
        if risk['errors']:
            summary += "\n❌ 风险警告:\n"
            for error in risk['errors']:
                summary += f"  • {error}\n"
        
        if risk['warnings']:
            summary += "\n⚠️  注意事项:\n"
            for warning in risk['warnings']:
                summary += f"  • {warning}\n"
        
        summary += f"\n{'='*40}\n"
        summary += "💡 请仔细评估风险后再做决策\n"
        
        return summary
    
    def _save_report(self, report: dict):
        """保存报告到文件"""
        try:
            output_config = self.config.get("output", {})
            save_to_file = output_config.get("save_to_file", True)
            
            if save_to_file:
                file_path = output_config.get("file_path", "./trading_decision_system/logs/decisions/")
                
                # 确保目录存在
                Path(file_path).mkdir(parents=True, exist_ok=True)
                
                # 生成文件名
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{file_path}analysis_{report['symbol']}_{timestamp}.json"
                
                # 保存JSON
                with open(filename, "w", encoding="utf-8") as f:
                    json.dump(report, f, indent=2, ensure_ascii=False)
                
                self.logger.info(f"报告已保存到: {filename}")
                
        except Exception as e:
            self.logger.error(f"保存报告失败: {e}")
    
    def start_scheduler(self):
        """启动任务调度器"""
        self.task_scheduler.start()
    
    def stop_scheduler(self):
        """停止任务调度器"""
        self.task_scheduler.stop()
    
    def close(self):
        """关闭系统"""
        self.logger.info("正在关闭系统...")
        
        try:
            self.stop_scheduler()
            self.llm_analyzer.close()
            self.logger.info("系统已关闭")
        except Exception as e:
            self.logger.error(f"关闭系统失败: {e}")


async def main():
    """主函数"""
    try:
        # 创建系统实例
        system = TradingDecisionSystem()
        
        # 分析指定交易对
        symbols = system.config.get("exchange.symbols", ["BTCUSDT", "SOLUSDT"])
        
        for symbol in symbols[:2]:  # 只分析前2个
            try:
                report = await system.run_analysis(symbol, "strategist")
                
                # 打印总结
                print(report['summary'])
                
            except Exception as e:
                print(f"分析 {symbol} 失败: {e}\n")
                continue
        
        # 关闭系统
        system.close()
        
    except Exception as e:
        # 记录错误日志
        system.logger.error(f"系统运行失败: {e}", exc_info=True)
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
