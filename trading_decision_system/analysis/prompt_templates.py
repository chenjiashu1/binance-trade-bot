"""
Prompt模板系统
提供各种分析场景的Prompt模板
"""

from typing import Dict, Any, Optional
import json

class PromptTemplates:
    """
    Prompt模板管理器
    """
    
    # 策略分析师Prompt模板
    STRATEGIST_PROMPT = """
【角色】你是资深数字货币策略分析师，拥有10年以上交易经验
【任务】基于市场数据和账户状态，生成专业的交易策略建议

【输入数据】
市场数据:
- 交易对: {symbol}
- 当前价格: {current_price}
- 24小时涨跌幅: {price_change_24h}%
- 趋势方向: {trend} (强度: {trend_strength}%)

技术指标:
- RSI: {rsi} ({rsi_status})
- MACD: {macd} (信号线: {signal}, 柱状图: {histogram}, 交叉信号: {macd_crossover})
- 移动均线: MA20={ma20}, MA50={ma50}, MA200={ma200}
- 布林带: 上轨={bb_upper}, 中轨={bb_middle}, 下轨={bb_lower}, 价格位置: {bb_position}
- ATR: {atr}

成交量:
- 24小时成交量: {volume_24h}
- 成交量趋势: {volume_trend}

【账户状态】
- 总资产(USDT): {total_assets}
- USDT余额: {usdt_balance}
- 当前持仓: {current_positions}
- 交易胜率: {win_rate}%
- 最近30天交易次数: {total_trades}

【分析要求】
请基于以上信息，从以下维度进行分析：

1. 趋势判断
- 短期(1-4小时)趋势方向和强度
- 中期(1-7天)趋势方向和强度
- 趋势的可靠性评估

2. 关键价位识别
- 重要支撑位(至少2个)
- 重要阻力位(至少2个)
- 关键突破位

3. 风险收益评估
- 潜在上涨空间
- 潜在下跌空间
- 风险收益比

4. 仓位管理建议
- 建议仓位比例(占总资金百分比)
- 单笔最大止损金额
- 加仓/减仓时机

5. 入场时机
- 理想入场价格区间
- 等待的确认信号
- 不适合入场的情况

【输出格式】
请使用JSON格式输出，包含以下字段：
{{
    "symbol": "交易对",
    "analysis_time": "分析时间",
    "trend_analysis": {{
        "short_term_trend": "up/down/sideways",
        "short_term_strength": 0-100,
        "medium_term_trend": "up/down/sideways",
        "medium_term_strength": 0-100,
        "trend_confidence": 0-100
    }},
    "key_levels": {{
        "support_levels": [价格1, 价格2],
        "resistance_levels": [价格1, 价格2],
        "breakout_level": 价格
    }},
    "risk_reward": {{
        "upside_potential": "百分比",
        "downside_risk": "百分比",
        "risk_reward_ratio": 数值
    }},
    "position_sizing": {{
        "recommended_position_percent": 百分比,
        "max_stop_loss_usdt": USDT金额,
        "add_position_condition": "条件描述",
        "reduce_position_condition": "条件描述"
    }},
    "entry_timing": {{
        "ideal_entry_range": "价格区间",
        "confirmation_signals": ["信号1", "信号2"],
        "avoid_entry_conditions": ["条件1", "条件2"]
    }},
    "overall_bias": "bullish/bearish/neutral",
    "confidence_score": 0-100,
    "rationale": "分析理由总结(不超过300字)"
}}

注意：
- 所有数值请使用合理的浮点数或整数
- 确保JSON格式正确，没有多余的逗号
- 分析要客观，基于数据，避免主观臆断
- 必须包含止损建议
    """
    
    # 技术分析师Prompt模板
    TECHNICAL_PROMPT = """
【角色】你是技术分析专家，专注于图表模式和指标信号
【任务】基于多时间框架技术分析，生成交易信号

【输入数据】
交易对: {symbol}
当前价格: {current_price}

多时间框架数据:

1小时图:
- 趋势: {trend_1h} (强度: {trend_strength_1h}%)
- RSI: {rsi_1h} ({rsi_status_1h})
- MACD: {macd_1h}, Signal: {signal_1h}, Histogram: {histogram_1h}
- MA20: {ma20_1h}, MA50: {ma50_1h}
- 布林带: 上轨={bb_upper_1h}, 中轨={bb_middle_1h}, 下轨={bb_lower_1h}

4小时图:
- 趋势: {trend_4h} (强度: {trend_strength_4h}%)
- RSI: {rsi_4h} ({rsi_status_4h})
- MACD: {macd_4h}, Signal: {signal_4h}, Histogram: {histogram_4h}
- MA20: {ma20_4h}, MA50: {ma50_4h}, MA200: {ma200_4h}
- 布林带: 上轨={bb_upper_4h}, 中轨={bb_middle_4h}, 下轨={bb_lower_4h}

日线图:
- 趋势: {trend_1d} (强度: {trend_strength_1d}%)
- RSI: {rsi_1d} ({rsi_status_1d})
- MACD: {macd_1d}, Signal: {signal_1d}, Histogram: {histogram_1d}
- MA20: {ma20_1d}, MA50: {ma50_1d}, MA200: {ma200_1d}
- 布林带: 上轨={bb_upper_1d}, 中轨={bb_middle_1d}, 下轨={bb_lower_1d}

【分析要求】

1. 多时间框架分析
- 各时间框架趋势一致性
- 主要趋势方向（以较高时间框架为准）
- 短期回调机会

2. 指标信号分析
- RSI超买/超卖情况
- MACD交叉信号
- 均线支撑/阻力
- 布林带突破信号

3. 形态识别
- 当前价格形态（头肩顶/底、三角形、旗形等）
- 关键支撑/阻力位
- 趋势线分析

4. 交易信号生成
- 买入信号（强烈/中等/微弱/无）
- 卖出信号（强烈/中等/微弱/无）
- 持仓建议

【输出格式】
{{
    "symbol": "交易对",
    "analysis_time": "分析时间",
    "timeframe_analysis": {{
        "1h": {{
            "trend": "趋势方向",
            "strength": 强度,
            "bias": "bullish/bearish/neutral"
        }},
        "4h": {{
            "trend": "趋势方向",
            "strength": 强度,
            "bias": "bullish/bearish/neutral"
        }},
        "1d": {{
            "trend": "趋势方向",
            "strength": 强度,
            "bias": "bullish/bearish/neutral"
        }}
    }},
    "signal_strength": {{
        "bullish_signals": [
            {{"indicator": "指标名称", "strength": "strong/medium/weak", "value": 数值}}
        ],
        "bearish_signals": [
            {{"indicator": "指标名称", "strength": "strong/medium/weak", "value": 数值}}
        ]
    }},
    "patterns": {{
        "identified_patterns": ["形态1", "形态2"],
        "pattern_confidence": 0-100
    }},
    "key_levels": {{
        "immediate_support": 价格,
        "major_support": 价格,
        "immediate_resistance": 价格,
        "major_resistance": 价格
    }},
    "trading_signals": {{
        "buy_signal": "strong/medium/weak/none",
        "sell_signal": "strong/medium/weak/none",
        "recommendation": "buy/sell/hold/wait",
        "entry_price": 建议入场价,
        "take_profit_levels": [目标1, 目标2, 目标3],
        "stop_loss_level": 止损价
    }},
    "confidence_score": 0-100,
    "notes": "重要注意事项"
}}
    """
    
    # 风险评估师Prompt模板
    RISK_PROMPT = """
【角色】你是严格的风险控制官，专注于资金安全
【任务】评估交易风险并提供风险控制建议

【输入数据】
交易信息:
- 交易对: {symbol}
- 当前价格: {current_price}
- 建议仓位: {position_size}% ({position_value} USDT)
- 建议入场价: {entry_price}
- 建议止损价: {stop_loss_price}
- 建议止盈价: {take_profit_price}

市场风险因素:
- 24小时涨跌幅: {price_change_24h}%
- ATR(波动率): {atr}
- 近期最大单日涨跌幅: {max_daily_change}%
- 成交量异常: {volume_anomaly}

账户信息:
- 总资产: {total_assets} USDT
- USDT余额: {usdt_balance} USDT
- 当前持仓数量: {open_positions} 个
- 最近30天最大回撤: {max_drawdown_30d}%
- 每日最大亏损限制: {max_daily_loss}%

【风险评估维度】

1. 单笔交易风险
- 潜在亏损金额(USDT)
- 潜在亏损比例(占总资金)
- 风险是否在可接受范围内

2. 账户整体风险
- 总持仓风险度
- 单一资产集中度风险
- 行业/市场风险暴露

3. 市场环境风险
- 当前市场波动率水平
- 流动性风险
- 黑天鹅事件概率

4. 风险控制建议
- 是否接受该交易
- 仓位调整建议
- 止损设置建议
- 应急退出方案

【输出格式】
{{
    "symbol": "交易对",
    "assessment_time": "评估时间",
    "single_trade_risk": {{
        "potential_loss_usdt": 潜在亏损金额,
        "potential_loss_percent": 潜在亏损百分比,
        "risk_level": "low/medium/high/extreme",
        "is_acceptable": true/false
    }},
    "portfolio_risk": {{
        "total_exposure_percent": 总持仓百分比,
        "max_single_exposure_percent": 单一资产最大百分比,
        "risk_concentration": "low/medium/high",
        "diversification_score": 0-100
    }},
    "market_environment_risk": {{
        "volatility_level": "low/medium/high/extreme",
        "liquidity_risk": "low/medium/high",
        "black_swan_risk": "low/medium/high",
        "overall_market_risk": "low/medium/high"
    }},
    "risk_metrics": {{
        "risk_of_ruin": 破产风险概率(%),
        "expected_shortfall": 预期亏损,
        "var_95": 95%置信度VaR,
        "calmar_ratio": Calmar比率
    }},
    "risk_control_recommendations": {{
        "accept_trade": true/false,
        "recommended_position_size": 建议仓位百分比,
        "recommended_stop_loss": 建议止损价,
        "trailing_stop_recommendation": "建议描述",
        "emergency_exit_plan": "应急方案描述",
        "additional_controls": ["控制措施1", "控制措施2"]
    }},
    "risk_score": 0-100 (越高风险越大),
    "risk_summary": "风险总结(不超过200字)"
}}

注意:
- 必须基于数据进行客观评估
- 当风险过高时，建议拒绝交易或减小仓位
- 所有建议必须符合风险控制规则
    """
    
    def __init__(self):
        pass
    
    def get_strategist_prompt(self, data: Dict[str, Any]) -> str:
        """
        获取策略分析师Prompt
        
        Args:
            data: 输入数据字典
            
        Returns:
            格式化后的Prompt
        """
        return self.STRATEGIST_PROMPT.format(
            symbol=data.get("symbol", "BTCUSDT"),
            current_price=data.get("current_price", 0),
            price_change_24h=data.get("price_change_24h", 0),
            trend=data.get("trend", "sideways"),
            trend_strength=data.get("trend_strength", 0),
            rsi=data.get("rsi", 50),
            rsi_status=data.get("rsi_status", "neutral"),
            macd=data.get("macd", 0),
            signal=data.get("signal", 0),
            histogram=data.get("histogram", 0),
            macd_crossover=data.get("macd_crossover", "none"),
            ma20=data.get("ma20", 0),
            ma50=data.get("ma50", 0),
            ma200=data.get("ma200", 0),
            bb_upper=data.get("bb_upper", 0),
            bb_middle=data.get("bb_middle", 0),
            bb_lower=data.get("bb_lower", 0),
            bb_position=data.get("bb_position", "inside"),
            atr=data.get("atr", 0),
            volume_24h=data.get("volume_24h", 0),
            volume_trend=data.get("volume_trend", "stable"),
            total_assets=data.get("total_assets", 0),
            usdt_balance=data.get("usdt_balance", 0),
            current_positions=data.get("current_positions", "无"),
            win_rate=data.get("win_rate", 0),
            total_trades=data.get("total_trades", 0)
        )
    
    def get_technical_prompt(self, data: Dict[str, Any]) -> str:
        """
        获取技术分析师Prompt
        
        Args:
            data: 输入数据字典
            
        Returns:
            格式化后的Prompt
        """
        return self.TECHNICAL_PROMPT.format(
            symbol=data.get("symbol", "BTCUSDT"),
            current_price=data.get("current_price", 0),
            
            # 1小时图
            trend_1h=data.get("trend_1h", "sideways"),
            trend_strength_1h=data.get("trend_strength_1h", 0),
            rsi_1h=data.get("rsi_1h", 50),
            rsi_status_1h=data.get("rsi_status_1h", "neutral"),
            macd_1h=data.get("macd_1h", 0),
            signal_1h=data.get("signal_1h", 0),
            histogram_1h=data.get("histogram_1h", 0),
            ma20_1h=data.get("ma20_1h", 0),
            ma50_1h=data.get("ma50_1h", 0),
            bb_upper_1h=data.get("bb_upper_1h", 0),
            bb_middle_1h=data.get("bb_middle_1h", 0),
            bb_lower_1h=data.get("bb_lower_1h", 0),
            
            # 4小时图
            trend_4h=data.get("trend_4h", "sideways"),
            trend_strength_4h=data.get("trend_strength_4h", 0),
            rsi_4h=data.get("rsi_4h", 50),
            rsi_status_4h=data.get("rsi_status_4h", "neutral"),
            macd_4h=data.get("macd_4h", 0),
            signal_4h=data.get("signal_4h", 0),
            histogram_4h=data.get("histogram_4h", 0),
            ma20_4h=data.get("ma20_4h", 0),
            ma50_4h=data.get("ma50_4h", 0),
            ma200_4h=data.get("ma200_4h", 0),
            bb_upper_4h=data.get("bb_upper_4h", 0),
            bb_middle_4h=data.get("bb_middle_4h", 0),
            bb_lower_4h=data.get("bb_lower_4h", 0),
            
            # 日线图
            trend_1d=data.get("trend_1d", "sideways"),
            trend_strength_1d=data.get("trend_strength_1d", 0),
            rsi_1d=data.get("rsi_1d", 50),
            rsi_status_1d=data.get("rsi_status_1d", "neutral"),
            macd_1d=data.get("macd_1d", 0),
            signal_1d=data.get("signal_1d", 0),
            histogram_1d=data.get("histogram_1d", 0),
            ma20_1d=data.get("ma20_1d", 0),
            ma50_1d=data.get("ma50_1d", 0),
            ma200_1d=data.get("ma200_1d", 0),
            bb_upper_1d=data.get("bb_upper_1d", 0),
            bb_middle_1d=data.get("bb_middle_1d", 0),
            bb_lower_1d=data.get("bb_lower_1d", 0)
        )
    
    def get_risk_prompt(self, data: Dict[str, Any]) -> str:
        """
        获取风险评估师Prompt
        
        Args:
            data: 输入数据字典
            
        Returns:
            格式化后的Prompt
        """
        return self.RISK_PROMPT.format(
            symbol=data.get("symbol", "BTCUSDT"),
            current_price=data.get("current_price", 0),
            position_size=data.get("position_size", 0),
            position_value=data.get("position_value", 0),
            entry_price=data.get("entry_price", 0),
            stop_loss_price=data.get("stop_loss_price", 0),
            take_profit_price=data.get("take_profit_price", 0),
            
            price_change_24h=data.get("price_change_24h", 0),
            atr=data.get("atr", 0),
            max_daily_change=data.get("max_daily_change", 0),
            volume_anomaly=data.get("volume_anomaly", "否"),
            
            total_assets=data.get("total_assets", 0),
            usdt_balance=data.get("usdt_balance", 0),
            open_positions=data.get("open_positions", 0),
            max_drawdown_30d=data.get("max_drawdown_30d", 0),
            max_daily_loss=data.get("max_daily_loss", 5)
        )
    
    def validate_json_output(self, json_str: str) -> Optional[Dict]:
        """
        验证并解析JSON输出
        
        Args:
            json_str: JSON字符串
            
        Returns:
            解析后的字典或None
        """
        try:
            # 清理可能的markdown标记
            json_str = json_str.strip()
            if json_str.startswith("```json"):
                json_str = json_str[7:]
            if json_str.startswith("```"):
                json_str = json_str[3:]
            if json_str.endswith("```"):
                json_str = json_str[:-3]
            json_str = json_str.strip()
            
            return json.loads(json_str)
            
        except json.JSONDecodeError as e:
            return None
        except Exception as e:
            return None
