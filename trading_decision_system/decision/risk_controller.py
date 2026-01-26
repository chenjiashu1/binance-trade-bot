"""
风险控制模块
提供交易风险评估和控制功能
"""

import json
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from enum import Enum

from ..utils.logger import LoggerMixin
from ..utils.exceptions import RiskControlError
from ..utils.config_loader import ConfigLoader

class RiskLevel(Enum):
    """风险级别"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EXTREME = "extreme"

class RiskController(LoggerMixin):
    """
    风险控制器
    评估和控制交易风险
    """
    
    def __init__(self, config: ConfigLoader):
        super().__init__()
        self.config = config
        self.daily_loss_tracker = {}
        self.position_limits = {}
        self._load_risk_config()
    
    def _load_risk_config(self):
        """加载风险配置"""
        risk_config = self.config.get("analysis.risk_limits", {})
        
        self.max_position_percent = risk_config.get("max_position_percent", 20)
        self.max_daily_loss = risk_config.get("max_daily_loss", 5)
        self.stop_loss_default = risk_config.get("stop_loss_default", 2)
        self.risk_free_rate = risk_config.get("risk_free_rate", 0.02)
        self.max_open_positions = risk_config.get("max_open_positions", 5)
        
        self.logger.info(f"风险配置加载完成: max_position={self.max_position_percent}%, max_daily_loss={self.max_daily_loss}%")
    
    def validate_trade(
        self,
        trade_info: Dict[str, Any],
        account_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        验证交易是否符合风险规则
        
        Args:
            trade_info: 交易信息
            account_info: 账户信息
            
        Returns:
            验证结果
        """
        try:
            validation = {
                "is_valid": True,
                "warnings": [],
                "errors": [],
                "suggestions": [],
                "risk_score": 0
            }
            
            # 1. 检查仓位大小
            position_check = self._check_position_size(trade_info, account_info)
            if not position_check["is_valid"]:
                validation["is_valid"] = False
                validation["errors"].extend(position_check["errors"])
            validation["warnings"].extend(position_check["warnings"])
            validation["suggestions"].extend(position_check["suggestions"])
            
            # 2. 检查止损设置
            sl_check = self._check_stop_loss(trade_info)
            if not sl_check["is_valid"]:
                validation["warnings"].append("建议设置止损")
            validation["suggestions"].extend(sl_check["suggestions"])
            
            # 3. 检查每日亏损
            daily_check = self._check_daily_loss(account_info)
            if not daily_check["is_valid"]:
                validation["is_valid"] = False
                validation["errors"].append("今日亏损已达上限")
            
            # 4. 检查持仓数量
            positions_check = self._check_open_positions(account_info)
            if not positions_check["is_valid"]:
                validation["warnings"].append("持仓数量较多，建议谨慎")
            
            # 5. 计算风险分数
            validation["risk_score"] = self._calculate_risk_score(
                trade_info, 
                account_info,
                validation
            )
            
            # 6. 确定风险级别
            validation["risk_level"] = self._get_risk_level(validation["risk_score"])
            
            return validation
            
        except Exception as e:
            raise RiskControlError(f"交易验证失败: {e}", risk_type="validation")
    
    def _check_position_size(
        self,
        trade_info: Dict[str, Any],
        account_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        检查仓位大小
        
        Args:
            trade_info: 交易信息
            account_info: 账户信息
            
        Returns:
            检查结果
        """
        result = {
            "is_valid": True,
            "warnings": [],
            "errors": [],
            "suggestions": []
        }
        
        position_size = trade_info.get("position_size", 0)
        total_assets = account_info.get("total_assets_usdt", 10000)
        
        if position_size > self.max_position_percent:
            result["is_valid"] = False
            result["errors"].append(
                f"仓位 {position_size}% 超过限制 {self.max_position_percent}%"
            )
            result["suggestions"].append(
                f"建议将仓位调整至 {self.max_position_percent}% 以下"
            )
        
        # 计算实际风险
        entry_price = trade_info.get("entry_price", 0)
        stop_loss = trade_info.get("stop_loss", 0)
        
        if entry_price > 0 and stop_loss > 0:
            risk_per_trade = abs(entry_price - stop_loss) / entry_price * position_size
            
            if risk_per_trade > self.max_daily_loss:
                result["warnings"].append(
                    f"单笔风险 {risk_per_trade:.2f}% 接近每日限制 {self.max_daily_loss}%"
                )
        
        return result
    
    def _check_stop_loss(self, trade_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        检查止损设置
        
        Args:
            trade_info: 交易信息
            
        Returns:
            检查结果
        """
        result = {
            "is_valid": True,
            "suggestions": []
        }
        
        stop_loss = trade_info.get("stop_loss", 0)
        entry_price = trade_info.get("entry_price", 0)
        
        if stop_loss <= 0:
            result["is_valid"] = False
            # 建议默认止损
            if entry_price > 0:
                suggested_sl = entry_price * (1 - self.stop_loss_default / 100)
                result["suggestions"].append(
                    f"建议设置止损价: {suggested_sl:.4f} (默认{self.stop_loss_default}%)"
                )
        
        return result
    
    def _check_daily_loss(self, account_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        检查每日亏损
        
        Args:
            account_info: 账户信息
            
        Returns:
            检查结果
        """
        result = {"is_valid": True}
        
        today = datetime.now().strftime("%Y-%m-%d")
        
        if today not in self.daily_loss_tracker:
            # 初始化今日追踪
            self.daily_loss_tracker[today] = {
                "start_balance": account_info.get("total_assets_usdt", 0),
                "current_balance": account_info.get("total_assets_usdt", 0),
                "max_balance": account_info.get("total_assets_usdt", 0),
                "min_balance": account_info.get("total_assets_usdt", 0),
                "total_loss": 0
            }
        
        tracker = self.daily_loss_tracker[today]
        current_balance = account_info.get("total_assets_usdt", 0)
        
        # 更新追踪数据
        tracker["current_balance"] = current_balance
        tracker["max_balance"] = max(tracker["max_balance"], current_balance)
        tracker["min_balance"] = min(tracker["min_balance"], current_balance)
        
        # 计算今日最大回撤
        if tracker["max_balance"] > 0:
            drawdown = (tracker["max_balance"] - current_balance) / tracker["max_balance"] * 100
            
            if drawdown >= self.max_daily_loss:
                result["is_valid"] = False
                self.logger.warning(
                    f"今日回撤 {drawdown:.2f}% 已达限制 {self.max_daily_loss}%"
                )
        
        return result
    
    def _check_open_positions(self, account_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        检查持仓数量
        
        Args:
            account_info: 账户信息
            
        Returns:
            检查结果
        """
        result = {"is_valid": True}
        
        open_positions = account_info.get("open_positions", 0)
        
        if open_positions >= self.max_open_positions:
            result["is_valid"] = False
            self.logger.warning(
                f"当前持仓 {open_positions} 个，已达限制 {self.max_open_positions} 个"
            )
        
        return result
    
    def _calculate_risk_score(
        self,
        trade_info: Dict[str, Any],
        account_info: Dict[str, Any],
        validation: Dict[str, Any]
    ) -> int:
        """
        计算风险分数
        
        Args:
            trade_info: 交易信息
            account_info: 账户信息
            validation: 验证结果
            
        Returns:
            风险分数 (0-100)
        """
        score = 0
        
        # 1. 仓位风险 (0-40分)
        position_size = trade_info.get("position_size", 0)
        position_risk = min(40, (position_size / self.max_position_percent) * 40)
        score += position_risk
        
        # 2. 止损风险 (0-20分)
        entry_price = trade_info.get("entry_price", 0)
        stop_loss = trade_info.get("stop_loss", 0)
        if entry_price > 0 and stop_loss > 0:
            risk_percent = abs(entry_price - stop_loss) / entry_price * 100
            if risk_percent > self.stop_loss_default * 2:
                score += 20
            elif risk_percent > self.stop_loss_default:
                score += 10
        else:
            score += 15  # 没有止损设置
        
        # 3. 账户风险 (0-20分)
        open_positions = account_info.get("open_positions", 0)
        if open_positions >= self.max_open_positions:
            score += 20
        elif open_positions >= self.max_open_positions * 0.8:
            score += 10
        
        # 4. 市场风险 (0-20分)
        price_change_24h = abs(trade_info.get("price_change_24h", 0))
        if price_change_24h > 10:
            score += 20
        elif price_change_24h > 5:
            score += 10
        
        # 5. 验证错误扣分
        if validation["errors"]:
            score += len(validation["errors"]) * 10
        
        return min(100, round(score))
    
    def _get_risk_level(self, score: int) -> str:
        """
        获取风险级别
        
        Args:
            score: 风险分数
            
        Returns:
            风险级别
        """
        if score <= 20:
            return RiskLevel.LOW.value
        elif score <= 50:
            return RiskLevel.MEDIUM.value
        elif score <= 80:
            return RiskLevel.HIGH.value
        else:
            return RiskLevel.EXTREME.value
    
    def calculate_var(
        self,
        price_data: List[float],
        confidence_level: float = 0.95,
        position_value: float = 10000
    ) -> Dict[str, float]:
        """
        计算风险价值(VaR)
        
        Args:
            price_data: 价格数据
            confidence_level: 置信水平
            position_value: 仓位价值
            
        Returns:
            VaR计算结果
        """
        if len(price_data) < 2:
            return {"var": 0, "cvar": 0}
        
        # 计算收益率
        returns = []
        for i in range(1, len(price_data)):
            ret = (price_data[i] - price_data[i-1]) / price_data[i-1]
            returns.append(ret)
        
        if not returns:
            return {"var": 0, "cvar": 0}
        
        # 排序收益率
        sorted_returns = sorted(returns)
        
        # 计算VaR
        var_index = int(len(sorted_returns) * (1 - confidence_level))
        var = abs(sorted_returns[var_index]) if var_index < len(sorted_returns) else 0
        
        # 计算CVaR (条件风险价值)
        tail_returns = sorted_returns[:var_index+1]
        cvar = abs(sum(tail_returns) / len(tail_returns)) if tail_returns else 0
        
        return {
            "var": round(var * position_value, 2),
            "cvar": round(cvar * position_value, 2),
            "var_percent": round(var * 100, 4),
            "cvar_percent": round(cvar * 100, 4)
        }
    
    def calculate_calmar_ratio(
        self,
        returns: List[float],
        period: str = "yearly"
    ) -> float:
        """
        计算Calmar比率
        
        Args:
            returns: 收益率列表
            period: 周期
            
        Returns:
            Calmar比率
        """
        if not returns:
            return 0
        
        # 计算年化收益率
        total_return = 1
        for ret in returns:
            total_return *= (1 + ret)
        
        if period == "yearly":
            periods = len(returns) / 365
        elif period == "monthly":
            periods = len(returns) / 30
        else:
            periods = 1
        
        if periods <= 0:
            return 0
        
        annualized_return = (total_return ** (1 / periods)) - 1
        
        # 计算最大回撤
        max_return = 0
        max_drawdown = 0
        current_return = 1
        
        for ret in returns:
            current_return *= (1 + ret)
            max_return = max(max_return, current_return)
            drawdown = (max_return - current_return) / max_return
            max_drawdown = max(max_drawdown, drawdown)
        
        if max_drawdown <= 0:
            return float('inf')
        
        # Calmar比率 = 年化收益率 / 最大回撤
        calmar_ratio = annualized_return / max_drawdown
        
        return round(calmar_ratio, 4)
    
    def generate_risk_report(
        self,
        trade_info: Dict[str, Any],
        account_info: Dict[str, Any],
        price_data: Optional[List[float]] = None
    ) -> Dict[str, Any]:
        """
        生成风险报告
        
        Args:
            trade_info: 交易信息
            account_info: 账户信息
            price_data: 价格数据
            
        Returns:
            风险报告
        """
        try:
            # 验证交易
            validation = self.validate_trade(trade_info, account_info)
            
            # 计算VaR
            var_result = {}
            if price_data and len(price_data) >= 10:
                position_value = account_info.get("total_assets_usdt", 10000) * trade_info.get("position_size", 0) / 100
                var_result = self.calculate_var(price_data, position_value=position_value)
            
            # 生成报告
            report = {
                "timestamp": int(time.time() * 1000),
                "datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "symbol": trade_info.get("symbol", "unknown"),
                "validation_result": validation,
                "var_analysis": var_result,
                "risk_summary": self._generate_risk_summary(validation, var_result),
                "recommendations": self._generate_recommendations(validation)
            }
            
            return report
            
        except Exception as e:
            raise RiskControlError(f"风险报告生成失败: {e}", risk_type="report")
    
    def _generate_risk_summary(
        self,
        validation: Dict[str, Any],
        var_result: Dict[str, float]
    ) -> str:
        """
        生成风险总结
        
        Args:
            validation: 验证结果
            var_result: VaR结果
            
        Returns:
            风险总结
        """
        risk_level = validation["risk_level"]
        risk_score = validation["risk_score"]
        
        summary = f"风险级别: {risk_level.upper()}，风险分数: {risk_score}/100\n"
        
        if validation["errors"]:
            summary += "\n⚠️  风险警告:\n"
            for error in validation["errors"]:
                summary += f"  - {error}\n"
        
        if validation["warnings"]:
            summary += "\n注意事项:\n"
            for warning in validation["warnings"]:
                summary += f"  - {warning}\n"
        
        if var_result:
            summary += f"\n📊 VaR分析 (95%置信度):\n"
            summary += f"  - 单日最大可能亏损: {var_result.get('var', 0)} USDT ({var_result.get('var_percent', 0)}%)\n"
            summary += f"  - 条件风险价值: {var_result.get('cvar', 0)} USDT ({var_result.get('cvar_percent', 0)}%)\n"
        
        return summary
    
    def _generate_recommendations(self, validation: Dict[str, Any]) -> List[str]:
        """
        生成风险控制建议
        
        Args:
            validation: 验证结果
            
        Returns:
            建议列表
        """
        recommendations = []
        
        if validation["risk_level"] == RiskLevel.HIGH.value or \
           validation["risk_level"] == RiskLevel.EXTREME.value:
            recommendations.append("⚠️  风险较高，建议取消或减小仓位")
            recommendations.append("严格执行止损策略")
            recommendations.append("考虑分多次建仓")
        
        if not validation["is_valid"]:
            recommendations.append("❌ 交易未通过风险验证，不建议执行")
        
        if validation["suggestions"]:
            recommendations.extend(validation["suggestions"])
        
        recommendations.append("📝 请仔细评估后再做决策")
        
        return recommendations
