# 策略开发指南

## 创建新策略

```bash
kh strategy create 我的策略
```

自动生成两个文件：
- `我的策略.py` — 策略代码（含标准回调函数模板）
- `我的策略.kh` — 回测配置（默认参数）

可指定输出目录：

```bash
kh strategy create 我的策略 --dir D:\CLIstrategies
```

## 策略管理命令

```bash
# 列出所有策略（显示配套 .kh 文件名）
kh strategy list

# 校验策略是否符合框架要求（会实际加载模块）
kh strategy validate D:\CLIstrategies\我的策略.py

# 静态分析策略信息（AST 解析，不执行代码）
kh strategy info D:\CLIstrategies\我的策略.py
```

- `validate` — 实际加载并执行模块代码，检查必需函数是否存在
- `info` — 纯 AST 静态分析，更安全，显示函数列表和导入依赖

---

## 策略文件结构

每个策略是一个标准 Python 文件，通过 `from khQuantImport import *` 导入所有 API 函数和常用库。

### 回调函数

| 函数 | 级别 | 签名 | 调用时机 | 返回值 |
|------|------|------|---------|--------|
| `init(stock_list, data)` | 推荐 | `init(stock_list: list, data: dict)` | 回测开始前调用一次 | 无 |
| `khHandlebar(data)` | **必需** | `khHandlebar(data: Dict) -> List[Dict]` | 每根 K 线 / 每次触发 | 信号列表 |
| `khPreMarket(data)` | 可选 | `khPreMarket(data: Dict) -> List[Dict]` | 每个交易日开盘前 | 信号列表 |
| `khPostMarket(data)` | 可选 | `khPostMarket(data: Dict) -> List[Dict]` | 每个交易日收盘后 | 信号列表 |

### data 字典结构

`khHandlebar(data)` 收到的 data 包含：

| Key | 类型 | 内容 |
|-----|------|------|
| `"__current_time__"` | dict | 当前时间：`{date, time, datetime, timestamp, raw_time, _dt}` |
| `"__account__"` | dict | 账户资金：`{cash, total_asset, market_value, ...}` |
| `"__positions__"` | dict | 持仓：每只股票含 `{volume, can_use_volume, avg_price, current_price, market_value, ...}` |
| `"__stock_list__"` | list | 股票池代码列表 |
| `"__framework__"` | object | 框架核心类实例（策略代码一般不直接使用）|
| 股票代码（如 `"000001.SZ"`） | Series | OHLCV 行情 + `khAddExtraFields` 注入的自定义指标字段 |

### 交易信号格式

```python
{
    "code": "000001.SZ",    # 股票代码（必须含交易所后缀）
    "action": "buy",         # buy 或 sell
    "price": 10.50,          # 委托价格
    "volume": 100,           # 委托数量（必须是 100 的整数倍）
    "reason": "金叉信号",     # 交易理由（记录到交易日志）
    "timestamp": 1700000000  # 时间戳（generate_signal 自动填充）
}
```

---

## 数据获取 API

### khGet(data, key) — 万能数据获取

从 data 字典中安全提取各类信息，无需手写嵌套字典访问。

```
khGet(data: Dict, key: str) -> Any
```

| key 值 | 返回类型 | 说明 |
|--------|---------|------|
| `'date_str'` / `'date'` | str | `"YYYY-MM-DD"` 格式日期 |
| `'date_num'` | str | `"YYYYMMDD"` 格式日期 |
| `'time_str'` / `'time'` | str | `"HH:MM:SS"` 格式时间 |
| `'datetime_str'` / `'datetime'` | str | `"YYYY-MM-DD HH:MM:SS"` |
| `'datetime_obj'` | datetime | Python datetime 对象 |
| `'timestamp'` | int | Unix 时间戳 |
| `'cash'` | float | 可用资金 |
| `'market_value'` | float | 持仓总市值 |
| `'total_asset'` | float | 总资产 |
| `'stocks'` | List[str] | 股票池完整列表 |
| `'first_stock'` | str | 股票池第一只股票代码 |
| `'positions'` | Dict | 完整持仓字典 |

键不存在时返回安全默认值（None / 0.0 / []）。

### khPrice(data, stock_code, field) — 获取行情价格

```
khPrice(data: Dict, stock_code: str, field: str = 'close') -> float
```

- 支持字段：`'open'`, `'high'`, `'low'`, `'close'`, `'volume'`, `'amount'` 等
- tick 场景下 `field='close'` 自动映射为 `lastPrice`
- 数据不存在时安全返回 `0.0`

### khIndex(data, stock_code, field) — 获取自定义指标值

```
khIndex(data: Dict, stock_code: str, field: str) -> float
```

- **field 为必填参数**（无默认值），与 khPrice 不同
- 读取通过 `khAddExtraFields` 预注入的指标（如 `'MA_20'`, `'RSI_14'`, `'DIF'`, `'DEA'`, `'MACD'`）
- 与 khPrice 底层相同，语义区分使代码更清晰
- field 名称必须与 DuckDB 中存储的列名完全一致
- 数据不存在时返回 `0.0`

### khHas(data, stock_code) — 判断持仓

```
khHas(data: Dict, stock_code: str) -> bool
```

快速判断是否持有某只股票。

### khAddExtraFields(context, fields) — 注入自定义指标字段

```
khAddExtraFields(context: Dict, fields: List[str]) -> None
```

**只能在 `init` 函数中调用**。告知框架在批量加载行情数据时顺带从 DuckDB 读入指定指标字段，使 `khHandlebar` 中可以用 `khIndex` 零 I/O 读取。

```python
def init(stock_list, data):
    khAddExtraFields(data, ["MA_20", "RSI_14", "DIF", "DEA", "MACD"])
```

### khRequestNextDailyTrigger() — 申请当日下一次触发

```
khRequestNextDailyTrigger() -> bool
```

- 仅 1d 模式有效，需配合 `.kh` 配置中 `daily_trigger_cap > 1`
- 申请成功返回 True；已达上限或非 1d 模式返回 False
- 再次触发时 data 与上一次完全相同，策略需用全局变量区分状态

---

## 历史数据与指标计算

### khHistory — 获取历史 K 线数据

```
khHistory(symbol_list, fields, bar_count, fre_step,
          current_time=None, skip_paused=False, fq='pre', force_download=False)
```

| 参数 | 类型 | 说明 |
|------|------|------|
| `symbol_list` | list/str | 一个或多个股票代码 |
| `fields` | list | 行情字段（`'open'`, `'close'`, `'high'`, `'low'`, `'volume'`, `'amount'` 等）|
| `bar_count` | int | K 线数量 |
| `fre_step` | str | K 线周期：`'1m'`, `'5m'`, `'1d'` |
| `current_time` | str | 截止时间（**不含**该时间点的数据）。**回测中必须传入当前时间，防止读取未来数据** |
| `skip_paused` | bool | 是否跳过停牌日（默认 False）|
| `fq` | str | 复权类型（默认 `'pre'`）|
| `force_download` | bool | 是否强制下载新数据（默认 False）|

`current_time` 支持格式：`"YYYYMMDD"`, `"YYYY-MM-DD"`, `"YYYYMMDDHHMMSS"`, `"YYYY-MM-DD HH:MM:SS"`

返回值：`dict`，键为股票代码，值为 `pandas.DataFrame`。

```python
# 日线策略获取过去 20 天数据
current_date = khGet(data, 'date_num')
hist = khHistory('000001.SZ', ['close'], 20, '1d', current_time=current_date)

# 分钟策略获取过去 60 分钟数据
current_time = khGet(data, 'datetime_str')
hist = khHistory('000001.SZ', ['close', 'volume'], 60, '1m', current_time=current_time)
```

### khDuckDB — 读取本地 DuckDB 历史数据

```
khDuckDB(stock_list, period, fields=None, start_time=None, end_time=None,
         dividend_type='none', duckdb_path=None, return_format='dict')
```

| 参数 | 说明 |
|------|------|
| `stock_list` | 股票代码列表 |
| `period` | `'1d'`, `'1m'`, `'5m'`, `'tick'` |
| `fields` | 返回字段列表，None 返回全部 |
| `start_time` / `end_time` | `'YYYYMMDD'` 或 `'YYYYMMDDHHmmss'` |
| `dividend_type` | `'none'`, `'front'`, `'back'`, `'front_ratio'`, `'back_ratio'` |

返回值：`dict`，键为股票代码，值为 DataFrame。

> **性能警告**：在 `khHandlebar` 中调用 khDuckDB 每根 K 线都会触发一次数据库 I/O。推荐使用下方的高性能模式。

### khMA — 移动平均线

```
khMA(stock_code: str, period: int, field: str = 'close',
     fre_step: str = '1d', end_time: str = None, fq: str = 'pre', data: Dict = None) -> float
```

回测中建议传入 `end_time` 避免未来数据。

---

## 高性能指标模式（推荐）

在回测数百只股票、跨越数年时，应避免在 `khHandlebar` 中反复调用 khDuckDB。推荐三步模式：

**第一步 — 数据准备**（独立脚本，非策略文件）：使用 `khDuckWrite` 把预计算指标写入 DuckDB。

**第二步 — 策略 init**：注册指标字段，框架一次性加载到内存。

```python
def init(stock_list, data):
    khAddExtraFields(data, ["DIF", "DEA", "MACD"])
```

**第三步 — 策略 khHandlebar**：零 I/O 读取。

```python
def khHandlebar(data):
    stock = khGet(data, 'first_stock')
    dif  = khIndex(data, stock, "DIF")
    dea  = khIndex(data, stock, "DEA")
    macd = khIndex(data, stock, "MACD")
```

对比：

| 方式 | I/O 次数（1000 天 × 100 股） | 性能 |
|------|------------------------------|------|
| khDuckDB 在 khHandlebar | 100,000 次 | 极慢 |
| khAddExtraFields + khIndex | 1 次 | 极快 |

---

## 交易辅助函数

### generate_signal — 智能信号生成（推荐）

```
generate_signal(data: Dict, stock_code: str, price: float,
                ratio: float, action: str, reason: str = "") -> List[Dict]
```

| 参数 | 说明 |
|------|------|
| `data` | 数据对象 |
| `stock_code` | 股票代码 |
| `price` | 交易价格 |
| `ratio` | **买入时** ≤1 为资金使用比例（0.5=50% 资金），>1 为目标股数（须为 100 整数倍）；**卖出时** 为持仓卖出比例（1.0=全部）|
| `action` | `'buy'` 或 `'sell'` |
| `reason` | 交易原因 |

返回 `List[Dict]`。条件不满足（资金不足/无仓可卖）返回空列表。

**重要**：
- 买入自动调用 `calculate_max_buy_volume` 验证资金充足性
- `ratio > 1` 时必须为 100 的整数倍，否则返回空列表
- 指定股数超过最大可买入量时自动调整
- **必须用 `signals.extend()`，不能用 `signals.append()`**

```python
# 买入：使用 50% 可用资金
buy = generate_signal(data, stock, price, 0.5, 'buy', "金叉买入")
signals.extend(buy)

# 卖出：全部卖出
sell = generate_signal(data, stock, price, 1.0, 'sell', "死叉卖出")
signals.extend(sell)

# 买入：指定股数
buy = generate_signal(data, stock, price, 1000, 'buy', "定量买入1000股")
signals.extend(buy)
```

### 挂单管理 API

以下函数用于查询和取消未成交的挂单：

| 函数 | 签名 | 说明 |
|------|------|------|
| `khGetPendingOrders(data, code=None)` | `-> List[Dict]` | 获取未成交挂单列表，可按股票代码过滤 |
| `khCancelOrder(data, order_id)` | `-> bool` | 取消指定挂单 |
| `khCancelOrdersByCode(data, code)` | `-> int` | 取消指定股票的所有挂单，返回取消数量 |
| `khCancelAllOrders(data)` | `-> int` | 取消所有挂单，返回取消数量 |
| `khGetPendingSummary(data)` | `-> Dict` | 获取挂单汇总：`{total_count, buy_count, sell_count, total_buy_volume, total_sell_volume}` |
| `khIsMatchEngineEnabled(data)` | `-> bool` | 检查撮合引擎是否启用 |

### 其他辅助函数

| 函数 | 签名 | 说明 |
|------|------|------|
| `parse_context(data)` | `-> StrategyContext` | 便捷函数，等价于 `StrategyContext(data)` |
| `get_default_risk_params()` | `-> Dict` | 返回默认风控参数：`{max_position: 1.0, max_single_position: 0.3, stop_loss: 0.1, stop_profit: 0.2}` |
| `calculate_max_buy_volume(data, stock_code, price, cash_ratio=1.0)` | `-> int` | 计算指定价格和资金比例下的最大可买入股数（已扣除交易成本）|

### 辅助类（khQuantImport）

| 类 | 用途 | 主要属性/方法 |
|-----|------|-------------|
| `TimeInfo(data)` | 时间访问 | `.date_str`、`.date_num`、`.time_str`、`.datetime_str`、`.datetime_num`、`.datetime_obj`、`.timestamp` |
| `StockDataParser(data)` | 行情访问 | `.get_close(code)`、`.get_open(code)`、`.get_high(code)`、`.get_low(code)`、`.get_volume(code)`、`.get_price(code, field)` |
| `PositionParser(data)` | 持仓查询 | `.has(code)`、`.get_volume(code)`、`.get_cost(code)`、`.get_all()` |
| `StockPoolParser(data)` | 股票池 | `.get_all()`、`.size()`、`.contains(code)`、`.first()` |
| `StrategyContext(data)` | 统一访问 | `.time`(TimeInfo)、`.stocks`(StockDataParser)、`.positions`(PositionParser)、`.pool`(StockPoolParser) |

---

## 时间工具函数

### is_trade_time()

```
is_trade_time() -> bool
```

判断当前是否处于 A 股交易时间（09:30-11:30, 13:00-15:00）。

### is_trade_day(date_str)

```
is_trade_day(date_str: str = None) -> bool
```

判断指定日期是否为 A 股交易日（自动剔除周末和法定节假日）。支持 `"YYYY-MM-DD"` 和 `"YYYYMMDD"` 格式，留空判断当天。

### get_trade_days_count(start_date, end_date)

```
get_trade_days_count(start_date: str, end_date: str) -> int
```

计算两个日期之间的交易日天数。日期格式 `"YYYY-MM-DD"`。

---

## 技术指标计算（MyTT 库）

KhQuant 集成了 MyTT 技术指标库（100+ 种指标，纯 Python，无需 ta-lib）。使用模式：先用 khHistory 获取历史数据，再传入 MyTT 计算。

### 基本用法

```python
current_time = khGet(data, 'datetime_str')
hist = khHistory([stock], ["close", "high", "low", "volume"], 60, "1d",
                 current_time=current_time)
CLOSE = hist[stock]["close"].values
HIGH  = hist[stock]["high"].values
LOW   = hist[stock]["low"].values
VOL   = hist[stock]["volume"].values

# 计算指标
ma5  = MA(CLOSE, 5)[-1]
ma20 = MA(CLOSE, 20)[-1]
rsi  = RSI(CLOSE, 14)[-1]
dif, dea, macd = MACD(CLOSE, 12, 26, 9)
k, d, j = KDJ(CLOSE, HIGH, LOW, 9, 3, 3)
upper, mid, lower = BOLL(CLOSE, 20, 2)
```

### 核心工具函数

**数学运算**：

| 函数 | 说明 |
|------|------|
| `RD(N, D=3)` | 四舍五入取 D 位小数 |
| `RET(S, N=1)` | 返回序列倒数第 N 个值 |
| `ABS(S)` | 绝对值 |
| `LN(S)` | 自然对数 |
| `POW(S, N)` | S 的 N 次方 |
| `SQRT(S)` | 平方根 |
| `MAX(S1, S2)` | 序列最大值 |
| `MIN(S1, S2)` | 序列最小值 |
| `IF(S, A, B)` | 布尔判断（S 为真返回 A，否则 B）|

**序列操作**：

| 函数 | 说明 |
|------|------|
| `REF(S, N=1)` | 序列后移 N 位（获取历史值）|
| `DIFF(S, N=1)` | 序列差分 |
| `SUM(S, N)` | N 日累计和 |
| `STD(S, N)` | N 日标准差 |
| `CONST(S)` | 序列末尾值扩展为等长常量 |

**条件判断**：

| 函数 | 说明 |
|------|------|
| `COUNT(S, N)` | N 日内满足条件的天数 |
| `EVERY(S, N)` | N 日内全部满足条件 |
| `EXIST(S, N)` | N 日内存在满足条件 |
| `CROSS(S1, S2)` | 向上金叉判断 |
| `LONGCROSS(S1, S2, N)` | 持续 N 周期后交叉 |
| `FILTER(S, N)` | 条件成立后屏蔽后续 N 周期 |

**序列统计**：

| 函数 | 说明 |
|------|------|
| `HHV(S, N)` | N 日最高价 |
| `LLV(S, N)` | N 日最低价 |
| `HHVBARS(S, N)` | N 日内最高价到当前的周期数 |
| `LLVBARS(S, N)` | N 日内最低价到当前的周期数 |
| `BARSLAST(S)` | 上一次条件成立到当前的周期数 |
| `BARSLASTCOUNT(S)` | 连续满足条件的周期数 |

### 技术指标函数

**均线类**：

| 函数 | 说明 |
|------|------|
| `MA(S, N)` | N 日简单移动平均 |
| `EMA(S, N)` | 指数移动平均 |
| `SMA(S, N, M=1)` | 中国式 SMA |
| `WMA(S, N)` | 加权移动平均 |
| `DMA(S, A)` | 动态移动平均 |
| `BBI(CLOSE, M1=3, M2=6, M3=12, M4=20)` | 多空均线 |

**趋势类**：

| 函数 | 说明 |
|------|------|
| `MACD(CLOSE, SHORT=12, LONG=26, M=9)` | 返回 (DIF, DEA, MACD) |
| `DMI(CLOSE, HIGH, LOW, M1=14, M2=6)` | 动向指标 |
| `TRIX(CLOSE, M1=12, M2=20)` | 三重指数平滑均线 |
| `SAR(HIGH, LOW, N=10, S=2, M=20)` | 抛物线转向 |

**动量摆动类**：

| 函数 | 说明 |
|------|------|
| `RSI(CLOSE, N=24)` | 相对强弱指标 |
| `KDJ(CLOSE, HIGH, LOW, N=9, M1=3, M2=3)` | 返回 (K, D, J) |
| `WR(CLOSE, HIGH, LOW, N=10, N1=6)` | 威廉指标 |
| `CCI(CLOSE, HIGH, LOW, N=14)` | 顺势指标 |
| `BIAS(CLOSE, L1=6, L2=12, L3=24)` | 乖离率 |
| `PSY(CLOSE, N=12, M=6)` | 心理线 |
| `MTM(CLOSE, N=12, M=6)` | 动量指标 |
| `ROC(CLOSE, N=12, M=6)` | 变动率指标 |

**波动通道类**：

| 函数 | 说明 |
|------|------|
| `BOLL(CLOSE, N=20, P=2)` | 布林带，返回 (UPPER, MID, LOWER) |
| `ATR(CLOSE, HIGH, LOW, N=20)` | 平均真实波幅 |
| `KTN(CLOSE, HIGH, LOW, N=20, M=10)` | 肯特纳通道 |

**成交量类**：

| 函数 | 说明 |
|------|------|
| `OBV(CLOSE, VOL)` | 能量潮指标 |
| `VR(CLOSE, VOL, M1=26)` | 容量比率 |
| `EMV(HIGH, LOW, VOL, N=14, M=9)` | 简易波动指标 |
| `MFI(CLOSE, HIGH, LOW, VOL, N=14)` | 资金流向指标 |

**其他**：

| 函数 | 说明 |
|------|------|
| `CR(CLOSE, HIGH, LOW, N=20)` | 价格动量指标 |
| `BRAR(OPEN, CLOSE, HIGH, LOW, M1=26)` | 情绪指标 |
| `ASI(OPEN, CLOSE, HIGH, LOW, M1=26, M2=10)` | 振动升降指标 |
| `DPO(CLOSE, M1=20, M2=10, M3=6)` | 区间震荡线 |

---

## 常用字段说明

### 基础行情字段（khHistory / khDuckDB 通用）

```
time, open, high, low, close, volume, amount,
settelementPrice, openInterest, preClose, suspendFlag
```

### 复权字段（khHistory / khDuckDB 通用）

```
open_front, high_front, low_front, close_front,
open_back, high_back, low_back, close_back,
open_front_ratio, high_front_ratio, low_front_ratio, close_front_ratio,
open_back_ratio, high_back_ratio, low_back_ratio, close_back_ratio
```

### 财务与指标字段（khDuckDB 日线特有）

| 字段 | 说明 |
|------|------|
| `turn` | 换手率 |
| `pctChg` | 涨跌幅 |
| `peTTM` | 市盈率 TTM |
| `psTTM` | 市销率 TTM |
| `pcfNcfTTM` | 市现率 TTM |
| `pbMRQ` | 市净率 MRQ |
| `isST` | 是否 ST |

> 注意：khHistory 暂不支持直接获取这些字段。

### Tick 字段（khDuckDB tick 模式）

```
time, lastPrice, open, high, low, lastClose, amount, volume, pvolume, stockStatus, openInt,
askPrice1~5, bidPrice1~5, askVol1~5, bidVol1~5, transactionNum
```

---

## .kh 配置文件结构

`.kh` 文件采用 JSON 格式，包含以下配置节：

```json
{
    "system": {
        "userdata_path": "...",
        "init_data_enabled": false
    },
    "run_mode": "backtest",
    "account": {
        "account_id": "88888888",
        "account_type": "SECURITY_ACCOUNT"
    },
    "strategy_file": "策略文件路径.py",
    "data_mode": "custom",
    "backtest": {
        "start_time": "20240101",
        "end_time": "20241231",
        "init_capital": 1000000.0,
        "min_volume": 100,
        "benchmark": "sh.000300",
        "trade_cost": {
            "min_commission": 5.0,
            "commission_rate": 0.0003,
            "stamp_tax_rate": 0.001,
            "flow_fee": 0.1,
            "slippage": {
                "type": "ratio",
                "tick_size": 0.01,
                "tick_count": 2,
                "ratio": 0.001
            }
        },
        "trigger": {
            "type": "1d",
            "daily_trigger_cap": 1,
            "custom_times": ["09:30:00"],
            "start_time": "09:30:00",
            "end_time": "15:00:00",
            "interval": 300
        }
    },
    "data": {
        "kline_period": "1d",
        "dividend_type": "none",
        "fields": ["open", "high", "low", "close", "volume", "amount",
                   "settelementPrice", "openInterest", "preClose", "suspendFlag"],
        "stock_list": ["000001.SZ"]
    },
    "market_callback": {
        "pre_market_enabled": false,
        "pre_market_time": "08:30:00",
        "post_market_enabled": false,
        "post_market_time": "15:30:00"
    },
    "risk": {
        "position_limit": 0.95,
        "order_limit": 100,
        "loss_limit": 0.1
    }
}
```

### 触发方式

| type | 说明 | 适用策略 |
|------|------|---------|
| `"tick"` | Tick 级触发 | 高频策略 |
| `"1m"` | 1 分钟 K 线 | 分钟级策略 |
| `"5m"` | 5 分钟 K 线 | 短周期策略 |
| `"1d"` | 日 K 线 | 日线策略 |
| `"custom"` | 自定义定时 | 特殊时间点策略 |

### 触发与数据匹配规则

| 组合 | 正确 |
|------|------|
| trigger.type=`"1d"` + kline_period=`"1d"` + khHistory fre_step=`"1d"` | ✓ |
| trigger.type=`"1m"` + kline_period=`"1m"` + khHistory fre_step=`"1m"` | ✓ |
| trigger.type=`"tick"` + kline_period=`"1m"` | ✓ |
| trigger.type=`"1d"` + khHistory fre_step=`"1m"` | ✗ 数据不匹配 |

### 日线多次触发

1. 默认每天只触发一次 `khHandlebar`
2. 设置 `daily_trigger_cap > 1` 允许同一天内多次触发
3. 策略中调用 `khRequestNextDailyTrigger()` 申请下一次
4. 再次触发时行情数据相同（同一天），但 `__account__` 和 `__positions__` 会反映上一轮交易结果（例如第一轮卖出后，第二轮可用释放的资金买入）
5. 策略需用全局变量区分当前是第几次触发

### 复权方式

| 值 | 说明 |
|----|------|
| `"none"` | 不复权（.kh 配置默认值）|
| `"front"` | 前复权（推荐，保持当前价格真实性）|
| `"back"` | 后复权 |
| `"front_ratio"` | 等比前复权 |
| `"back_ratio"` | 等比后复权 |

> 注意：.kh 配置中 `data.dividend_type` 默认为 `"none"`，如需前复权需显式设置为 `"front"`。而 `kh data download --adj` 参数默认为 `front`，两者默认值不同。

### 滑点模式

| 类型 | 计算方式 | 示例 |
|------|---------|------|
| `"tick"` | 绝对值：`tick_size × tick_count` | tick_size=0.01, tick_count=2 → 买价+0.02，卖价-0.02 |
| `"ratio"` | 比例（**减半后应用**）：买价 × (1 + ratio/2)，卖价 × (1 - ratio/2) | ratio=0.001 → 买价×1.0005，卖价×0.9995 |

### T+0 与 T+1 模式

- **T+1**（默认）：当天买入的股票次日才能卖出（A 股标准规则）
- **T+0**：当天买入当天可卖（适用于部分 ETF）
- **T+0 模式由框架自动检测**：当股票池中全部为 T0 ETF 标的时自动启用，混合池强制 T+1
- T+0 标的列表见 `data/T0stock.txt` 和 `data/T0ETF.txt`

### 股票池配置

```json
// 方式一：直接列表
"stock_list": ["000001.SZ", "600519.SH"]

// 方式二：文件引用
"stock_list_file": "path/to/stock_list.csv"
```

---

## 日志输出

```python
import logging  # 已包含在 khQuantImport 中

logging.info("一般信息，绿色显示")
logging.warning("警告信息，橙色显示")
logging.error("错误信息，红色显示")
```

在关键决策点添加日志有助于调试和监控策略运行状态。

---

## 完整策略模板

```python
"""策略: [名称]"""
from khQuantImport import *

# ═══ 策略参数 ═══
PARAM_A = 5
PARAM_B = 20

def init(stock_list, data):
    """策略初始化 — 仅执行一次"""
    # 如需预加载指标：
    # khAddExtraFields(data, ["MA_20", "RSI_14"])
    pass

def khHandlebar(data: Dict) -> List[Dict]:
    """策略主逻辑 — 每根 K 线触发"""
    signals = []

    try:
        target_stock = khGet(data, 'first_stock')
        if not target_stock:
            return signals

        current_price = khPrice(data, target_stock)
        if current_price <= 0:
            return signals

        has_position = khHas(data, target_stock)

        # ─── 获取历史数据并计算指标 ───
        current_time = khGet(data, 'datetime_str')
        hist = khHistory([target_stock], ["close"], 30, "1d",
                         current_time=current_time)
        if target_stock not in hist or hist[target_stock].empty:
            return signals

        closes = hist[target_stock]["close"].values
        if len(closes) < PARAM_B:
            return signals

        ma_short = MA(closes, PARAM_A)[-1]
        ma_long  = MA(closes, PARAM_B)[-1]

        # ─── 交易逻辑 ───
        if ma_short > ma_long and not has_position:
            buy = generate_signal(data, target_stock, current_price,
                                  0.5, 'buy', f"金叉 MA{PARAM_A} > MA{PARAM_B}")
            signals.extend(buy)

        elif ma_short < ma_long and has_position:
            sell = generate_signal(data, target_stock, current_price,
                                   1.0, 'sell', f"死叉 MA{PARAM_A} < MA{PARAM_B}")
            signals.extend(sell)

    except Exception as e:
        logging.error(f"策略执行出错: {e}")

    return signals
```

---

## 编程规范

### 必须遵循

1. **统一导入**：使用 `from khQuantImport import *`，特殊需求才额外导入
2. **股票代码**：必须包含交易所后缀（`000001.SZ`、`600000.SH`）
3. **数据检查**：使用前检查是否为空 / None / 0
4. **持仓检查**：买入前检查是否已持仓，卖出前检查是否有仓
5. **触发匹配**：khHistory 的 `fre_step` 必须与 .kh 配置的 trigger type 和 kline_period 一致
6. **信号列表**：使用 `signals.extend()`，禁止 `signals.append()`
7. **避免未来函数**：khHistory 中必须传入 `current_time`

### 性能优化

1. 避免在 khHandlebar 中重复获取相同数据
2. 优先用 `khAddExtraFields + khIndex` 模式代替循环调用 khDuckDB
3. 使用 numpy/pandas 向量化操作
4. 合理使用全局变量缓存计算结果
5. 使用早期返回减少不必要计算

### 常见错误

| 问题 | 原因 | 修复 |
|------|------|------|
| khPrice 返回 0 | 数据不存在或无效 | `if current_price <= 0: return []` |
| 股票代码无数据 | 缺少交易所后缀 | 使用 `"000001.SZ"` 而非 `"000001"` |
| 信号未执行 | 用了 append 而非 extend | `signals.extend(buy_signals)` |
| 指标计算异常 | 历史数据不足 | 检查数据长度 + try/except |
| 读到未来数据 | khHistory 未传 current_time | 传入 `khGet(data, 'datetime_str')` |
