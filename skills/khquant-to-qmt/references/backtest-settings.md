# .kh 配置 → 大QMT 回测设置对照

迁移时把用户 `.kh` 里的每一项填进下表，写进迁移报告，让用户照着在 QMT 里设置。

## 1. 数据准备（QMT「操作 → 数据管理 → 补充行情」）

- 周期：QMT 只真正存储 tick、1m、5m、1d 四个基础周期，其他周期由它们合成。日线策略下载 1d；用 15m、30m、1h 等合成周期要下载 5m；用 3m 要下载 1m。
- 范围：股票池全部代码 + 主图品种（见第 2 节）+ 基准指数。开始日期要往前多留预热期（最长指标周期 + 一段余量，和 khQuant 下载时的预热期一致）。
- 用到 ST 历史、合约乘数、退市合约时，在【行情 → 智能下载】里勾【过期合约列表】补充。
- 用到财务数据时，先在数据管理里下载财务数据。
- 建议在「批量下载」里勾定时下载，盘后自动补当天数据。

## 2. 策略编辑器「基本信息」

| QMT 字段 | 怎么填 | 原因 |
|---|---|---|
| 位置 | 副图 | 手册要求回测必须以副图运行 |
| 默认周期 | 和 `.kh` 的 `data.kline_period` 相同（1d / 1m / 5m） | `handlebar` 按主图周期触发 |
| 默认品种 | 多股票策略填 `000300.SH`（沪深300指数）；单股票策略可以填这只股票 | `handlebar` 只在主图有 K 线时触发。主图选个股时，它停牌的日子整个策略都不会运行；指数每个交易日都有 K 线 |
| 复权方式 | 和 `.kh` 的 `data.dividend_type` 相同 | 兼容层取数时显式传复权方式，但主图显示和 QMT 撮合用的是这里的设置。khQuant 本地库的前复权可能是下载时的快照，和 QMT 当天算的前复权差一个固定金额（实测见 not-supported.md C10），股数会因此不同；只为对账时建议两边都用不复权 |
| 快速计算 | 0 | 从主图第一根 K 线开始算；兼容层自己按 `start_date` 跳过回测区间之前的 K 线 |

## 3. 策略编辑器「回测参数」

界面上的字段依次是：开始时间、结束时间、基准、初始资金（元）、保证金比例、滑点类型、滑点值、手续费类型、买入印花税、卖出印花税、最低佣金（元）、买入佣金、平昨佣金、平今佣金、最大成交比例。**除了初始资金和最低佣金以元为单位，其余费率框的单位都是 %**：佣金 0.00511 要填 0.511，印花税 0.0005 要填 0.05。成品 `init` 打印的 `[设置]` 行已经换算成界面要填的数，照抄即可。（2026-11-01 在券商版大QMT 实测确认）

| `.kh` 字段 | QMT 回测参数 | 说明 |
|---|---|---|
| `backtest.start_time` / `end_time` | 开始时间 / 结束时间 | 兼容层在 `init` 里写 `C.start`、`C.end`。实测代码设置会覆盖界面：界面留着默认的 2017–2020，回测照样按代码里的区间跑 |
| `backtest.init_capital` | 初始资金 | 兼容层同时写 `C.capital` |
| `backtest.benchmark`（如 `sh.000300`） | 基准，填 `000300.SH` | 写法换成「代码.市场」 |
| （无） | 保证金比例 | 期货用，股票回测不用管 |
| `trade_cost.slippage` | 滑点类型选「按成交额比例」，滑点值填 0 | 兼容层自己处理滑点：`commission` 模式折进佣金，`price` 模式加进委托价。界面再填会重复计算 |
| `trade_cost.commission_rate` | 手续费类型选「按成交额比例」；买入佣金、平昨佣金、平今佣金三项都填 `[设置]` 行打印的同一个数 | 这个数等于佣金率 + 过户费 0.00001（股票，2022-04-29 之后口径）+ 单边滑点比例（`slippage_mode='commission'` 时），已换算成百分数。卖出取哪一框手册没写清，三框填一样就不用管。实测买入、卖出扣费和这个数分毫不差 |
| `trade_cost.min_commission` | 最低佣金（元） | |
| `trade_cost.stamp_tax_rate` | 卖出印花税（%）；买入印花税填 0 | 回测区间跨 2023-08-28 且 `.kh` 里写了 `"stamp_tax_mode": "a_share_legal"` 时，QMT 只能填一个值：分两段回测或接受误差 |
| `trade_cost.flow_fee` | 无对应项 | 每笔固定费用，金额很小时忽略；不小时折算进佣金率并在报告里说明 |
| 设置里的「成交量限制」参与率 | 最大成交比例（%） | **界面默认是 0，要改成 100**（khQuant 没开成交量限制时）。开了成交量限制就填参与率的百分数；剩余数量怎么处理手册未写（not-supported.md C5） |
| `backtest.min_volume` | 无 | 兼容层按 100 股整数倍计算 |
| `risk.*` | 无 | khQuant 的 `risk` 配置本身不自动执行，迁移时不用管 |

## 4. 兼容层 `KH_CONFIG` 对照

| `.kh` 字段 | `KH_CONFIG` 键 |
|---|---|
| `data.stock_list`（或 `stock_list_file` 里的代码） | `stock_list` |
| `backtest.start_time` / `end_time` | `start_date` / `end_date`（`YYYYMMDD`） |
| `backtest.init_capital` | `init_capital` |
| `data.kline_period` | `period` |
| `data.dividend_type` | `dividend_type` |
| `trade_cost.commission_rate` / `min_commission` / `stamp_tax_rate` / `flow_fee` | 同名键 |
| `trade_cost.stamp_tax_mode` | `stamp_tax_mode` |
| `trade_cost.transfer_fee_enabled`（缺省为开） | `transfer_fee_enabled` |
| `trade_cost.slippage` | `slippage`（原样复制 `type`、`ratio`、`tick_size`、`tick_count`） |
| `market_callback.pre_market_enabled` / `pre_market_time` | 同名键 |
| `market_callback.post_market_enabled` / `post_market_time` | 同名键 |
| `backtest.trigger.daily_trigger_cap` | `daily_trigger_cap` |
| T+0 ETF 股票池 | `t0_codes`（列出池中的 T+0 ETF，清单见 khQuant 的 `data/T0型ETF.csv` 等 `T0*.csv`）或直接写 `t_plus_1: False` |
| （无对应项） | `slippage_mode`：默认 `commission`，按离线自检的「推荐滑点模式」改 |
| （无对应项） | `selfcheck`：保持 `True`，第一次 QMT 回测时打印核对信息 |

`backtest.trigger.type` 为 `tick` 或 `custom` 时，兼容层不直接支持，按 not-supported.md 的 A11、C13 处理。

## 5. 运行和导出

1. 策略编辑器点「编译」（只保存，不查语法），再点「回测」。
2. 有报错看「日志输出」面板；第一行常见问题是编码（文件要 GBK）和缩进混用。
3. 回测结束后在结果面板的「操作明细」右键导出，和 khQuant 的 `trades.csv` 对照。
4. 运行无反应或报 `run script failed!`：右上角「布局 → 恢复默认布局」，停掉其他正在运行的策略，再重启客户端。
