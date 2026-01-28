# 快速开始指南

## 🚀 5分钟上手

### 1. 环境准备

```bash
# 确保安装了 Python 3.9+
python --version

# 进入项目目录
cd binance-trade-bot

# 激活虚拟环境 (如果有)
.venv\Scripts\activate
```

### 2. 安装依赖

```bash
pip install pandas numpy openai aiohttp apscheduler pyyaml python-binance
```

### 3. 配置API密钥

```bash
# 复制环境变量示例文件
cp trading_decision_system/.env.example .env

# 编辑 .env 文件 (用记事本或VS Code)
notepad .env
```

在 `.env` 文件中填入你的API密钥:

```env
# Binance API (需要只读权限即可)
BINANCE_API_KEY=your_api_key_here
BINANCE_SECRET=your_secret_here

# DeepSeek API (必需)
DEEPSEEK_API_KEY=your_deepseek_key_here

# Qwen API (可选)
QWEN_API_KEY=your_qwen_key_here

# OpenAI API (可选)
OPENAI_API_KEY=your_openai_key_here
```

**注意**: 
- Binance API需要启用 "读取" 权限
- 建议先使用测试网 (testnet)

### 4. 运行测试

```bash
python trading_decision_system/test_system.py
```

**预期输出**:
```
🎉 所有测试通过！系统功能正常。
```

### 5. 启动分析

#### 方式1: 直接运行

```bash
python trading_decision_system/main.py
```

#### 方式2: 交互式分析

```python
# 创建 analysis.py
from trading_decision_system.main import TradingDecisionSystem
import asyncio

system = TradingDecisionSystem()
report = asyncio.run(system.run_analysis("BTCUSDT"))
print(report["summary"])
system.close()
```

运行:
```bash
python analysis.py
```

---

## 📊 输出示例

### 交易决策总结

```
📊 交易决策总结
========================================

交易对: BTCUSDT
分析时间: 2024-01-20 23:00:00

🎯 最终决策
------------------------------
动作: BUY
趋势: BULLISH
信心度: 75/100
建议仓位: 15%
仓位价值: 1500.0 USDT

📈 入场参考
------------------------------
建议入场价: 42500.0
止损价: 41500.0
止盈 1: 44000.0
止盈 2: 45500.0

🤝 模型一致性
------------------------------
一致性级别: HIGH
一致性分数: 85.5
模型数量: 3
平均信心度: 78.3

⚠️  风险评估
------------------------------
风险级别: MEDIUM
风险分数: 45/100

========================================
💡 请仔细评估风险后再做决策
```

---

## 🔧 常见问题

### Q1: 测试失败怎么办？

**A**: 检查以下内容:
1. Python版本是否 ≥ 3.9
2. 所有依赖是否安装成功
3. 配置文件路径是否正确

### Q2: API密钥如何获取？

**A**:
- **Binance**: https://www.binance.com/en/my/settings/api-management
- **DeepSeek**: https://platform.deepseek.com/  
- **Qwen**: https://dashscope.aliyun.com/
- **OpenAI**: https://platform.openai.com/

### Q3: 如何使用测试网？

**A**: 在 `config.yaml` 中设置:
```yaml
exchange:
  testnet: true
```

### Q4: 如何添加新的交易对？

**A**: 在 `config.yaml` 中修改:
```yaml
exchange:
  symbols:
    - BTCUSDT
    - ETHUSDT
    - ADAUSDT
    - SOLUSDT
    - XRPUSDT
    - YOUR_SYMBOL
```

### Q5: 如何调整模型权重？

**A**: 在 `config.yaml` 中修改:
```yaml
models:
  deepseek:
    weight: 0.4
  qwen:
    weight: 0.3
  gpt4:
    weight: 0.3
```

### Q6: 如何关闭某个模型？

**A**: 设置 `enabled: false`:
```yaml
models:
  qwen:
    enabled: false
```

### Q7: 日志文件在哪里？

**A**: 日志保存在:
- 系统日志: `trading_decision_system/logs/decisions.log`
- 决策报告: `trading_decision_system/logs/decisions/YYYY-MM-DD_HH-MM-SS.json`

### Q8: 如何自定义分析时间？

**A**: 在 `config.yaml` 中设置:
```yaml
analysis:
  schedule:
    - time: "23:00"
      type: strategic
      enabled: true
    - time: "05:00"
      type: strategic
      enabled: true
```

---

## 🎯 快速示例

### 示例1: 分析单个交易对

```python
from trading_decision_system.main import TradingDecisionSystem
import asyncio

system = TradingDecisionSystem()

# 分析 BTCUSDT
report = asyncio.run(system.run_analysis("BTCUSDT"))

# 打印总结
print(report["summary"])

# 打印详细决策
print("\n详细决策:")
print(report["final_decision"])

system.close()
```

### 示例2: 分析多个交易对

```python
from trading_decision_system.main import TradingDecisionSystem
import asyncio

system = TradingDecisionSystem()

symbols = ["BTCUSDT", "ETHUSDT", "ADAUSDT"]

for symbol in symbols:
    print(f"\n{'='*60}")
    print(f"分析: {symbol}")
    print(f"{'='*60}")
    
    try:
        report = asyncio.run(system.run_analysis(symbol))
        print(report["summary"])
    except Exception as e:
        print(f"分析失败: {e}")

system.close()
```

### 示例3: 定时分析

```python
from trading_decision_system.scheduler.task_scheduler import TaskScheduler
from trading_decision_system.main import TradingDecisionSystem

system = TradingDecisionSystem()
scheduler = TaskScheduler(system)

# 每天23:00分析 BTCUSDT
scheduler.add_cron_task(
    "daily_btc_analysis",
    func=system.run_analysis,
    args=["BTCUSDT"],
    hour=23,
    minute=0
)

# 启动调度器
scheduler.start()

print("定时任务已启动，按 Ctrl+C 退出")
```

---

## ⚠️ 重要提醒

1. **安全第一**
   - 永远不要在代码中硬编码API密钥
   - 使用环境变量或加密配置
   - 定期更换API密钥

2. **测试优先**
   - 先在测试网运行至少30天
   - 小资金实盘测试
   - 记录每笔交易

3. **风险控制**
   - 单次仓位不超过20%
   - 严格执行止损
   - 避免过度交易

4. **持续学习**
   - 理解每个指标的含义
   - 学习LLM的分析逻辑
   - 不断优化策略

---

## 📚 更多资源

- **详细文档**: `trading_decision_system/README.md`
- **项目总结**: `TRADING_DECISION_SYSTEM_SUMMARY.md`
- **配置文件**: `trading_decision_system/configs/config.yaml`
- **源码**: `trading_decision_system/`

---

**祝你交易顺利！** 🚀
