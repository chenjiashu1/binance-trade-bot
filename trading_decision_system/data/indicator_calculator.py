"""
技术指标计算模块
计算各种技术分析指标
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from enum import Enum

from ..utils.logger import LoggerMixin
from ..utils.exceptions import DataFetchError

class TrendDirection(Enum):
    """趋势方向"""
    UP = "up"
    DOWN = "down"
    SIDEWAYS = "sideways"

class IndicatorCalculator(LoggerMixin):
    """
    技术指标计算器
    计算各种技术分析指标
    """
    
    def __init__(self):
        super().__init__()
    
    def calculate_rsi(
        self,
        data: pd.DataFrame,
        period: int = 14,
        price_col: str = "close"
    ) -> pd.Series:
        """
        计算RSI指标
        
        Args:
            data: K线数据
            period: 计算周期
            price_col: 价格列名
            
        Returns:
            RSI序列
        """
        try:
            prices = data[price_col]
            delta = prices.diff()
            
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            
            return rsi
            
        except Exception as e:
            raise DataFetchError(f"RSI计算失败: {e}", source="indicator")
    
    def calculate_macd(
        self,
        data: pd.DataFrame,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9,
        price_col: str = "close"
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        计算MACD指标
        
        Args:
            data: K线数据
            fast_period: 快速EMA周期
            slow_period: 慢速EMA周期
            signal_period: 信号线周期
            price_col: 价格列名
            
        Returns:
            MACD线, 信号线, 柱状图
        """
        try:
            prices = data[price_col]
            
            ema_fast = prices.ewm(span=fast_period, adjust=False).mean()
            ema_slow = prices.ewm(span=slow_period, adjust=False).mean()
            
            macd = ema_fast - ema_slow
            signal = macd.ewm(span=signal_period, adjust=False).mean()
            histogram = macd - signal
            
            return macd, signal, histogram
            
        except Exception as e:
            raise DataFetchError(f"MACD计算失败: {e}", source="indicator")
    
    def calculate_ma(
        self,
        data: pd.DataFrame,
        periods: List[int],
        price_col: str = "close"
    ) -> Dict[int, pd.Series]:
        """
        计算移动平均线
        
        Args:
            data: K线数据
            periods: 周期列表
            price_col: 价格列名
            
        Returns:
            MA字典 {period: MA序列}
        """
        try:
            prices = data[price_col]
            ma_dict = {}
            
            for period in periods:
                ma_dict[period] = prices.rolling(window=period).mean()
            
            return ma_dict
            
        except Exception as e:
            raise DataFetchError(f"MA计算失败: {e}", source="indicator")
    
    def calculate_ema(
        self,
        data: pd.DataFrame,
        periods: List[int],
        price_col: str = "close"
    ) -> Dict[int, pd.Series]:
        """
        计算指数移动平均线
        
        Args:
            data: K线数据
            periods: 周期列表
            price_col: 价格列名
            
        Returns:
            EMA字典 {period: EMA序列}
        """
        try:
            prices = data[price_col]
            ema_dict = {}
            
            for period in periods:
                ema_dict[period] = prices.ewm(span=period, adjust=False).mean()
            
            return ema_dict
            
        except Exception as e:
            raise DataFetchError(f"EMA计算失败: {e}", source="indicator")
    
    def calculate_bollinger_bands(
        self,
        data: pd.DataFrame,
        period: int = 20,
        std_dev: float = 2.0,
        price_col: str = "close"
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        计算布林带
        
        Args:
            data: K线数据
            period: 计算周期
            std_dev: 标准差倍数
            price_col: 价格列名
            
        Returns:
            上轨, 中轨, 下轨
        """
        try:
            prices = data[price_col]
            
            middle_band = prices.rolling(window=period).mean()
            std = prices.rolling(window=period).std()
            
            upper_band = middle_band + (std * std_dev)
            lower_band = middle_band - (std * std_dev)
            
            return upper_band, middle_band, lower_band
            
        except Exception as e:
            raise DataFetchError(f"布林带计算失败: {e}", source="indicator")
    
    def calculate_atr(
        self,
        data: pd.DataFrame,
        period: int = 14
    ) -> pd.Series:
        """
        计算ATR指标
        
        Args:
            data: K线数据
            period: 计算周期
            
        Returns:
            ATR序列
        """
        try:
            high = data["high"]
            low = data["low"]
            close = data["close"]
            
            tr1 = high - low
            tr2 = abs(high - close.shift())
            tr3 = abs(low - close.shift())
            
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr = tr.rolling(window=period).mean()
            
            return atr
            
        except Exception as e:
            raise DataFetchError(f"ATR计算失败: {e}", source="indicator")
    
    def calculate_volume_profile(
        self,
        data: pd.DataFrame,
        period: int = 20
    ) -> Dict[str, float]:
        """
        计算成交量分布
        
        Args:
            data: K线数据
            period: 计算周期
            
        Returns:
            成交量分布统计
        """
        try:
            recent_data = data.tail(period)
            
            total_volume = recent_data["volume"].sum()
            avg_volume = recent_data["volume"].mean()
            max_volume = recent_data["volume"].max()
            min_volume = recent_data["volume"].min()
            volume_trend = recent_data["volume"].pct_change().mean()
            
            return {
                "total_volume": total_volume,
                "avg_volume": avg_volume,
                "max_volume": max_volume,
                "min_volume": min_volume,
                "volume_trend": volume_trend,
                "volume_ratio": total_volume / (avg_volume * period) if avg_volume > 0 else 0
            }
            
        except Exception as e:
            raise DataFetchError(f"成交量分布计算失败: {e}", source="indicator")
    
    def detect_trend(
        self,
        data: pd.DataFrame,
        short_period: int = 20,
        long_period: int = 50,
        price_col: str = "close"
    ) -> Dict[str, any]:
        """
        检测趋势方向
        
        Args:
            data: K线数据
            short_period: 短期MA周期
            long_period: 长期MA周期
            price_col: 价格列名
            
        Returns:
            趋势信息
        """
        try:
            prices = data[price_col]
            
            ma_short = prices.rolling(window=short_period).mean()
            ma_long = prices.rolling(window=long_period).mean()
            
            current_price = prices.iloc[-1]
            current_ma_short = ma_short.iloc[-1]
            current_ma_long = ma_long.iloc[-1]
            
            ma_diff = 0
            
            # 计算趋势强度
            if not pd.isna(current_ma_short) and not pd.isna(current_ma_long) and current_ma_long != 0:
                ma_diff = (current_ma_short - current_ma_long) / current_ma_long * 100
                price_diff = (current_price - current_ma_short) / current_ma_short * 100 if current_ma_short != 0 else 0
                
                if ma_diff > 0.5 and price_diff > 0.2:
                    trend = TrendDirection.UP.value
                    strength = min(100, ma_diff * 10 + price_diff * 5)
                elif ma_diff < -0.5 and price_diff < -0.2:
                    trend = TrendDirection.DOWN.value
                    strength = min(100, abs(ma_diff) * 10 + abs(price_diff) * 5)
                else:
                    trend = TrendDirection.SIDEWAYS.value
                    strength = min(100, abs(ma_diff) * 20)
            else:
                trend = TrendDirection.SIDEWAYS.value
                strength = 0
            
            return {
                "trend": trend,
                "strength": round(strength, 2),
                "ma_short": round(current_ma_short, 4),
                "ma_long": round(current_ma_long, 4),
                "current_price": round(current_price, 4),
                "ma_crossover": "golden" if ma_diff > 0 else "death" if ma_diff < 0 else "none"
            }
            
        except Exception as e:
            raise DataFetchError(f"趋势检测失败: {e}", source="indicator")
    
    def calculate_all_indicators(
        self,
        data: pd.DataFrame,
        config: Optional[Dict] = None
    ) -> Dict[str, any]:
        """
        计算所有技术指标
        
        Args:
            data: K线数据
            config: 指标配置
            
        Returns:
            所有指标计算结果
        """
        if config is None:
            config = {
                "rsi": {"period": 14},
                "macd": {"fast": 12, "slow": 26, "signal": 9},
                "ma": {"periods": [20, 50, 200]},
                "bollinger": {"period": 20, "std": 2.0},
                "atr": {"period": 14}
            }
        
        try:
            indicators = {}
            
            # RSI
            rsi = self.calculate_rsi(data, period=config["rsi"]["period"])
            indicators["rsi"] = {
                "value": round(rsi.iloc[-1], 2),
                "status": "overbought" if rsi.iloc[-1] > 70 else "oversold" if rsi.iloc[-1] < 30 else "neutral"
            }
            
            # MACD
            macd, signal, histogram = self.calculate_macd(
                data,
                fast_period=config["macd"]["fast"],
                slow_period=config["macd"]["slow"],
                signal_period=config["macd"]["signal"]
            )
            indicators["macd"] = {
                "macd": round(macd.iloc[-1], 4),
                "signal": round(signal.iloc[-1], 4),
                "histogram": round(histogram.iloc[-1], 4),
                "crossover": "bullish" if histogram.iloc[-1] > 0 and histogram.iloc[-2] < 0 else
                           "bearish" if histogram.iloc[-1] < 0 and histogram.iloc[-2] > 0 else "none"
            }
            
            # MA
            ma_dict = self.calculate_ma(data, periods=config["ma"]["periods"])
            indicators["ma"] = {}
            for period, ma_series in ma_dict.items():
                indicators["ma"][f"ma{period}"] = round(ma_series.iloc[-1], 4)
            
            # 布林带
            upper, middle, lower = self.calculate_bollinger_bands(
                data,
                period=config["bollinger"]["period"],
                std_dev=config["bollinger"]["std"]
            )
            current_price = data["close"].iloc[-1]
            indicators["bollinger"] = {
                "upper": round(upper.iloc[-1], 4),
                "middle": round(middle.iloc[-1], 4),
                "lower": round(lower.iloc[-1], 4),
                "position": "above" if current_price > upper.iloc[-1] else
                           "below" if current_price < lower.iloc[-1] else "inside"
            }
            
            # ATR
            atr = self.calculate_atr(data, period=config["atr"]["period"])
            indicators["atr"] = round(atr.iloc[-1], 4)
            
            # 趋势检测
            trend_info = self.detect_trend(data)
            indicators["trend"] = trend_info
            
            # 成交量分布
            volume_profile = self.calculate_volume_profile(data)
            indicators["volume"] = volume_profile
            
            # 价格统计
            recent_data = data.tail(20)
            indicators["price_stats"] = {
                "current": round(data["close"].iloc[-1], 4),
                "open": round(data["open"].iloc[-1], 4),
                "high": round(recent_data["high"].max(), 4),
                "low": round(recent_data["low"].min(), 4),
                "change_24h": round((data["close"].iloc[-1] - data["open"].iloc[-24]) / data["open"].iloc[-24] * 100, 2) if len(data) >= 24 else 0
            }
            
            return indicators
            
        except Exception as e:
            raise DataFetchError(f"指标计算失败: {e}", source="indicator")
