---
name: khquant-to-qmt
description: 把看海量化 khQuant 的回测策略（.py + .kh）迁移到迅投大QMT（券商QMT/投研端）的内置 Python 里回测，并明确列出大QMT 做不到或口径不同的部分。用户说"把策略搬到QMT""迁移到大QMT""khQuant策略在QMT里跑""改成QMT的handlebar/passorder""QMT回测和khQuant对不上""哪些功能QMT做不到""khHandlebar怎么在QMT里写""盘前盘后/挂单/止损单在QMT里怎么实现"时使用；只要任务涉及把 khHandlebar、generate_signal、khHistory、khMA 等 khQuant 写法改成 QMT 的 init(C)/handlebar(C)/get_market_data_ex/passorder，即使用户没说"迁移"两个字也要用。不用于：khQuant 自身的回测、数据下载和 miniQMT 数据源设置（用 khquant skill），以及和 khQuant 无关的 QMT 策略开发。
---

# khQuant 策略迁移到大QMT

你帮用户把 khQuant 回测策略改成能在大QMT 内置 Python 里回测的版本，并在动手前把「大QMT 做不到或做法不同」的部分讲清楚。用户多是写策略的个人投资者，回复用中文，朴实直说。

依据：khQuant V3.4.1.11 源码与官网教程；迅投知识库内置 Python 手册（dict.thinktrader.net，线上文件时间 2026-07-27）。QMT 手册没写明的行为不要替它下结论，列为「需实测」。

## 先讲清楚的三件事

1. **两边行情不同，结果不会完全一样。** QMT 回测只用 QMT 自己下载的行情；khQuant 用 BaoStock、Tushare、tdx 等数据源导入的 DuckDB 库。复权算法、停牌处理、成交量单位都可能不同，阈值附近的信号会翻转。迁移的目标是「逻辑一致、差异可解释」，不承诺收益数字相同。
2. **有些功能大QMT 做不到。** 完整清单在 `references/not-supported.md`。迁移前按用户策略实际用到的功能逐条对照，先把命中的条目告诉用户，再写代码。
3. **兼容层只用于回测。** 要在 QMT 跑模拟盘或实盘，另写实盘版，见 `references/live-trading.md`。本 skill 不替用户启动实盘、不下真实委托。

## 两条迁移路线

| 路线 | 做法 | 适合 |
|---|---|---|
| 兼容层（默认） | 把 `assets/kh_compat_qmt.py` 整个放进 QMT 策略，khQuant 策略代码基本原样贴进去 | 想在 QMT 里复现 khQuant 回测、对账 |
| 原生改写 | 按 `references/function-mapping.md` 改成 QMT 官方写法 | 准备转实盘，或想要更短的纯 QMT 代码 |

兼容层在策略内部按 khQuant 的规则判断成交，再用 QMT 的指定价下单。它模拟了：信号列表、市价/限价/止损/止损限价单与有效期、挂单查询和撤单、盘前盘后回调（日线）、日内多次触发（日线）、T+1、涨跌停拒单（规则见 not-supported.md B6）、khQuant 口径的股数计算。

滑点有两种交给 QMT 的方式（`KH_CONFIG['slippage_mode']`，见 not-supported.md B2、B16）：

- **`commission`（默认）**：委托价不加滑点，单边滑点折进 QMT 佣金率。滑点大时更准。
- **`price`**：滑点加进委托价。滑点不到一分钱时更准，因为 khQuant 把成交价取整到分，小滑点经常被取整掉；用限价单、盘前盘后挂单的策略也更准，因为 khQuant 限价成交的滑点不越过限价。

离线自检会把两种都跑一遍，推荐期末资产更接近 khQuant 的那种。下单前兼容层还会按 QMT 实际收费口径核一遍资金，不够就减一手，避免 QMT 拒单后账目错乱。

用 khQuant 本地数据做过两组对照（2026-11-01），成交时间、代码、方向全部和 khQuant 引擎逐笔一致：

- **12 个功能场景**：限价单（当日有效、GTD、`max_pending_bars`、撤单）、止损和止损限价单、盘前盘后、日内两轮满仓换股、不复权 T+1 和涨跌停拒单、跳数滑点和最低佣金、印花税切换、小滑点多股轮动、5 分钟线、1 分钟 T+0、后复权、按持仓均价止盈止损。按推荐模式，期末资产差在 0 到 +0.28% 之间（5 分钟线那组 +0.28% 来自 ETF 价格三位小数时滑点取整）。
- **8 个 khQuant 内置策略**：每个交给一个只拿到本 skill 的子代理独立迁移，再用离线自检独立复核交付文件。双均线 3 个、RSI、三个 1 分钟 T+0 网格、khIndex 读库 MACD 全部原样能跑，期末资产差 −0.21% ～ +0.05%。另一个联网调外部接口的策略只做盘点，子代理正确指出了单线程阻塞、分钟线盘后回调和 T+0 实测等问题。

在真实大QMT（券商版，2026-11-01）回测过「日内两轮」的成品，原样粘贴就能跑：

- QMT 66 笔、khQuant 64 笔，其中 63 笔日期、代码、方向相同；不同的 4 笔都落在只靠浮点误差决定的均线交叉点上。
- 期末资产差 −0.66%，主要来自两边前复权价不同（C10），共同成交的股数因此全部不同。
- 折进佣金的滑点、卖出印花税，QMT 实际扣费和 `[设置]` 行分毫不差。
- 回测参数里的费率框单位是 %，最大成交比例默认 0，要改成 100（见 backtest-settings.md 第 3 节）。

## 工作流程

### 第 1 步：收集材料

向用户要（或在用户给的目录里找）：

- 策略 `.py` 和配套 `.kh`；`.py` 里 import 的本地模块。
- khQuant 版本（`kh version`）。
- 原策略在 khQuant 的回测结果目录（有 `trades.csv` 最好，用来对账）。
- 用户的目标：只在 QMT 里回测，还是之后要跑模拟盘或实盘。
- QMT 是券商版还是投研版（影响扩展数据、第三方库白名单）。

### 第 2 步：盘点功能，先报告做不到的部分

读 `.py` 和 `.kh`，按下表找出用到的功能，再对照 `references/not-supported.md` 归类：

| 搜什么 | 对应条目 |
|---|---|
| `khPreMarket`、`khPostMarket`、`.kh` 的 `market_callback` | B4（只支持日线） |
| `khRequestNextDailyTrigger`、`daily_trigger_cap` | B5（只支持日线） |
| `order_type`、`stop_price`、`time_in_force`、`expire_date`、`max_pending_bars`、`khGetPendingOrders`、`khCancel*` | B3 |
| `khAddExtraFields`、`khIndex`、`khDuckDB`、`khDuckWrite` | A2 |
| `peTTM`、`pbMRQ`、`turn`、`isST` 等 BaoStock 字段 | A3 |
| `khKline`、缠论函数 | A13；复制 `khChanLunTools.py` 里用到的函数 |
| MyTT 指标函数 | 复制 khQuant 的 `MyTT.py` 里用到的函数（已确认能按 Python 3.6 解析） |
| `is_trade_time`、`is_trade_day`、`get_trade_days_*` | A12 |
| `threading`、`multiprocessing`、`concurrent`、`asyncio` | A9 |
| `requests`、`urllib`、读写文件 | 白名单和路径问题（A8） |
| `.kh` 的 `trigger.type` 为 `tick` 或 `custom` | A11、C13 |
| `.kh` 的 `trade_cost`：`stamp_tax_mode`、`flow_fee`、过户费 | B15 |
| 成交量限制（软件设置里开启） | B17、C5 |
| 股票池全是 T+0 ETF | B7、C4 |
| `random`（内置案例的随机参数） | 改成固定值，否则两边没法对比 |
| 3.7 及以后的语法或标准库 | 见下方「Python 3.6 清单」 |

把结果整理成一张表发给用户：每项写「用到了什么 → 属于哪一类 → 迁移后怎么处理 → 会不会影响结果」。命中「一、做不到」的项目，替代方案有多种取舍时，用 AskUserQuestion 让用户选；只有一种合理做法时直接说明并继续。

### 第 3 步：生成 QMT 策略文件（兼容层路线）

1. 复制 `assets/kh_compat_qmt.py` 作为底稿。
2. 按 `references/backtest-settings.md` 第 4 节，把 `.kh` 的取值填进 `KH_CONFIG`。
3. 把 khQuant 策略代码贴进「三、khQuant 策略代码」一段，替换掉那里的占位函数，然后：
   - 删掉 `from khQuantImport import *`；
   - `def init(...)` 改名为 `def kh_init(...)`，参数不变；
   - 用到的 MyTT、缠论函数从 khQuant 安装目录（或源码目录）的 `MyTT.py`、`khChanLunTools.py` 复制进来；
   - 本地 import 的辅助模块内联进文件；
   - 第 2 步里需要替换的写法逐项改掉，每处改动加一行中文注释说明原写法。
4. 兼容层已提供的同名函数：`khGet`、`khPrice`、`khHas`、`khHistory`、`khMA`、`generate_signal`、`calculate_max_buy_volume`、`round_price`、`get_price_decimals`、`khRequestNextDailyTrigger`、`khGetPendingOrders`、`khGetPendingSummary`、`khCancelOrder`、`khCancelOrdersByCode`、`khCancelAllOrders`、`khIsMatchEngineEnabled`，以及 `logging`、`np`、`pd`、`datetime`、`dt`、`timedelta`、`Dict`、`List`、`Optional`。不在这个列表里的 khQuant 函数（`khKline`、`khDuckDB`、`is_trade_day`、`TimeInfo`、`StockDataParser`、`PositionParser`、`StrategyContext` 等）要改写成上面这些，或自己补实现。
5. 不要改兼容层「二」「四」两段。确实要改时，在迁移报告里写明改了什么、为什么。
6. 成品要原样就能跑：
   - 不留占位路径和要用户先改才能运行的默认值。
   - 确实要用户填的内容（比如另一台电脑上的 CSV 路径），集中写在 `KH_CONFIG` 下方，用「需要你填写」注释标出，并在报告「需要你填写的配置」一节列出来。
   - 给默认值时，选一个不填也能跑的方案（例如指标默认在 QMT 里现算，读 CSV 作为可选项）。
7. `slippage_mode` 先用默认的 `commission`，做完第 4 步后改成自检推荐的模式。`selfcheck` 保持 `True`：第一次在 QMT 回测时，日志里 `[自检]` `[设置]` 开头的行会打印账号资金、K 线时间格式、前 3 笔委托后 QMT 查到的持仓和资金（并和兼容层按 QMT 收费推算的资金对比），以及回测参数界面该填的数（已换算成百分数）。
8. 保存成品：文件名 `<策略名>_QMT.py`，按 GBK 编码写入（Python 里 `open(path, 'w', encoding='gbk')`；遇到 GBK 存不下的字符先改掉）。第一行保持 `#coding:gbk`。

原生改写路线按 `references/function-mapping.md` 写，第 6 步照样做。示例：`assets/example_dual_ma_section.py` 是内置双均线案例迁移后的策略段。

### 第 4 步：本机离线自检（用户电脑上有 khQuant 和本地数据时）

`scripts/offline_check.py` 用 khQuant 的 DuckDB 数据（只读）模拟 QMT 手册写明的回测撮合规则，跑「兼容层 + 迁移后的策略段」，再和 khQuant 的 `trades.csv` 逐笔对照，同时检查 Python 3.6 语法。

1. 没有 khQuant 回测结果时，先征得用户同意再跑 `kh run 原配置.kh`（会在回测结果目录里新增一条记录）。
2. 把迁移后的策略段（不含兼容层）单独存一个文件，运行：

```bash
python scripts/offline_check.py --compat assets/kh_compat_qmt.py --strategy 策略段.py --data-root <khQuant数据目录> --stocks 000001.SZ --start 20230101 --end 20241231 --period 1d --dividend-type front --kh-trades <khQuant结果目录>/trades.csv --config "{\"commission_rate\": 0.0001, \"min_commission\": 5, \"stamp_tax_rate\": 0.0005, \"slippage\": {\"type\": \"ratio\", \"ratio\": 0.001}}"
```

`--config` 里的费用、滑点、盘前盘后、日内触发上限都要和 `.kh` 一致。用装了 duckdb、pandas 的 Python（khQuant 源码用户用 khQuant 自己的 Python 环境）。脚本默认把两种滑点模式各跑一遍（`--slippage-mode auto`）。

3. 读结果：
   - 「结论：通过」要求成交时间、代码、方向逐笔一致，而且成交不为 0 笔。不一致说明迁移改错了逻辑，常见原因：`khHistory` 截止点、`init` 里初始化的状态、随机参数、MyTT 函数漏抄或改动、日线里误用当天收盘价判断、指标的复权口径和原来不同。
   - 「khQuant 口径价格或股数有差异」的那几笔，是兼容层按 khQuant 规则算出的价格和股数。差异只应来自两种情况，日志里都有提示：一是委托价超出当根高低点，按端点下了单；二是按 QMT 收费口径资金不够，减了一手。之后的股数差几手是资金差连带的。
   - 「期末资产差」是照兼容层打印的回测参数设置后，模拟 QMT 的结果和 khQuant 的差距。把成品的 `slippage_mode` 改成「推荐滑点模式」，报告里写上两种模式各差多少。差距超过 1% 时，先查原因，再写进报告。
   - 自检通过只说明迁移逻辑对，不代表 QMT 真实回测一样，QMT 那边还有行情源和费用差异。
4. 策略另取了不同复权的数据（例如用不复权价算指标）时，脚本会按需读取对应的复权列，前提是 khQuant 本地库里有这些列。

### 第 5 步：交给用户

交付三样东西：

1. `<策略名>_QMT.py`（GBK 编码）。
2. 迁移报告（Markdown），按下面的结构写：

```markdown
# <策略名> 迁移到大QMT 报告

## 结论
（能不能迁、哪些部分做不到、预计和 khQuant 的差异有多大）

## 大QMT 做不到或做法不同的部分
| 用到的功能 | 类别（做不到 / 做法不同 / 需实测） | 迁移后怎么处理 | 对结果的影响 |

## 需要你填写的配置
（没有就写「无，原样粘贴即可」；有的话逐项写：在文件哪一行、填什么、不填会怎样）

## QMT 里怎么设置
（数据下载清单；基本信息：位置、默认周期、默认品种、复权；回测参数逐项取值，按成品 `[设置]` 打印的值。写明费率框单位是 %、最大成交比例填 100）

## 本机自检结果
（命令；成交笔数；是否逐笔一致；两种滑点模式各自的期末资产差距和选用哪种；有差异的成交及原因。没做自检就写明没做）

## 第一次 QMT 回测核对表
| 序号 | 日期时间 | 代码 | 方向 | 股数 | 委托价 | 预计手续费 |
（取自检里的前 3 笔。说明日志里哪几行 `[自检]` 对应哪一项实测：账号资金、K 线索引格式、委托后的持仓和可卖数量）

## 上线 QMT 回测后要实测的项目
（not-supported.md 第三节里命中的条目和最小测试方法）
```

3. QMT 操作步骤：补数据 → 新建 Python 模型 → 粘贴代码 → 基本信息 → 回测参数 → 编译 → 回测 → 导出「操作明细」。细节在 `references/backtest-settings.md`。

### 第 6 步：QMT 回测后对账

用户在 QMT 回测后贴回操作明细或日志时：

- 先看日志里的 `[自检]` 行：账号查不到资金、K 线索引格式异常、委托后 QMT 持仓或可卖数量和预期不符、QMT 资金和兼容层推算资金差得多（常见是费率框按小数填了，小了 100 倍），都要先解决。
- 再比成交时间、代码、方向，然后比价格和股数。用核对表里的前 3 笔快速判断回测参数是否填对。
- 差异先归到已知原因：行情源和复权（A1、C10）、QMT 费用口径（B15）、滑点（B16、C2）、高低点外的价格（B2）、资金连带的股数差。
- 归不进去的差异，按 not-supported.md 第三节的方法做最小测试定位，不要凭猜测改兼容层。

## Python 3.6 清单

QMT 内置 Python 的版本由客户端决定：官方手册和多数券商版是 3.6，新版本可能更高。成品一律按 3.6 写，新旧客户端都能跑；第一次回测时 `[自检]` 会打印实际版本。离线自检按 3.6 检查语法；标准库和第三方库的 API 要自己看：

- 语法：不能用 `:=`、`match`、仅限位置参数 `/`、`f"{x=}"`、`from __future__ import annotations`、`list[int]` / `dict[str, int]` 这类注解（改用 `typing.List`）。
- 标准库：`dataclasses`（3.7）、`datetime.fromisoformat`（3.7）、`contextlib.nullcontext`（3.7）、`time.time_ns`（3.7）、`math.prod` / `math.isqrt`（3.8）、`functools.cache`（3.9）、`str.removeprefix` / `removesuffix`（3.9）、字典 `|` 合并（3.9）、`zoneinfo`（3.9）都没有。
- pandas、numpy 版本由 QMT 决定，可能较旧。用到较新的 API（如 `DataFrame.map`、`pd.concat` 的新参数）时，在 `kh_init` 里打印版本让用户确认。
- 字符串和注释里的中文最终要能按 GBK 保存。

## 参考文件

| 文件 | 什么时候读 |
|---|---|
| `references/not-supported.md` | 第 2 步盘点；写迁移报告；对账时归因 |
| `references/backtest-settings.md` | 填 `KH_CONFIG`；写 QMT 设置步骤 |
| `references/function-mapping.md` | 原生改写路线；兼容层没有的函数怎么替代 |
| `references/live-trading.md` | 用户要转模拟盘或实盘 |
| `assets/kh_compat_qmt.py` | 兼容层底稿 |
| `assets/example_dual_ma_section.py` | 迁移后的策略段示例 |
| `scripts/offline_check.py` | 第 4 步离线自检 |
