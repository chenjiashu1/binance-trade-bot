"""
数据获取模块
从交易所获取市场数据
"""

import asyncio
import time
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

from binance.client import Client
from binance.exceptions import BinanceAPIException
from cachetools import TTLCache, cached

from ..utils.logger import LoggerMixin
from ..utils.exceptions import DataFetchError
from ..utils.config_loader import ConfigLoader

class DataFetcher(LoggerMixin):
    """
    数据获取器
    从币安获取市场行情数据
    """
    
    def __init__(self, config: ConfigLoader):
        super().__init__()
        self.config = config
        self.client = self._init_client()
        self.cache = TTLCache(maxsize=100, ttl=60)  # 1分钟缓存
    
    def _init_client(self) -> Client:
        """初始化币安客户端"""
        exchange_config = self.config.get_exchange_config()
        
        try:
            client = Client(
                api_key=exchange_config.get("api_key", ""),
                api_secret=exchange_config.get("secret", ""),
                testnet=exchange_config.get("testnet", True)
            )
            
            # 测试连接
            client.ping()
            self.logger.info("币安客户端初始化成功")
            return client
            
        except BinanceAPIException as e:
            raise DataFetchError(f"币安API连接失败: {e}", source="binance")
        except Exception as e:
            raise DataFetchError(f"客户端初始化失败: {e}", source="binance")
    
    @cached(cache=TTLCache(maxsize=50, ttl=30))
    def get_klines(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 100,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None
    ) -> pd.DataFrame:
        """
        获取K线数据
        
        Args:
            symbol: 交易对 (如 "BTCUSDT")
            timeframe: 时间周期 (如 "1h", "4h", "1d")
            limit: 获取数量
            start_time: 开始时间 (毫秒时间戳)
            end_time: 结束时间 (毫秒时间戳)
            
        Returns:
            K线数据DataFrame
        """
        try:
            self.logger.debug(f"获取K线数据: {symbol} {timeframe} limit={limit}")
            
            # 转换时间周期
            binance_timeframe = self._convert_timeframe(timeframe)
            
            klines = self.client.get_klines(
                symbol=symbol.upper(),
                interval=binance_timeframe,
                limit=limit,
                startTime=start_time,
                endTime=end_time
            )
            
            if not klines:
                raise DataFetchError(f"未获取到K线数据: {symbol}", source="binance")
            
            # 转换为DataFrame
            df = pd.DataFrame(
                klines,
                columns=[
                    "timestamp", "open", "high", "low", "close", "volume",
                    "close_time", "quote_volume", "trades", "taker_buy_base",
                    "taker_buy_quote", "ignore"
                ]
            )
            
            # 转换数据类型
            numeric_cols = ["open", "high", "low", "close", "volume", 
                          "quote_volume", "taker_buy_base", "taker_buy_quote"]
            df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric)
            
            # 添加时间列
            df["datetime"] = pd.to_datetime(df["timestamp"], unit="ms")
            df.set_index("datetime", inplace=True)
            
            self.logger.debug(f"成功获取K线数据: {symbol} {timeframe} {len(df)}条")
            return df
            
        except BinanceAPIException as e:
            raise DataFetchError(f"K线数据获取失败: {e}", source="binance")
        except Exception as e:
            raise DataFetchError(f"K线数据处理失败: {e}", source="binance")
    
    @cached(cache=TTLCache(maxsize=100, ttl=10))
    def get_symbol_ticker(self, symbol: str) -> Dict[str, float]:
        """
        获取交易对最新价格
        
        Args:
            symbol: 交易对
            
        Returns:
            价格信息
        """
        try:
            ticker = self.client.get_symbol_ticker(symbol=symbol.upper())
            return {
                "symbol": ticker["symbol"],
                "price": float(ticker["price"]),
                "timestamp": int(time.time() * 1000)
            }
            
        except BinanceAPIException as e:
            raise DataFetchError(f"价格获取失败: {e}", source="binance")
    
    @cached(cache=TTLCache(maxsize=50, ttl=60))
    def get_all_tickers(self) -> Dict[str, float]:
        """
        获取所有交易对价格
        
        Returns:
            价格字典 {symbol: price}
        """
        try:
            tickers = self.client.get_all_tickers()
            return {t["symbol"]: float(t["price"]) for t in tickers}
            
        except BinanceAPIException as e:
            raise DataFetchError(f"所有价格获取失败: {e}", source="binance")
    
    @cached(cache=TTLCache(maxsize=50, ttl=30))
    def get_order_book(self, symbol: str, limit: int = 100) -> Dict[str, List]:
        """
        获取订单簿数据
        
        Args:
            symbol: 交易对
            limit: 订单数量
            
        Returns:
            订单簿数据
        """
        try:
            order_book = self.client.get_order_book(symbol=symbol.upper(), limit=limit)
            
            # 转换数据类型
            bids = [[float(price), float(quantity)] for price, quantity in order_book["bids"]]
            asks = [[float(price), float(quantity)] for price, quantity in order_book["asks"]]
            
            return {
                "symbol": symbol.upper(),
                "bids": bids,
                "asks": asks,
                "timestamp": int(time.time() * 1000)
            }
            
        except BinanceAPIException as e:
            raise DataFetchError(f"订单簿获取失败: {e}", source="binance")
    
    @cached(cache=TTLCache(maxsize=50, ttl=60))
    def get_24h_ticker(self, symbol: str) -> Dict[str, float]:
        """
        获取24小时交易统计
        
        Args:
            symbol: 交易对
            
        Returns:
            24小时统计数据
        """
        try:
            ticker = self.client.get_ticker(symbol=symbol.upper())
            
            return {
                "symbol": ticker["symbol"],
                "price_change": float(ticker["priceChange"]),
                "price_change_percent": float(ticker["priceChangePercent"]),
                "weighted_avg_price": float(ticker["weightedAvgPrice"]),
                "prev_close_price": float(ticker["prevClosePrice"]),
                "last_price": float(ticker["lastPrice"]),
                "bid_price": float(ticker["bidPrice"]),
                "ask_price": float(ticker["askPrice"]),
                "open_price": float(ticker["openPrice"]),
                "high_price": float(ticker["highPrice"]),
                "low_price": float(ticker["lowPrice"]),
                "volume": float(ticker["volume"]),
                "quote_volume": float(ticker["quoteVolume"]),
                "open_time": int(ticker["openTime"]),
                "close_time": int(ticker["closeTime"])
            }
            
        except BinanceAPIException as e:
            raise DataFetchError(f"24小时统计获取失败: {e}", source="binance")
    
    def get_historical_klines(
        self,
        symbol: str,
        timeframe: str,
        start_str: str,
        end_str: Optional[str] = None
    ) -> pd.DataFrame:
        """
        获取历史K线数据
        
        Args:
            symbol: 交易对
            timeframe: 时间周期
            start_str: 开始时间字符串
            end_str: 结束时间字符串
            
        Returns:
            历史K线数据
        """
        try:
            self.logger.info(f"获取历史K线数据: {symbol} {timeframe} from {start_str} to {end_str}")
            
            binance_timeframe = self._convert_timeframe(timeframe)
            
            klines = self.client.get_historical_klines(
                symbol=symbol.upper(),
                interval=binance_timeframe,
                start_str=start_str,
                end_str=end_str
            )
            
            if not klines:
                raise DataFetchError(f"未获取到历史K线数据: {symbol}", source="binance")
            
            df = pd.DataFrame(
                klines,
                columns=[
                    "timestamp", "open", "high", "low", "close", "volume",
                    "close_time", "quote_volume", "trades", "taker_buy_base",
                    "taker_buy_quote", "ignore"
                ]
            )
            
            numeric_cols = ["open", "high", "low", "close", "volume",
                          "quote_volume", "taker_buy_base", "taker_buy_quote"]
            df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric)
            
            df["datetime"] = pd.to_datetime(df["timestamp"], unit="ms")
            df.set_index("datetime", inplace=True)
            
            self.logger.info(f"成功获取历史K线数据: {symbol} {timeframe} {len(df)}条")
            return df
            
        except Exception as e:
            raise DataFetchError(f"历史K线数据获取失败: {e}", source="binance")
    
    def _convert_timeframe(self, timeframe: str) -> str:
        """转换时间周期格式"""
        timeframe_mapping = {
            "1m": Client.KLINE_INTERVAL_1MINUTE,
            "3m": Client.KLINE_INTERVAL_3MINUTE,
            "5m": Client.KLINE_INTERVAL_5MINUTE,
            "15m": Client.KLINE_INTERVAL_15MINUTE,
            "30m": Client.KLINE_INTERVAL_30MINUTE,
            "1h": Client.KLINE_INTERVAL_1HOUR,
            "2h": Client.KLINE_INTERVAL_2HOUR,
            "4h": Client.KLINE_INTERVAL_4HOUR,
            "6h": Client.KLINE_INTERVAL_6HOUR,
            "8h": Client.KLINE_INTERVAL_8HOUR,
            "12h": Client.KLINE_INTERVAL_12HOUR,
            "1d": Client.KLINE_INTERVAL_1DAY,
            "3d": Client.KLINE_INTERVAL_3DAY,
            "1w": Client.KLINE_INTERVAL_1WEEK,
            "1M": Client.KLINE_INTERVAL_1MONTH
        }
        
        return timeframe_mapping.get(timeframe, Client.KLINE_INTERVAL_1HOUR)
    
    async def async_get_klines(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 100
    ) -> pd.DataFrame:
        """异步获取K线数据"""
        return await asyncio.to_thread(self.get_klines, symbol, timeframe, limit)
    
    async def async_get_all_symbols_data(
        self,
        symbols: List[str],
        timeframe: str,
        limit: int = 100
    ) -> Dict[str, pd.DataFrame]:
        """异步获取多个交易对的K线数据"""
        tasks = [
            self.async_get_klines(symbol, timeframe, limit)
            for symbol in symbols
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return {
            symbol: result
            for symbol, result in zip(symbols, results)
            if not isinstance(result, Exception)
        }
