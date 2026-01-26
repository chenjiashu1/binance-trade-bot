"""
账户管理模块
管理账户状态和交易历史
"""

import json
import time
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import pandas as pd

from binance.client import Client
from binance.exceptions import BinanceAPIException
from sqlalchemy.util import symbol

from ..utils.logger import LoggerMixin
from ..utils.exceptions import DataFetchError

class AccountManager(LoggerMixin):
    """
    账户管理器
    管理账户余额、持仓和交易历史
    """
    
    def __init__(self, client: Client):
        super().__init__()
        self.client = client
        self.balances: Dict[str, float] = {}
        self.positions: Dict[str, Dict] = {}
        self.trade_history: List[Dict] = []
        self.last_update_time: float = 0
    
    def get_account_info(self) -> Dict:
        """
        获取账户信息
        
        Returns:
            账户信息字典
        """
        try:
            account = self.client.get_account()
            
            return {
                "maker_commission": account["makerCommission"],
                "taker_commission": account["takerCommission"],
                "buyer_commission": account["buyerCommission"],
                "seller_commission": account["sellerCommission"],
                "can_trade": account["canTrade"],
                "can_withdraw": account["canWithdraw"],
                "can_deposit": account["canDeposit"],
                "update_time": account["updateTime"]
            }
            
        except BinanceAPIException as e:
            raise DataFetchError(f"账户信息获取失败: {e}", source="account")
    
    def get_balances(self, update: bool = True) -> Dict[str, float]:
        """
        获取账户余额
        
        Args:
            update: 是否强制更新
            
        Returns:
            余额字典 {asset: free_balance}
        """
        try:
            if update or time.time() - self.last_update_time > 60:
                account = self.client.get_account()
                self.balances = {
                    balance["asset"]: float(balance["free"]) + float(balance["locked"])
                    for balance in account["balances"]
                    if float(balance["free"]) + float(balance["locked"]) > 0
                }
                self.last_update_time = time.time()
                self.logger.debug(f"余额更新成功: {len(self.balances)} 个币种")
            
            return self.balances
            
        except BinanceAPIException as e:
            raise DataFetchError(f"余额获取失败: {e}", source="account")
    
    def get_balance(self, asset: str, update: bool = True) -> float:
        """
        获取指定币种余额
        
        Args:
            asset: 币种
            update: 是否强制更新
            
        Returns:
            余额
        """
        balances = self.get_balances(update)
        return balances.get(asset.upper(), 0.0)
    
    def get_usdt_balance(self, prices: Optional[Dict[str, float]] = None) -> Dict[str, float]:
        """
        获取以USDT计价的资产
        
        Args:
            prices: 价格字典 {symbol: price}
            
        Returns:
            USDT计价的资产
        """
        try:
            balances = self.get_balances()
            
            if prices is None:
                prices = {}
                tickers = self.client.get_all_tickers()
                prices = {t["symbol"]: float(t["price"]) for t in tickers}
            
            total_usdt = 0.0
            asset_usdt = {}
            
            for asset, balance in balances.items():
                if asset == "USDT":
                    usdt_value = balance
                else:
                    symbol = f"{asset}USDT"
                    price = prices.get(symbol, 0)
                    usdt_value = balance * price
                
                asset_usdt[asset] = usdt_value
                total_usdt += usdt_value
            
            asset_usdt["total"] = total_usdt
            
            return asset_usdt
            
        except BinanceAPIException as e:
            raise DataFetchError(f"USDT资产计算失败: {e}", source="account")
    
    def get_trade_history(
        self,
        symbol: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        获取交易历史
        
        Args:
            symbol: 交易对 (None表示所有)
            limit: 获取数量
            
        Returns:
            交易历史列表
        """
        try:
            if symbol:
                # 指定交易对时可以直接获取
                params = {
                    "symbol": symbol.upper(),
                    "limit": limit
                }
                trades = self.client.get_my_trades(**params)
            else:
                # 不指定交易对时，需要从账户信息中获取
                # 注意: Binance API不支持直接获取所有交易历史
                # 这里返回空列表，实际使用时应该指定具体交易对
                self.logger.warning("Binance API不支持直接获取所有交易历史，请指定交易对")
                trades = []
            
            self.trade_history = [{
                "symbol": trade["symbol"],
                "order_id": trade["orderId"],
                "trade_id": trade["id"],
                "price": float(trade["price"]),
                "quantity": float(trade["qty"]),
                "quote_quantity": float(trade["quoteQty"]),
                "commission": float(trade["commission"]),
                "commission_asset": trade["commissionAsset"],
                "is_buyer": trade["isBuyer"],
                "is_maker": trade["isMaker"],
                "is_best_match": trade["isBestMatch"],
                "time": trade["time"],
                "datetime": datetime.fromtimestamp(trade["time"] / 1000).strftime("%Y-%m-%d %H:%M:%S")
            } for trade in trades]
            
            self.logger.debug(f"获取交易历史: {len(self.trade_history)} 条")
            return self.trade_history
            
        except BinanceAPIException as e:
            raise DataFetchError(f"交易历史获取失败: {e}", source="account")
    
    def get_trade_statistics(self, symbol: Optional[str] = None, days: int = 30) -> Dict:
        """
        获取交易统计信息
        
        Args:
            symbol: 交易对
            days: 统计天数
            
        Returns:
            交易统计
        """
        try:
            trades = self.get_trade_history(symbol=symbol)
            
            # 过滤最近N天的交易
            cutoff_time = time.time() - (days * 24 * 60 * 60)
            recent_trades = [
                trade for trade in trades
                if trade["time"] / 1000 > cutoff_time
            ]
            
            if not recent_trades:
                return {
                    "total_trades": 0,
                    "win_rate": 0,
                    "profit_factor": 0,
                    "avg_profit": 0,
                    "max_win": 0,
                    "max_loss": 0,
                    "consecutive_wins": 0,
                    "consecutive_losses": 0
                }
            
            # 计算盈亏
            profits = []
            win_count = 0
            loss_count = 0
            current_consecutive_wins = 0
            current_consecutive_losses = 0
            max_consecutive_wins = 0
            max_consecutive_losses = 0
            
            for trade in recent_trades:
                # 简化计算：假设卖出时的价格变化
                # 实际应该使用成交价格和当前价格计算
                profit = trade["quote_quantity"] * 0.01  # 简化计算
                profits.append(profit)
                
                if profit > 0:
                    win_count += 1
                    current_consecutive_wins += 1
                    current_consecutive_losses = 0
                    max_consecutive_wins = max(max_consecutive_wins, current_consecutive_wins)
                else:
                    loss_count += 1
                    current_consecutive_losses += 1
                    current_consecutive_wins = 0
                    max_consecutive_losses = max(max_consecutive_losses, current_consecutive_losses)
            
            total_profit = sum(p for p in profits if p > 0)
            total_loss = abs(sum(p for p in profits if p < 0))
            
            return {
                "total_trades": len(recent_trades),
                "win_trades": win_count,
                "loss_trades": loss_count,
                "win_rate": round(win_count / len(recent_trades) * 100, 2) if recent_trades else 0,
                "total_profit": round(total_profit, 4),
                "total_loss": round(total_loss, 4),
                "profit_factor": round(total_profit / total_loss, 2) if total_loss > 0 else 0,
                "avg_profit": round(sum(profits) / len(profits), 4) if profits else 0,
                "max_win": round(max(profits), 4) if profits else 0,
                "max_loss": round(min(profits), 4) if profits else 0,
                "consecutive_wins": max_consecutive_wins,
                "consecutive_losses": max_consecutive_losses,
                "statistics_period": f"last {days} days"
            }
            
        except Exception as e:
            self.logger.error(f"交易统计计算失败: {e}", exc_info=True)
            raise DataFetchError(f"交易统计计算失败: {e}", source="account")
    
    def get_account_summary(self, symbol: str, prices: Optional[Dict[str, float]] = None) -> Dict:
        """
        获取账户摘要
        
        Args:
            prices: 价格字典
            
        Returns:
            账户摘要
        """
        try:
            balances = self.get_balances()
            asset_usdt = self.get_usdt_balance(prices)
            
            # 尝试获取交易统计，如果失败则返回空统计
            try: 
                trade_stats = self.get_trade_statistics(symbol)
            except DataFetchError as e:
                self.logger.warning(f"无法获取交易统计: {e}")
                trade_stats = {
                    "total_trades": 0,
                    "win_rate": 0,
                    "profit_factor": 0,
                    "avg_profit": 0,
                    "max_win": 0,
                    "max_loss": 0,
                    "consecutive_wins": 0,
                    "consecutive_losses": 0,
                    "statistics_period": "N/A"
                }
            
            account_info = self.get_account_info()
            
            summary = {
                "timestamp": int(time.time() * 1000),
                "datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "account_info": account_info,
                "balances": balances,
                "asset_usdt": asset_usdt,
                "total_assets_usdt": round(asset_usdt.get("total", 0), 2),
                "trade_statistics": trade_stats,
                "asset_distribution": self._get_asset_distribution(asset_usdt)
            }
            
            return summary
            
        except Exception as e:
            raise DataFetchError(f"账户摘要获取失败: {e}", source="account")
    
    def _get_asset_distribution(self, asset_usdt: Dict[str, float]) -> Dict[str, float]:
        """
        获取资产分布
        
        Args:
            asset_usdt: USDT计价的资产
            
        Returns:
            资产分布
        """
        total = asset_usdt.get("total", 1)
        if total <= 0:
            total = 1
        
        distribution = {}
        for asset, value in asset_usdt.items():
            if asset != "total":
                distribution[asset] = round(value / total * 100, 2)
        
        # 按比例排序
        distribution = dict(sorted(distribution.items(), key=lambda x: x[1], reverse=True))
        
        return distribution
    
    def save_account_snapshot(self, filepath: str):
        """
        保存账户快照
        
        Args:
            filepath: 保存路径
        """
        try:
            summary = self.get_account_summary()
            
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(summary, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"账户快照已保存到: {filepath}")
            
        except Exception as e:
            self.logger.error(f"账户快照保存失败: {e}")
    
    def load_account_snapshot(self, filepath: str) -> Dict:
        """
        加载账户快照
        
        Args:
            filepath: 文件路径
            
        Returns:
            账户快照数据
        """
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                summary = json.load(f)
            
            self.logger.info(f"账户快照已加载: {filepath}")
            return summary
            
        except Exception as e:
            self.logger.error(f"账户快照加载失败: {e}")
            return {}
