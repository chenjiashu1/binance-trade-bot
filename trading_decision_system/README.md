# 多模型数字货币智能决策系统

一个基于多LLM模型的数字货币交易决策支持系统，通过结合市场客观数据和账户主观状态，生成具备风险意识的量化交易方案。

## 📋 项目概述

### 核心目标
构建一个基于多LLM模型的数字货币交易决策支持系统，通过结合市场客观数据和账户主观状态，生成具备风险意识的量化交易方案。

### 项目定位
- **性质**：决策辅助系统（非全自动交易系统）
- **用户**：有一定经验的数字货币交易者
- **模式**：AI建议 → 人工审核 → 手动/半自动执行
- **阶段**：先模拟验证，后小资金实盘测试

## 🏗️ 系统架构

### 三层架构

```
┌─────────────────────────────────────────────────────┐
│              决策汇总层 (Decision Layer)             │
│  • 多模型结果聚合算法                                │
│  • 风险控制模块                                      │
│  • 最终决策生成                                      │
└─────────────────────────────────────────────────────┘
                        ↑
┌─────────────────────────────────────────────────────┐
│              智能分析层 (Analysis Layer)             │
│  • LLM模型集成 (DeepSeek, Qwen, GPT-4)              │
│  • Prompt模板系统                                    │
│  • 多模型并行分析                                    │
└─────────────────────────────────────────────────────┘
                        ↑
┌─────────────────────────────────────────────────────┐
│              数据采集层 (Data Layer)                 │
│  • 市场行情获取 (Binance API)                       │
│  • 技术指标计算 (RSI, MACD, MA, 布林带等)            │
│  • 账户状态管理                                      │
└─────────────────────────────────────────────────────┘
```

### 模块结构

```
trading_decision_system/
├── __init__.py              # 包初始化
├── main.py                  # 主程序入口
├── configs/
│   └── config.yaml         # 配置文件
├── data/                   # 数据采集层
│   ├── __init__.py
│   ├── data_fetcher.py     # 市场数据获取
│   ├── indicator_calculator.py  # 技术指标计算
│   └── account_manager.py  # 账户状态管理
├── analysis/               # 智能分析层
│   ├── __init__.py
│   ├── llm_analyzer.py     # LLM分析器
│   └── prompt_templates.py # Prompt模板
├── decision/               # 决策汇总层
│   ├── __init__.py
│   ├── decision_aggregator.py  # 决策聚合器
│   └── risk_controller.py  # 风险控制器
├── scheduler/              # 任务调度
│   ├── __init__.py
│   └── task_scheduler.py   # 任务调度器
├── utils/                  # 工具模块
│   ├── __init__.py
│   ├── logger.py           # 日志系统
│   ├── config_loader.py    # 配置加载
│   └── exceptions.py       # 自定义异常
└── logs/                   # 日志目录
    └── decisions/          # 决策报告目录
```

## 🚀 快速开始

### 环境要求

- Python 3.9+
- pip 20.0+

### 安装依赖

```bash
# 进入项目目录
cd binance-trade-bot

# 安装依赖
pip install -r requirements.txt

# 或者手动安装关键依赖
pip install python-binance pandas numpy openai aiohttp apscheduler pyyaml
```

### 配置API密钥

1. 复制环境变量示例文件
```bash
cp trading_decision_system/.env.example .env
```

2. 编辑 `.env` 文件，填入你的API密钥
```env
# Binance API (需要只读权限即可)
BINANCE_API_KEY=your_api_key
BINANCE_SECRET=your_secret

# DeepSeek API (必需)
DEEPSEEK_API_KEY=your_deepseek_key

# Qwen API (可选，用于技术分析)
QWEN_API_KEY=your_qwen_key

# OpenAI API (可选，用于风险评估)
OPENAI_API_KEY=your_openai_key
```

### 运行系统

```bash
# 方式1: 直接运行主程序
python trading_decision_system/main.py

# 方式2: 作为模块运行
python -m trading_decision_system.main

# 方式3: 交互式分析
python -c "
from trading_decision_system.main import TradingDecisionSystem
import asyncio

system = TradingDecisionSystem()
report = asyncio.run(system.run_analysis('BTCUSDT'))
print(report['summary'])
system.close()
"
```

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

## 🔧 配置说明

### config.yaml 主要配置项

```yaml
# 交易所配置
exchange:
  name: binance
  api_key: ${BINANCE_API_KEY}
  secret: ${BINANCE_SECRET}
  symbols: [BTCUSDT, ETHUSDT, ADAUSDT]
  timeframes: [1h, 4h, 1d]
  testnet: true

# LLM模型配置
models:
  deepseek:
    api_key: ${DEEPSEEK_API_KEY}
    role: strategist
    weight: 0.4
    enabled: true
  
  qwen:
    api_key: ${QWEN_API_KEY}
    role: technical
    weight: 0.3
    enabled: false

# 风险控制配置
analysis:
  risk_limits:
    max_position_percent: 20
    max_daily_loss: 5
    stop_loss_default: 2

# 定时任务配置
analysis:
  schedule:
    - time: "23:00"
      type: strategic
      enabled: true
    - time: "05:00"
      type: strategic
      enabled: true
```

## 🎯 核心功能

### 1. 多时间框架分析
- 1小时图: 短期趋势分析
- 4小时图: 中期趋势分析
- 日线图: 长期趋势分析

### 2. 技术指标计算
- RSI (相对强弱指数)
- MACD (移动平均收敛/发散)
- MA (移动平均线)
- 布林带
- ATR (平均真实波动)
- 成交量分布

### 3. 多LLM模型分析
- **策略分析师** (DeepSeek): 趋势判断、关键价位、风险收益比
- **技术分析师** (Qwen): 多时间框架、指标信号、形态识别
- **风险评估师** (GPT-4): 风险评估、仓位控制、止损建议

### 4. 决策聚合算法
- 冲突检测
- 加权投票
- 一致性分析
- 风险过滤

### 5. 风险控制
- VaR (风险价值) 计算
- Calmar比率
- 每日亏损限制
- 仓位大小限制
- 持仓数量限制

## 📈 定时任务

系统支持以下定时分析任务：

- **低频分析**: 每日2次 (23:00, 05:00) - 基本面+策略分析
- **技术分析**: 每小时整点 - 技术指标监控
- **周报分析**: 每周日23:00 - 总结与调整

## ⚠️ 风险提示

1. **资金安全**
   - 仅使用只读API密钥 (初期)
   - 模拟账户至少运行30天
   - 实盘资金不超过总投资5%

2. **系统风险**
   - 关键配置环境变量化
   - API密钥加密存储
   - 操作审计日志

3. **决策风险**
   - 所有建议必须包含止损
   - 单次建议仓位≤20%总资金
   - 高风险时段自动降低仓位

## 📝 开发计划

### 第一阶段: MVP (已完成)
- [x] 单一交易所数据获取 (币安)
- [x] 基础技术指标计算 (RSI, MACD, MA)
- [x] 单个LLM分析 (DeepSeek)
- [x] 简单决策输出 (JSON格式)
- [x] 人工手动执行

### 第二阶段: 多模型系统 (进行中)
- [x] 多LLM并行分析 (Qwen + GPT-4)
- [x] 决策聚合算法 (加权投票)
- [x] 账户状态集成
- [x] 风险控制模块
- [ ] 简单回测验证

### 第三阶段: 高级功能 (规划中)
- [ ] 模拟交易引擎
- [ ] 实时监控告警
- [ ] 性能分析面板
- [ ] 事件驱动触发

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

### 开发流程
1. Fork 本仓库
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 🙏 致谢

- [Binance API](https://binance-docs.github.io/apidocs/spot/en/) - 市场数据来源
- [DeepSeek](https://www.deepseek.com/) - 策略分析模型
- [Qwen](https://www.alibabacloud.com/product/dashscope) - 技术分析模型
- [OpenAI](https://openai.com/) - 风险评估模型
- [pandas](https://pandas.pydata.org/) - 数据处理
- [python-binance](https://python-binance.readthedocs.io/) - Binance API客户端

## 📞 联系方式

如有问题或建议，欢迎通过以下方式联系：

- 提交 Issue
- 发送邮件

---

**免责声明**: 本系统仅供学习和研究使用，不构成任何投资建议。加密货币交易存在高风险，请谨慎决策。
