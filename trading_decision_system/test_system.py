"""
系统测试脚本
测试各个模块的功能
"""

import sys
import asyncio
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from trading_decision_system.utils.logger import setup_logger
from trading_decision_system.utils.config_loader import ConfigLoader
from trading_decision_system.data.data_fetcher import DataFetcher
from trading_decision_system.data.indicator_calculator import IndicatorCalculator
from trading_decision_system.analysis.prompt_templates import PromptTemplates


def test_config_loader():
    """测试配置加载"""
    print("\n" + "="*60)
    print("测试 1: 配置加载")
    print("="*60)
    
    try:
        config = ConfigLoader("./trading_decision_system/configs/config.yaml")
        print("✅ 配置文件加载成功")
        
        # 测试获取配置
        exchange_config = config.get_exchange_config()
        print(f"  - 交易所名称: {exchange_config.get('name')}")
        print(f"  - 交易对: {exchange_config.get('symbols')}")
        print(f"  - 时间周期: {exchange_config.get('timeframes')}")
        
        models = config.get_all_enabled_models()
        print(f"  - 启用的模型: {list(models.keys())}")
        
        return True
        
    except Exception as e:
        print(f"❌ 配置加载失败: {e}")
        return False


def test_indicator_calculator():
    """测试指标计算"""
    print("\n" + "="*60)
    print("测试 2: 指标计算")
    print("="*60)
    
    try:
        import pandas as pd
        import numpy as np
        
        # 创建模拟数据
        np.random.seed(42)
        dates = pd.date_range(start="2024-01-01", periods=100, freq="1h")
        prices = np.cumsum(np.random.randn(100) * 0.01) + 100
        
        data = pd.DataFrame({
            "timestamp": dates.astype(np.int64) // 10**9,
            "open": prices,
            "high": prices + np.random.rand(100) * 2,
            "low": prices - np.random.rand(100) * 2,
            "close": prices,
            "volume": np.random.randint(1000, 10000, size=100)
        })
        data.set_index(pd.to_datetime(data["timestamp"], unit="s"), inplace=True)
        
        print(f"✅ 生成模拟数据: {len(data)} 条")
        
        # 初始化计算器
        calculator = IndicatorCalculator()
        
        # 计算RSI
        rsi = calculator.calculate_rsi(data)
        print(f"  - RSI: {rsi.iloc[-1]:.2f}")
        
        # 计算MACD
        macd, signal, histogram = calculator.calculate_macd(data)
        print(f"  - MACD: {macd.iloc[-1]:.4f}")
        print(f"  - Signal: {signal.iloc[-1]:.4f}")
        print(f"  - Histogram: {histogram.iloc[-1]:.4f}")
        
        # 计算MA
        ma_dict = calculator.calculate_ma(data, periods=[20, 50])
        print(f"  - MA20: {ma_dict[20].iloc[-1]:.2f}")
        print(f"  - MA50: {ma_dict[50].iloc[-1]:.2f}")
        
        # 计算布林带
        upper, middle, lower = calculator.calculate_bollinger_bands(data)
        print(f"  - 布林带上轨: {upper.iloc[-1]:.2f}")
        print(f"  - 布林带中轨: {middle.iloc[-1]:.2f}")
        print(f"  - 布林带下轨: {lower.iloc[-1]:.2f}")
        
        # 计算ATR
        atr = calculator.calculate_atr(data)
        print(f"  - ATR: {atr.iloc[-1]:.2f}")
        
        # 检测趋势
        trend = calculator.detect_trend(data)
        print(f"  - 趋势: {trend['trend']} (强度: {trend['strength']}%)")
        
        # 计算所有指标
        all_indicators = calculator.calculate_all_indicators(data)
        print(f"\n✅ 所有指标计算完成")
        print(f"  - 指标数量: {len(all_indicators)}")
        
        return True
        
    except Exception as e:
        print(f"❌ 指标计算失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_prompt_templates():
    """测试Prompt模板"""
    print("\n" + "="*60)
    print("测试 3: Prompt模板")
    print("="*60)
    
    try:
        templates = PromptTemplates()
        
        # 准备测试数据
        test_data = {
            "symbol": "BTCUSDT",
            "current_price": 42500.0,
            "price_change_24h": 2.5,
            "trend": "up",
            "trend_strength": 75,
            "rsi": 65,
            "rsi_status": "neutral",
            "macd": 50.5,
            "signal": 45.2,
            "histogram": 5.3,
            "macd_crossover": "bullish",
            "ma20": 42000,
            "ma50": 41500,
            "ma200": 40000,
            "bb_upper": 43000,
            "bb_middle": 42500,
            "bb_lower": 42000,
            "bb_position": "inside",
            "atr": 500,
            "volume_24h": 10000000,
            "volume_trend": "increasing",
            "total_assets": 10000,
            "usdt_balance": 5000,
            "current_positions": 3,
            "win_rate": 65,
            "total_trades": 50
        }
        
        # 测试策略分析师Prompt
        strategist_prompt = templates.get_strategist_prompt(test_data)
        print(f"✅ 策略分析师Prompt生成成功")
        print(f"  - 长度: {len(strategist_prompt)} 字符")
        
        # 测试技术分析师Prompt
        technical_data = test_data.copy()
        technical_data.update({
            "trend_1h": "up",
            "trend_strength_1h": 70,
            "rsi_1h": 60,
            "rsi_status_1h": "neutral",
            "macd_1h": 25.5,
            "signal_1h": 20.2,
            "histogram_1h": 5.3,
            "ma20_1h": 42200,
            "ma50_1h": 41800,
            "bb_upper_1h": 42800,
            "bb_middle_1h": 42500,
            "bb_lower_1h": 42200,
            "trend_4h": "up",
            "trend_strength_4h": 80,
            "rsi_4h": 68,
            "rsi_status_4h": "neutral",
            "macd_4h": 80.5,
            "signal_4h": 70.2,
            "histogram_4h": 10.3,
            "ma20_4h": 42000,
            "ma50_4h": 41500,
            "ma200_4h": 40000,
            "bb_upper_4h": 43500,
            "bb_middle_4h": 42500,
            "bb_lower_4h": 41500,
            "trend_1d": "up",
            "trend_strength_1d": 85,
            "rsi_1d": 72,
            "rsi_status_1d": "neutral",
            "macd_1d": 150.5,
            "signal_1d": 130.2,
            "histogram_1d": 20.3,
            "ma20_1d": 41800,
            "ma50_1d": 41000,
            "ma200_1d": 39500,
            "bb_upper_1d": 44000,
            "bb_middle_1d": 42500,
            "bb_lower_1d": 41000
        })
        
        technical_prompt = templates.get_technical_prompt(technical_data)
        print(f"✅ 技术分析师Prompt生成成功")
        print(f"  - 长度: {len(technical_prompt)} 字符")
        
        # 测试风险评估师Prompt
        risk_data = {
            "symbol": "BTCUSDT",
            "current_price": 42500.0,
            "position_size": 15,
            "position_value": 1500,
            "entry_price": 42500.0,
            "stop_loss_price": 41500.0,
            "take_profit_price": 44000.0,
            "price_change_24h": 2.5,
            "atr": 500,
            "max_daily_change": 5.2,
            "volume_anomaly": "否",
            "total_assets": 10000,
            "usdt_balance": 5000,
            "open_positions": 3,
            "max_drawdown_30d": 8.5,
            "max_daily_loss": 5
        }
        
        risk_prompt = templates.get_risk_prompt(risk_data)
        print(f"✅ 风险评估师Prompt生成成功")
        print(f"  - 长度: {len(risk_prompt)} 字符")
        
        # 测试JSON验证
        test_json = '{"key": "value", "number": 123}'
        parsed = templates.validate_json_output(test_json)
        print(f"\n✅ JSON验证功能正常")
        print(f"  - 解析结果: {parsed}")
        
        return True
        
    except Exception as e:
        print(f"❌ Prompt模板测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """主测试函数"""
    print("\n" + "#"*60)
    print("# 多模型数字货币智能决策系统 - 单元测试")
    print("#"*60)
    
    results = []
    
    # 测试配置加载
    results.append(("配置加载", test_config_loader()))
    
    # 测试指标计算
    results.append(("指标计算", test_indicator_calculator()))
    
    # 测试Prompt模板
    results.append(("Prompt模板", test_prompt_templates()))
    
    # 汇总结果
    print("\n" + "="*60)
    print("测试结果汇总")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{name}: {status}")
    
    print(f"\n总计: {passed}/{total} 通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！系统功能正常。")
    else:
        print(f"\n⚠️  {total - passed} 个测试失败，请检查问题。")
    
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
