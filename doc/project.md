* hyper-alpha-arena项目特点分析：
    - 缺少历史回测（导致交易信号和prompt只能回测最近的数据）
    - 对Hyperliquid依赖强，如数据获取、钱包、交易等（导致无法在其他交易所部署）
    - 目前只有实盘评估，缺少回测效果评估
    - 自带信号和prompt回测功能，可以借鉴过来
    - 可以通过Hyperliquid获取的交易数据，如订单、成交等客观数据
    - 模拟盘的回测和真实盘的回测是存在差异的，比如：价格数据精度、订单执行确定性、市场环境复杂度、心理因素影响等
* 综合上述特点：
    - 短期实现历史回测有点困难,所以先通过实盘评估，再考虑历史回测
* 初期方案（只能提供一个意见支持）：
    - 先通过币安获取行情数据、技术指标等客观数据
    - 主观数据通过后端配置账号传入（如：账户持仓、历史交易等情况）
    - 通过接口或者定时任务（北京时间23点和北京时间5点）
    - 设置prompt，基于客观数据和主观数据，通过多种LLm（qwen、deepseek等）生成交易策略和走势概率预测
    - 汇总各种模型结果，生成最优的交易方案，并给出原因
* 初期方案需要解决的问题：
    - 没有回测过该方案，只是结合多个llm的能力去分析预测（说明这是临时方案，不可靠）
    - 没有定完备的交易信号，导致缺少交易触发机制，需手动触发（缺少动态监控的能力）
* 需考虑的问题：
    - 初期方案的后期的扩展性
    - pgsql数据库的设计和使用
    - 是否有必要在原始项目上变更---在binance-trade-bot的基础上改造，它已对接币安，hyper-alpha-arena项目存在太多原始依赖，启动相对复杂，未对接币安
    - binance-trade-bot使用的是litesql，和mysql大差不差，更加轻量级




# 多模型数字货币智能决策系统需求文档

## 📌 项目概述

### 核心目标
构建一个基于多LLM模型的数字货币交易决策支持系统，通过结合市场客观数据和账户主观状态，生成具备风险意识的量化交易方案。

### 项目定位
- **性质**：决策辅助系统（非全自动交易系统）
- **用户**：有一定经验的数字货币交易者
- **模式**：AI建议 → 人工审核 → 手动/半自动执行
- **阶段**：先模拟验证，后小资金实盘测试

## 🏗️ 系统架构（三层架构）

### 1. 数据采集层
#### 客观数据源
```
1. 市场行情（币安API）
   - 实时价格（秒级/分钟级）
   - K线数据（1m, 15m, 1h, 4h, 1d）
   - 成交量与深度
   - 资金费率（永续合约）

2. 技术指标（实时计算）
   - 基础指标：MA, EMA, MACD, RSI, Bollinger Bands
   - 高级指标：ATR, ADX, Ichimoku Cloud（可选）
   - 自定义指标：用户可配置

3. 链上数据（二期扩展）
   - 大额转账监控
   - 交易所流入流出
```

#### 主观数据源
```
1. 账户状态（用户配置）
   - 持仓明细：币种、数量、成本价
   - 资产分布：USDT余额、各币种市值
   - 浮动盈亏：未实现盈亏比例

2. 交易历史
   - 最近30笔交易记录
   - 胜率统计、盈亏比
   - 最大回撤、连续盈亏记录

3. 风险偏好配置
   - 单笔最大风险（1-5%）
   - 每日最大亏损限额
   - 仓位偏好（保守/中性/激进）
```

### 2. 智能分析层
#### 模型配置（初期）
```
┌─────────────────┬─────────────────┬─────────────────┐
│   模型名称      │     角色        │     权重        │
├─────────────────┼─────────────────┼─────────────────┤
│   DeepSeek      │  策略分析师    │      40%       │
│   Qwen-Max      │  技术分析师    │      30%       │
│   GPT-4         │  风险评估师    │      30%       │
└─────────────────┴─────────────────┴─────────────────┘
```

#### 分析触发机制
**A. 定时分析（主要模式）**
```
- 低频：每日2次（北京时间23:00, 05:00，基本面+策略）
- 周报：每周日23:00（总结与调整）
```

**B. 事件触发（二期）**
```
- 价格异常波动（>5% in 1h）
- 重大新闻事件（新闻API接入）
- 账户风险预警（回撤>预设值）
```

#### Prompt模板设计
```python
# 策略分析师Prompt模板
STRATEGIST_PROMPT = """
【角色】你是资深数字货币策略分析师
【输入数据】{market_data} + {account_status}
【任务】基于以下维度分析：
1. 趋势判断：短期/中期趋势方向
2. 关键价位：重要支撑/阻力位
3. 风险收益比评估
4. 仓位管理建议
【输出格式】JSON，包含：trend, confidence, position_size, rationale
```

```python
# 技术分析师Prompt模板  
TECHNICAL_PROMPT = """
【角色】你是技术分析专家，只关注图表
【输入数据】{indicators} + {price_action}
【任务】技术分析：
1. 多时间框架分析（1h, 4h, 1d）
2. 指标信号一致性检查
3. 形态识别（头肩顶、三角形等）
【输出格式】JSON，包含：signals, patterns, targets, stop_loss
```

```python
# 风险评估师Prompt模板
RISK_PROMPT = """
【角色】你是严格的风险控制官
【输入数据】{account_status} + {market_volatility}
【任务】风险评估：
1. 当前仓位风险度（1-10分）
2. 建议最大仓位上限
3. 止损位置计算
4. 黑天鹅事件预案
【输出格式】JSON，包含：risk_score, max_position, stop_loss_levels, warnings
```

### 3. 决策汇总层
#### 多模型结果聚合算法
```
输入：各模型输出结果（JSON格式）
处理：
  1. 冲突检测 → 标记不一致的决策点
  2. 加权投票 → 基于模型历史准确率加权
  3. 风险过滤 → 应用风险控制规则
  4. 账户适配 → 调整建议适应实际账户状态
输出：最终交易方案 + 各模型观点对比
```

#### 输出格式
```json
{
  "timestamp": "2024-01-20 23:00:00",
  "final_decision": {
    "action": "BUY/BUY_LIMIT/SELL/SELL_LIMIT/HOLD",
    "symbol": "BTCUSDT",
    "recommended_size": "0.05 BTC",
    "entry_price": "42000.00",
    "take_profit": ["43000.00", "44000.00"],
    "stop_loss": "41000.00",
    "timeframe": "4h-1d",
    "confidence": 7.5
  },
  "model_consensus": {
    "agreement_level": "HIGH/MEDIUM/LOW",
    "conflicting_points": ["entry_price", "position_size"],
    "details": {
      "deepseek": {...},
      "qwen": {...},
      "gpt4": {...}
    }
  },
  "risk_assessment": {
    "position_risk": "LOW/MEDIUM/HIGH",
    "max_drawdown_estimate": "3.2%",
    "recommended_capital_usage": "15%"
  }
}
```

## 🔧 技术实现方案

### 开发阶段规划
#### 第一阶段：MVP（2-3周）
```
功能范围：
  ✅ 单一交易所数据获取（币安）
  ✅ 基础技术指标计算（RSI, MACD, MA）
  ✅ 单个LLM分析（DeepSeek）
  ✅ 简单决策输出（JSON格式）
  ✅ 人工手动执行
  
技术栈：
  - 数据获取：ccxt + python-binance
  - 指标计算：TA-Lib / pandas_ta
  - LLM调用：openai兼容SDK
  - 任务调度：APScheduler
  - 数据存储：SQLite
```

#### 第二阶段：多模型系统（3-4周）
```
新增功能：
  🔄 多LLM并行分析（Qwen + GPT-4）
  🔄 决策聚合算法（加权投票）
  🔄 账户状态集成
  🔄 风险控制模块
  🔄 简单回测验证
  
技术增强：
  - 异步处理：asyncio + aiohttp
  - 缓存优化：Redis
  - 配置管理：YAML配置文件
```

#### 第三阶段：高级功能（4-6周）
```
扩展功能：
  🔄 模拟交易引擎
  🔄 实时监控告警
  🔄 性能分析面板
  🔄 事件驱动触发
  
技术完善：
  - API服务：FastAPI
  - 前端面板：Streamlit / Vue.js
  - 部署：Docker容器化

```

### 关键接口定义
```python
# 核心接口类
class TradingDecisionSystem:
    def fetch_market_data(self, symbol: str, timeframe: str) -> Dict
    def fetch_account_data(self) -> Dict
    def calculate_indicators(self, ohlcv: pd.DataFrame) -> Dict
    def analyze_with_llm(self, model: str, prompt_template: str, data: Dict) -> Dict
    def aggregate_decisions(self, model_outputs: List[Dict]) -> Dict
    def validate_decision(self, decision: Dict, account: Dict) -> bool
    def generate_execution_plan(self, decision: Dict) -> Dict
```

### 配置文件示例（config.yaml）
```yaml
# 交易所配置
exchange:
  name: "binance"
  api_key: "${BINANCE_API_KEY}"
  secret: "${BINANCE_SECRET}"
  symbols: ["BTCUSDT", "ETHUSDT"]
  timeframes: ["1h", "4h", "1d"]

# 模型配置
models:
  deepseek:
    api_key: "${DEEPSEEK_API_KEY}"
    base_url: "https://api.deepseek.com"
    role: "strategist"
    weight: 0.4
    
  qwen:
    api_key: "${QWEN_API_KEY}"
    base_url: "https://dashscope.aliyuncs.com"
    role: "technical"
    weight: 0.3

# 分析配置
analysis:
  schedule:
    - time: "23:00"
      type: "strategic"
    - time: "05:00" 
      type: "strategic"
    - time: "*:00"
      type: "technical"
  
  risk_limits:
    max_position_percent: 20
    max_daily_loss: 5
    stop_loss_default: 2

# 输出配置
output:
  format: "json"
  destinations:
    - type: "file"
      path: "./logs/decisions/"
    - type: "email"
      enabled: false
    - type: "telegram"
      enabled: false
```

## 🚦 风险控制与合规

### 强制安全措施
```
1. 资金安全
   - 仅使用只读API密钥（初期）
   - 模拟账户至少运行30天
   - 实盘资金不超过总投资5%

2. 系统安全
   - 关键配置环境变量化
   - API密钥加密存储
   - 操作审计日志

3. 决策安全
   - 所有建议必须包含止损
   - 单次建议仓位≤20%总资金
   - 高风险时段自动降低仓位
```

### 验证与测试方案
```
阶段验证：
  1. 历史回测（6个月数据）
  2. 模拟交易（30天，虚拟资金）
  3. 小资金实盘（1个月，≤1000USDT）
  4. 逐步扩大（每阶段收益验证）

质量指标：
  - 方向预测准确率 > 55%
  - 盈亏比 > 1.5
  - 最大回撤 < 15%
  - 月收益率 > 5%
```

## 📋 验收标准（MVP版本）

### 功能验收
- [ ] 能够定时获取BTC/USDT 1小时K线数据
- [ ] 正确计算至少3个技术指标（RSI, MACD, MA20）
- [ ] 调用DeepSeek API并返回结构化JSON
- [ ] 生成包含具体参数的交易建议
- [ ] 每日在指定时间自动运行
- [ ] 输出结果可读性良好

### 性能验收  
- [ ] 单次分析耗时 < 30秒
- [ ] 系统可连续运行7天无崩溃
- [ ] API调用错误有重试机制
- [ ] 数据获取失败有降级方案

### 文档验收
- [ ] 完整的README安装说明
- [ ] 配置示例文件
- [ ] API密钥设置指南
- [ ] 常见问题解答

## 🎯 下一步具体行动

### 本周目标（第一周）
1. **完成环境搭建**
   - Python 3.9+环境
   - 安装依赖包：ccxt, pandas, openai
   - 获取币安API（只读权限）

2. **实现数据获取**
   - 编写币安数据获取模块
   - 实现技术指标计算
   - 数据本地存储（CSV格式）

3. **完成第一个LLM调用**
   - 配置DeepSeek API
   - 设计基础prompt模板
   - 实现JSON解析输出

4. **创建简单调度**
   - 使用APScheduler定时任务
   - 每天北京时间23点运行
   - 日志记录每次运行结果

### 需要明确的技术决策点
```
1. LLM选择：
   - 初期：DeepSeek（性价比高）
   - 扩展：Qwen + GPT-4（对比验证）

2. 数据存储：
   - 简单版：CSV文件 + SQLite
   - 进阶版：PostgreSQL + 时序数据库

3. 部署方式：
   - 本地运行：Python脚本
   - 服务器部署：Docker容器
   - 云服务：AWS/GCP/Azure
```
