# khQuant 函数 → 大QMT 写法对照（原生改写路线）

走兼容层路线时不需要读这份，兼容层已经提供了同名函数。用户要一份不依赖兼容层、按 QMT 官方写法的策略（比如准备转实盘、或想让代码更短），再按这份改写。

## 目录

1. 结构对照
2. 时间、行情、账户、持仓
3. 历史数据和指标
4. 下单
5. khQuant 有、QMT 没有的写法怎么替代
6. 原生回测骨架

---

## 1. 结构对照

| khQuant | 大QMT 内置 Python |
|---|---|
| `from khQuantImport import *` | 删除；需要的库自己 import（numpy、pandas、talib 内置） |
| `init(stock_codes, init_data)` | `init(C)`：只跑一次。`get_trading_dates` 这类函数要放到 `after_init(C)` |
| `khHandlebar(data) -> List[Dict]` | `handlebar(C)`：历史每根 K 线一次；没有返回值，直接下单 |
| `khPreMarket(data)` / `khPostMarket(data)` | 没有。回测里在 `handlebar` 里判断「新的一天的第一根」做盘前逻辑；盘后逻辑放到当天最后一根之后或第二天第一根之前（见第 5 节） |
| 模块全局变量存状态 | 照常用模块全局变量或自建空类实例；不要往 `C` 上挂自定义属性（每根 K 线会回滚） |
| `logging.info(...)` | `print(...)` |
| 文件编码 UTF-8，第一行 `# coding: utf-8` | 第一行 `#coding:gbk`，文件按 GBK 保存 |

## 2. 时间、行情、账户、持仓

| khQuant | 大QMT |
|---|---|
| `khGet(data, 'date_num')` | `timetag_to_datetime(C.get_bar_timetag(C.barpos), '%Y%m%d')` |
| `khGet(data, 'datetime_str')` | `timetag_to_datetime(C.get_bar_timetag(C.barpos), '%Y-%m-%d %H:%M:%S')` |
| `khGet(data, 'stocks')` | 策略里写死的股票池列表，或 `C.get_stock_list_in_sector('沪深300')`（QMT 板块名） |
| `khPrice(data, code, 'open')` | `C.get_market_data_ex(['open'], [code], period=C.period, end_time=bar_time, count=1, subscribe=False)[code]['open'].iloc[-1]`；先确认最后一行就是当前这根（停牌时可能是前一天） |
| `khGet(data, 'cash')` | `get_trade_detail_data(acct, 'stock', 'account')[0].m_dAvailable` |
| `khGet(data, 'total_asset')` | 同上 `.m_dBalance` |
| `khGet(data, 'positions')` | `get_trade_detail_data(acct, 'stock', 'position')`，每个对象：`m_strInstrumentID + '.' + m_strExchangeID` 为代码，`m_nVolume` 持仓，`m_nCanUseVolume` 可卖，`m_dOpenPrice` 成本 |
| `khHas(data, code)` | 上面持仓字典里有这只且 `m_nVolume > 0` |
| `get_stock_name(code)` | `C.get_instrument_detail(code)['InstrumentName']`（`C.get_stock_name` 手册说以后会废弃） |
| `is_trade_day(d)` | `C.get_trading_dates(code, start, end, count, '1d')`，只能在 `after_init` / `handlebar` 里调用 |

回测账号：任意字符串，查询和下单用同一个（not-supported.md C1）。实盘账号来自模型交易界面的全局变量 `account`、`accountType`（见 live-trading.md）。

## 3. 历史数据和指标

**khHistory 不含截止那一根，`get_market_data_ex(end_time=...)` 含。** 这是改写时最容易引入未来数据或错一根的地方：

```python
bar_time = timetag_to_datetime(C.get_bar_timetag(C.barpos), '%Y%m%d%H%M%S')
df = C.get_market_data_ex(['close'], [code], period='1d', end_time=bar_time,
                          count=N + 1, dividend_type='front', fill_data=False,
                          subscribe=False)[code]
# 去掉当前这一根（日线按日期比，分钟按到分钟比）；停牌时最后一行可能不是今天，不能直接 iloc[:-1]
df = df[[str(i).replace('-', '')[:8] < bar_time[:8] for i in df.index]].tail(N)
```

| khQuant | 大QMT |
|---|---|
| `khHistory(codes, fields, n, '1d', current_time=...)` | 上面的写法；`fq='pre'/'post'/'none'` 对应 `dividend_type='front'/'back'/'none'`，不写时用 `.kh` 的复权方式 |
| `khMA(code, n, end_time=...)` | 上面取 n 根收盘价求均值，再按价格精度四舍五入；不足 n 根时跳过 |
| MyTT 指标（`MA`、`EMA`、`MACD`、`KDJ`、`RSI`、`BOLL` 等） | 从 khQuant 的 `MyTT.py` 复制用到的函数进策略文件（纯 numpy/pandas）；或改用内置 `talib`（参数和口径要核对，例如 MyTT 的 `SMA` 是中国式 SMA，和 talib 的 SMA 不同） |
| `khKline(code, '15m', n)` | `get_market_data_ex(..., period='15m')`，需要已下载 5m；最后一根是否收线自己判断 |
| 缠论工具 `is_bottom_fractal` 等 | 从 `khChanLunTools.py` 复制用到的函数 |
| `get_market_data_ex(subscribe=True)` | 回测里不要用；订阅模式有数量上限（单次不超过 500 只），回测一律 `subscribe=False` |

`fill_data` 默认 True 会给停牌日补数据；khQuant 本地库停牌日一般没有新数据，迁移时建议 `fill_data=False`，并用 `dropna` 去掉空行。

## 4. 下单

| khQuant | 大QMT |
|---|---|
| 返回 `{'code', 'action': 'buy', 'price', 'volume'}` | `passorder(23, 1101, acct, code, 11, price, volume, C)` |
| `'action': 'sell'` | `passorder(24, 1101, acct, code, 11, price, volume, C)` |
| `volume` 单位是股 | `orderType=1101` 时股票的 `volume` 也是股 |
| `generate_signal(data, code, price, ratio, 'buy')` | 自己算股数：`可用资金 × ratio ÷ (价格 × (1 + 滑点) × (1 + 佣金率))` 向下取整到 100 股，再扣最低佣金检查；或用 `orderType=1123`（按可用资金比例）让 QMT 算，但口径和 khQuant 不同 |
| `generate_signal(..., 'sell')` 卖可卖数量 × ratio，取整到 100 股 | 用 `m_nCanUseVolume` 计算 |
| 不写 `order_type`（市价单）按信号价成交 | 用指定价 `prType=11` 下单，价格要落在当根最低价和最高价之间，否则回测按收盘价成交 |
| `prType=5`（最新价） | 回测里相当于按当根收盘价成交，和 khQuant 用开盘价下单的策略口径不同，不要混用 |

手写信号常见问题：khQuant 不会替手写信号取整到 100 股，QMT 实盘里不足一手会废单（科创板 200 股起）。

**滑点**：QMT 回测参数里「滑点」一项的单位手册没写，不要依赖它，界面填 0，在代码里处理。两种做法：

- 委托价不加滑点，把单边滑点比例加进 QMT 的佣金率（例如单边 0.5% 就在佣金率上加 0.005）。委托价总在当根高低点内，资金曲线最接近 khQuant；代价是操作明细里的成交价不含滑点，手续费偏高。滑点大时用这种。
- 把滑点加进委托价，取整到分。委托价超出当根高低点时只能按端点下单，滑点被吞掉一部分。滑点每股不到一分钱时用这种：khQuant 取整后本来就常常没有滑点。

不管哪种，算买入股数时都要按 QMT 实际收费口径（委托价 × 股数 × (1 + 佣金率)，不低于最低佣金）核一遍资金，否则满仓买入会因差几十元被拒单。

## 5. khQuant 有、QMT 没有的写法怎么替代

**限价单 / 止损单 / 挂单**：在全局变量里维护自己的挂单列表，每根 K 线读当根开高低：

```python
# 买入限价单：当根最低价 <= 限价时成交，开盘价已低于限价按开盘价
if bar_low <= limit_price:
    fill = bar_open if bar_open <= limit_price else limit_price
    passorder(23, 1101, acct, code, 11, fill, volume, C)
# 卖出止损单：当根最低价 <= 止损价时触发，跳空低开按开盘价
if bar_low <= stop_price:
    fill = min(max(min(stop_price, bar_open), bar_low), bar_high)
    passorder(24, 1101, acct, code, 11, fill, volume, C)
```

这里读当根高低点是在模拟撮合，策略判断本身不能用当根的收盘价、最高价、最低价，否则就成了未来数据。

**盘前回调**：在新的一天第一根 K 线时、做别的事之前执行，只能用前一天及更早的数据。

**盘后回调**：日线回测里放在当根 `handlebar` 的最后（这时当天日线已完整），把信号存进全局列表，第二天第一根按限价单处理，当天收盘还没成交就作废。

**日内多次触发（先卖后买）**：同一次 `handlebar` 里先发卖单，再按「卖出后预计资金」算买入股数下买单。回测里卖出资金是否当根可用需实测（not-supported.md C3），不可用时把买单放到下一根。

**涨跌停**：按 `preClose` × (1 ± 涨跌幅) 两位小数取整算出当日涨跌停价（科创板、创业板 20%，北交所 30%，其余 10%）。当根最高最低价超出这个区间时（复权价配不复权昨收、除权日、新股）跳过校验。khQuant 的规则（兼容层照做）：
- 市价单（不写 `order_type` 的信号、`generate_signal`）不校验，收盘封涨停也照样成交；
- 回调当根发出的限价、止损、止损限价单：一字涨停不买、收盘封涨停不买（跌停同理），限价越出涨跌停直接拒单，拒单后不进挂单簿；
- 挂单簿里的单：能成交的那根如果封板或限价越界，本根不成交、继续挂着；
- 和复权方式无关：只要 `.kh` 的 `data.fields` 里有 `preClose` 就校验。khQuant 的 `preClose` 是不复权价，前复权回测里配上复权 K 线，部分日子会按不复权昨收误判（实测一个前复权限价单策略被拒了几笔）。

`get_instrument_detail` 的 `UpStopPrice` 只对当天有效，回测里不能用。

## 6. 原生回测骨架

```python
#coding:gbk
import numpy as np

class G():
    pass
g = G()

ACCT = 'kh_backtest'
POOL = ['000001.SZ']

def init(C):
    g.last_date = ''
    C.start = '2024-01-01 00:00:00'
    C.end = '2024-12-31 23:59:59'
    C.capital = 1000000

def handlebar(C):
    bar_time = timetag_to_datetime(C.get_bar_timetag(C.barpos), '%Y%m%d%H%M%S')
    today = bar_time[:8]
    if today != g.last_date:
        g.last_date = today
        # 盘前逻辑放这里
    cur = C.get_market_data_ex(['open', 'high', 'low', 'close'], POOL, period=C.period,
                               end_time=bar_time, count=1, subscribe=False)
    acc = get_trade_detail_data(ACCT, 'stock', 'account')
    cash = acc[0].m_dAvailable if acc else 0.0
    holds = {p.m_strInstrumentID + '.' + p.m_strExchangeID: p
             for p in get_trade_detail_data(ACCT, 'stock', 'position') if p.m_nVolume > 0}
    for code in POOL:
        df = cur.get(code)
        if df is None or len(df) == 0 or str(df.index[-1]).replace('-', '')[:8] != today:
            continue  # 今天没有这只的 K 线
        bar = df.iloc[-1]
        # ……策略判断，只用开盘价和历史数据……
        # 买：passorder(23, 1101, ACCT, code, 11, round(bar['open'], 2), vol, C)
        # 卖：passorder(24, 1101, ACCT, code, 11, round(bar['open'], 2), holds[code].m_nCanUseVolume, C)
```
