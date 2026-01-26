"""
决策聚合模块
聚合多个模型的分析结果，生成最终决策
"""

import json
import time
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from enum import Enum

from ..utils.logger import LoggerMixin
from ..utils.exceptions import DecisionError
from ..utils.config_loader import ConfigLoader

class AgreementLevel(Enum):
    """一致性级别"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    CONFLICT = "conflict"

class ActionType(Enum):
    """交易动作类型"""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    WAIT = "wait"
    BUY_LIMIT = "buy_limit"
    SELL_LIMIT = "sell_limit"

class DecisionAggregator(LoggerMixin):
    """
    决策聚合器
    聚合多个LLM模型的分析结果，生成最终交易决策
    """
    
    def __init__(self, config: ConfigLoader):
        super().__init__()
        self.config = config
        self.model_weights = {}
    
    def set_model_weights(self, weights: Dict[str, float]):
        """
        设置模型权重
        
        Args:
            weights: 模型权重字典
        """
        self.model_weights = weights
    
    def aggregate_decisions(
        self,
        model_outputs: Dict[str, Dict[str, Any]],
        account_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        聚合多个模型的决策结果
        
        Args:
            model_outputs: 各模型的输出结果
            account_info: 账户信息
            
        Returns:
            最终决策
        """
        try:
            if not model_outputs:
                raise DecisionError("没有模型输出", stage="aggregate")
            
            self.logger.info(f"开始聚合 {len(model_outputs)} 个模型的决策...")
            
            # 1. 冲突检测
            conflicts = self._detect_conflicts(model_outputs)
            
            # 2. 加权投票
            weighted_result = self._weighted_voting(model_outputs)
            
            # 3. 一致性分析
            agreement = self._analyze_agreement(model_outputs)
            
            # 4. 风险过滤
            risk_filtered = self._risk_filter(weighted_result, account_info)
            
            # 5. 生成最终决策
            final_decision = self._generate_final_decision(
                risk_filtered,
                model_outputs,
                conflicts,
                agreement
            )
            
            self.logger.info("决策聚合完成")
            return final_decision
            
        except Exception as e:
            raise DecisionError(f"决策聚合失败: {e}", stage="aggregate")
    
    def _detect_conflicts(self, model_outputs: Dict[str, Dict]) -> List[str]:
        """
        检测模型间的冲突
        
        Args:
            model_outputs: 模型输出
            
        Returns:
            冲突点列表
        """
        conflicts = []
        
        if len(model_outputs) < 2:
            return conflicts
        
        # 提取关键决策点
        decisions = []
        for model_name, output in model_outputs.items():
            if output.get("success", True) is False:
                continue
            
            decision = {
                "model": model_name,
                "bias": output.get("overall_bias", "neutral"),
                "position_size": output.get("position_sizing", {}).get("recommended_position_percent", 0),
                "entry_price": output.get("entry_timing", {}).get("ideal_entry_range", ""),
                "stop_loss": output.get("trading_signals", {}).get("stop_loss_level", 0)
            }
            decisions.append(decision)
        
        if len(decisions) < 2:
            return conflicts
        
        # 检测bias冲突
        biases = [d["bias"] for d in decisions]
        if len(set(biases)) > 1:
            conflicts.append("bias")
            self.logger.warning(f"模型bias冲突: {biases}")
        
        # 检测仓位冲突
        positions = [d["position_size"] for d in decisions if d["position_size"] > 0]
        if positions:
            max_pos = max(positions)
            min_pos = min(positions)
            if max_pos / min_pos > 2 and min_pos > 0:
                conflicts.append("position_size")
                self.logger.warning(f"仓位建议差异较大: min={min_pos}, max={max_pos}")
        
        return conflicts
    
    def _weighted_voting(self, model_outputs: Dict[str, Dict]) -> Dict[str, Any]:
        """
        加权投票算法
        
        Args:
            model_outputs: 模型输出
            
        Returns:
            加权结果
        """
        weighted_result = {
            "bias": "neutral",
            "position_size": 0,
            "entry_price": 0,
            "stop_loss": 0,
            "take_profit": [],
            "confidence_score": 0
        }
        
        total_weight = 0
        
        for model_name, output in model_outputs.items():
            if output.get("success", True) is False:
                continue
            
            weight = self.model_weights.get(model_name, 1.0)
            total_weight += weight
            
            # Bias加权
            bias = output.get("overall_bias", "neutral")
            if bias == "bullish":
                weighted_result["bias"] = "bullish" if weighted_result["bias"] != "bearish" else "neutral"
            elif bias == "bearish":
                weighted_result["bias"] = "bearish" if weighted_result["bias"] != "bullish" else "neutral"
            
            # 仓位加权
            position_size = output.get("position_sizing", {}).get("recommended_position_percent", 0)
            weighted_result["position_size"] += position_size * weight
            
            # 入场价加权
            entry_range = output.get("entry_timing", {}).get("ideal_entry_range", "")
            if entry_range:
                try:
                    if "-" in entry_range:
                        low, high = entry_range.split("-")
                        entry_price = (float(low.strip()) + float(high.strip())) / 2
                    else:
                        entry_price = float(entry_range.strip())
                    weighted_result["entry_price"] += entry_price * weight
                except:
                    pass
            
            # 止损价加权
            stop_loss = output.get("trading_signals", {}).get("stop_loss_level", 0)
            if stop_loss > 0:
                weighted_result["stop_loss"] += stop_loss * weight
            
            # 止盈价加权
            take_profits = output.get("trading_signals", {}).get("take_profit_levels", [])
            if take_profits:
                for tp in take_profits[:3]:  # 最多取3个
                    weighted_result["take_profit"].append((tp, weight))
            
            # 信心度加权
            confidence = output.get("confidence_score", 0)
            weighted_result["confidence_score"] += confidence * weight
        
        # 归一化
        if total_weight > 0:
            weighted_result["position_size"] = round(weighted_result["position_size"] / total_weight, 2)
            if weighted_result["entry_price"] > 0:
                weighted_result["entry_price"] = round(weighted_result["entry_price"] / total_weight, 4)
            if weighted_result["stop_loss"] > 0:
                weighted_result["stop_loss"] = round(weighted_result["stop_loss"] / total_weight, 4)
            weighted_result["confidence_score"] = round(weighted_result["confidence_score"] / total_weight, 2)
        
        # 处理止盈价
        if weighted_result["take_profit"]:
            tp_dict = {}
            for tp, weight in weighted_result["take_profit"]:
                if tp in tp_dict:
                    tp_dict[tp] += weight
                else:
                    tp_dict[tp] = weight
            
            sorted_tps = sorted(tp_dict.items(), key=lambda x: x[0])
            weighted_result["take_profit"] = [tp for tp, _ in sorted_tps[:3]]
        
        return weighted_result
    
    def _analyze_agreement(self, model_outputs: Dict[str, Dict]) -> Dict[str, Any]:
        """
        分析模型一致性
        
        Args:
            model_outputs: 模型输出
            
        Returns:
            一致性分析结果
        """
        if len(model_outputs) < 2:
            return {
                "agreement_level": AgreementLevel.HIGH.value,
                "agreement_score": 100
            }
        
        biases = []
        confidences = []
        
        for output in model_outputs.values():
            if output.get("success", True) is False:
                continue
            
            biases.append(output.get("overall_bias", "neutral"))
            confidences.append(output.get("confidence_score", 0))
        
        if not biases:
            return {
                "agreement_level": AgreementLevel.LOW.value,
                "agreement_score": 0
            }
        
        # 计算一致性分数
        bullish_count = biases.count("bullish")
        bearish_count = biases.count("bearish")
        neutral_count = biases.count("neutral")
        
        total = len(biases)
        max_count = max(bullish_count, bearish_count, neutral_count)
        agreement_score = (max_count / total) * 100
        
        # 确定一致性级别
        if agreement_score >= 80:
            level = AgreementLevel.HIGH.value
        elif agreement_score >= 50:
            level = AgreementLevel.MEDIUM.value
        elif agreement_score >= 30:
            level = AgreementLevel.LOW.value
        else:
            level = AgreementLevel.CONFLICT.value
        
        return {
            "agreement_level": level,
            "agreement_score": round(agreement_score, 2),
            "bias_distribution": {
                "bullish": bullish_count,
                "bearish": bearish_count,
                "neutral": neutral_count
            },
            "avg_confidence": round(sum(confidences) / len(confidences), 2) if confidences else 0
        }
    
    def _risk_filter(
        self,
        decision: Dict[str, Any],
        account_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        风险过滤
        
        Args:
            decision: 决策结果
            account_info: 账户信息
            
        Returns:
            风险过滤后的决策
        """
        risk_config = self.config.get("analysis.risk_limits", {})
        max_position_percent = risk_config.get("max_position_percent", 20)
        max_daily_loss = risk_config.get("max_daily_loss", 5)
        
        # 限制仓位大小
        if decision["position_size"] > max_position_percent:
            self.logger.warning(
                f"仓位超过限制: {decision['position_size']}% -> {max_position_percent}%"
            )
            decision["position_size"] = max_position_percent
        
        # 计算实际仓位价值
        total_assets = account_info.get("total_assets_usdt", 10000)
        position_value = total_assets * decision["position_size"] / 100
        decision["position_value_usdt"] = round(position_value, 2)
        
        # 计算潜在风险
        if decision["entry_price"] > 0 and decision["stop_loss"] > 0:
            risk_percent = abs(decision["entry_price"] - decision["stop_loss"]) / decision["entry_price"] * 100
            risk_usdt = position_value * risk_percent / 100
            
            decision["risk_percent"] = round(risk_percent, 2)
            decision["risk_usdt"] = round(risk_usdt, 2)
            
            # 检查风险是否超过每日限制
            daily_loss_limit = total_assets * max_daily_loss / 100
            if risk_usdt > daily_loss_limit:
                self.logger.warning(
                    f"风险超过每日限制: {risk_usdt} USDT -> {daily_loss_limit} USDT"
                )
                # 调整仓位
                decision["position_size"] = round(
                    decision["position_size"] * daily_loss_limit / risk_usdt,
                    2
                )
                decision["position_value_usdt"] = round(
                    total_assets * decision["position_size"] / 100,
                    2
                )
        
        return decision
    
    def _generate_final_decision(
        self,
        weighted_result: Dict[str, Any],
        model_outputs: Dict[str, Dict],
        conflicts: List[str],
        agreement: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        生成最终决策
        
        Args:
            weighted_result: 加权结果
            model_outputs: 模型输出
            conflicts: 冲突点
            agreement: 一致性分析
            
        Returns:
            最终决策
        """
        # 确定交易动作
        bias = weighted_result["bias"]
        position_size = weighted_result["position_size"]
        
        if bias == "bullish" and position_size > 0:
            action = ActionType.BUY.value
        elif bias == "bearish" and position_size > 0:
            action = ActionType.SELL.value
        elif position_size == 0:
            action = ActionType.HOLD.value
        else:
            action = ActionType.WAIT.value
        
        final_decision = {
            "timestamp": int(time.time() * 1000),
            "datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "symbol": next(iter(model_outputs.values())).get("symbol", "unknown"),
            "final_decision": {
                "action": action,
                "bias": bias,
                "recommended_position_size_percent": position_size,
                "recommended_position_value_usdt": weighted_result.get("position_value_usdt", 0),
                "entry_price": weighted_result.get("entry_price", 0),
                "stop_loss": weighted_result.get("stop_loss", 0),
                "take_profit_levels": weighted_result.get("take_profit", []),
                "confidence_score": weighted_result.get("confidence_score", 0)
            },
            "model_consensus": {
                "agreement_level": agreement["agreement_level"],
                "agreement_score": agreement["agreement_score"],
                "bias_distribution": agreement["bias_distribution"],
                "avg_confidence": agreement["avg_confidence"],
                "conflicting_points": conflicts,
                "models_count": len(model_outputs),
                "details": model_outputs
            },
            "risk_assessment": {
                "risk_percent": weighted_result.get("risk_percent", 0),
                "risk_usdt": weighted_result.get("risk_usdt", 0),
                "position_risk": self._assess_position_risk(weighted_result),
                "recommended_capital_usage": f"{position_size}%"
            },
            "execution_plan": self._generate_execution_plan(weighted_result)
        }
        
        return final_decision
    
    def _assess_position_risk(self, decision: Dict[str, Any]) -> str:
        """
        评估仓位风险
        
        Args:
            decision: 决策结果
            
        Returns:
            风险级别
        """
        risk_percent = decision.get("risk_percent", 0)
        position_size = decision.get("position_size", 0)
        
        if risk_percent <= 1 or position_size <= 5:
            return "low"
        elif risk_percent <= 3 or position_size <= 15:
            return "medium"
        else:
            return "high"
    
    def _generate_execution_plan(self, decision: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成执行计划
        
        Args:
            decision: 决策结果
            
        Returns:
            执行计划
        """
        action = decision.get("action", "hold")
        entry_price = decision.get("entry_price", 0)
        stop_loss = decision.get("stop_loss", 0)
        take_profits = decision.get("take_profit", [])
        
        plan = {
            "action": action,
            "entry_condition": "",
            "exit_conditions": [],
            "notes": []
        }
        
        if action == "buy":
            plan["entry_condition"] = f"价格接近 {entry_price} 且确认看涨信号"
            if stop_loss > 0:
                plan["exit_conditions"].append(f"止损: 价格跌破 {stop_loss}")
            for i, tp in enumerate(take_profits[:3], 1):
                plan["exit_conditions"].append(f"止盈 {i}: 价格达到 {tp}")
            plan["notes"].append("建议分批建仓")
            plan["notes"].append("严格执行止损")
            
        elif action == "sell":
            plan["entry_condition"] = f"价格接近 {entry_price} 且确认看跌信号"
            if stop_loss > 0:
                plan["exit_conditions"].append(f"止损: 价格突破 {stop_loss}")
            for i, tp in enumerate(take_profits[:3], 1):
                plan["exit_conditions"].append(f"止盈 {i}: 价格达到 {tp}")
            plan["notes"].append("注意空头风险")
            
        elif action == "hold":
            plan["entry_condition"] = "继续持有"
            plan["notes"].append("密切关注价格变化")
            
        elif action == "wait":
            plan["entry_condition"] = "等待更明确的信号"
            plan["notes"].append("当前信号不明确")
            plan["notes"].append("等待市场方向确认")
        
        return plan
