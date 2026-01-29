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
【角色】你是一位专业的技术分析师和交易顾问，专注于图表模式和指标信号
【任务】请基于以下三个时间维度（1小时/4小时/日线）的K线图表数据和技术指标，提供可操作的交易见解。

=== 分析背景 ===
交易标的：{symbol}
分析时间（UTC）：{current_time_utc}

=== 当前市场数据 ===
当前价格： $ {current_price}
24小时涨跌幅：{change_24h}%
24小时成交量： $ {volume_24h}
未平仓合约（Open Interest）： $ {open_interest}
资金费率：{funding_rate}%
佣金费率：{commission_rates}

=== 1小时图数据（最近20根K线） ===
{klines_summary_1h}

=== 1小时图技术指标 ===
{indicators_summary_1h}

=== 4小时图数据（最近20根K线） ===
{klines_summary_4h}

=== 4小时图技术指标 ===
{indicators_summary_4h}

=== 日线图数据（最近20根K线） ===
{klines_summary_1d}

=== 日线图技术指标 ===
{indicators_summary_1d}

=== 市场资金流指标 ===
{flow_indicators_summary}

=== 持仓情况 ===
{positions_summary}

=== 用户问题（如有） ===
{user_message}

=== 分析要求 ===
请严格基于上述三个时间维度的数据，完成以下分析，并以 **Markdown 格式** 输出正文内容，**同时在最后附上一个完整的 JSON 结构化结果**（格式见下方“输出格式”）。

## 📊 多时间框架趋势分析
- **日线图（长期趋势）**：判断趋势方向与强度，评估长期支撑/阻力位
- **4小时图（中期趋势）**：判断趋势方向与强度，评估中期支撑/阻力位
- **1小时图（短期趋势）**：判断趋势方向与强度，评估短期支撑/阻力位
- **趋势一致性分析**：三个时间框架是否形成共振？是否存在背离？
- **主导趋势判断**：以日线图和4小时图为准，1小时图用于寻找入场时机

## 🎯 关键价格位（多时间框架综合）
- **主要支撑位**：基于日线/4小时图的重要支撑（至少2个）
- **主要阻力位**：基于日线/4小时图的重要阻力（至少2个）
- **短期支撑/阻力**：基于1小时图的即时支撑/阻力
- **关键突破位**：结合布林带、均线、历史高低点的重要价位

## 📈 技术信号解读（多时间框架对比）
- **RSI分析**：各时间框架的RSI状态，是否存在超买/超卖？是否有背离？
- **MACD分析**：各时间框架的MACD信号，是否出现金叉/死叉？动能如何变化？
- **均线系统**：各时间框架的均线支撑/阻力作用，均线排列形态
- **布林带分析**：各时间框架的布林带状态，价格位置

## 🔍 图表形态识别
- **日线图形态**：是否存在经典技术形态（头肩顶/底、三角形、旗形等）
- **4小时图形态**：是否存在经典技术形态
- **1小时图形态**：是否存在经典技术形态
- **形态确认**：形态置信度如何？是否有量能配合？

## 💡 交易建议（基于多时间框架共振）
- **推荐操作**：做多 / 做空 / 持有 / 观望
- **入场条件**：需要满足哪些时间框架的信号？
- **入场区间**：建议价格范围（基于1小时图）
- **止损位**：控制风险的止损价格（基于日线/4小时图支撑）
- **止盈目标**：至少两个层级（短期目标基于1小时图，长期目标基于日线图）
- **仓位建议**：根据多时间框架信号的强度，建议仓位比例

## ⚠️ 风险提示
- **时间框架冲突**：如果不同时间框架信号不一致，如何处理？
- **当前市场波动性评估**：基于各时间框架的ATR和价格波动
- **需警惕的主要风险**：如指标失效、流动性不足、外部事件等
- **分析失效条件**：哪些价格行为或数据将导致本分析结论失效？

{additional_instructions}

**重要原则**：
- 所有结论必须基于提供的三个时间维度的数据，不得臆测。
- 优先考虑较高时间框架（日线/4小时）的信号，1小时图用于精确入场时机。
- 多时间框架共振时，信号强度更高，可靠性更强。
- 同时考虑看涨与看跌情景，保持中立客观。
- 若数据不足以支持明确信号，请明确说明“无明确信号”或“建议观望”。
- 必须考虑佣金费率对交易成本的影响。
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
            # === 分析背景 ===
            symbol=data.get("symbol", "BTCUSDT"),
            current_time_utc=data.get("current_time_utc", "2024-01-01 00:00:00 UTC"),
            
            # === 当前市场数据 ===
            current_price=data.get("current_price", 0),
            change_24h=data.get("change_24h", 0),
            volume_24h=data.get("volume_24h", 0),
            open_interest=data.get("open_interest", "N/A"),
            funding_rate=data.get("funding_rate", "N/A"),
            commission_rates=data.get("commission_rates", {"maker": 0.001, "taker": 0.001}),
            
            # === 三个时间维度的K线数据 ===
            klines_summary_1h=data.get("klines_summary_1h", "暂无1小时K线数据"),
            klines_summary_4h=data.get("klines_summary_4h", "暂无4小时K线数据"),
            klines_summary_1d=data.get("klines_summary_1d", "暂无日线K线数据"),
            
            # === 三个时间维度的技术指标 ===
            indicators_summary_1h=data.get("indicators_summary_1h", "暂无1小时指标数据"),
            indicators_summary_4h=data.get("indicators_summary_4h", "暂无4小时指标数据"),
            indicators_summary_1d=data.get("indicators_summary_1d", "暂无日线指标数据"),
            
            # === 市场资金流指标 ===
            flow_indicators_summary=data.get("flow_indicators_summary", "暂无资金流数据"),
            
            # === 持仓情况 ===
            positions_summary=data.get("positions_summary", "暂无持仓数据"),
            
            # === 用户问题（如有） ===
            user_message=data.get("user_message", "无"),
            
            # === 额外分析要求 ===
            additional_instructions=data.get("additional_instructions", "")
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
