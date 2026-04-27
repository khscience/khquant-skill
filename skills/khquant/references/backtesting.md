# 回测执行指南

## 基本用法

```bash
kh run <配置文件.kh> [选项]
```

## .kh 配置文件格式

`.kh` 文件是 JSON 格式：

```json
{
  "strategy_file": "双均线精简_使用khMA函数.py",
  "backtest": {
    "start_time": "20250101",
    "end_time": "20250703",
    "init_capital": 1000000,
    "min_volume": 100,
    "benchmark": "sh.000300",
    "trade_cost": {
      "commission_rate": 0.0003,
      "stamp_tax_rate": 0.001,
      "min_commission": 5.0,
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
      "daily_trigger_cap": 1
    }
  },
  "data": {
    "kline_period": "1d",
    "stock_list": ["000001.SZ"],
    "dividend_type": "none"
  },
  "risk": {
    "position_limit": 0.95,
    "order_limit": 100,
    "loss_limit": 0.1
  }
}
```

### 核心字段

| 字段 | 说明 |
|------|------|
| `strategy_file` | 策略 .py 文件路径 |
| `backtest.start_time` | 开始日期 YYYYMMDD |
| `backtest.end_time` | 结束日期 YYYYMMDD |
| `backtest.init_capital` | 初始资金（元，默认 1000000）|
| `data.kline_period` | K 线周期：`tick`/`1m`/`5m`/`1d` |
| `data.dividend_type` | 复权方式（默认 `none`，推荐设为 `front`）|
| `data.stock_list` | 股票池（代码数组）|
| `backtest.trade_cost.commission_rate` | 佣金率（默认 0.0003 即万三）|
| `backtest.trade_cost.stamp_tax_rate` | 印花税率（默认 0.001 即千一，仅卖出收取）|
| `backtest.trade_cost.flow_fee` | 过户费（默认 0.1 元/笔）|
| `backtest.trade_cost.slippage.type` | 滑点类型：`tick`（绝对值）或 `ratio`（比例，应用时减半）|
| `backtest.trigger.type` | 触发方式：`tick`/`1m`/`5m`/`1d`/`custom` |
| `backtest.trigger.daily_trigger_cap` | 日线多次触发上限（仅 1d 模式，默认 1）|
| `risk.position_limit` | 最大仓位比例（默认 0.95）|

## CLI 参数覆盖

命令行参数优先级高于 .kh 文件：

```bash
# 覆盖策略文件
kh run config.kh --strategy other.py

# 覆盖日期区间
kh run config.kh --start 20240101 --end 20241231

# 覆盖资金
kh run config.kh --capital 500000

# 覆盖股票池
kh run config.kh --stocks 000001.SZ,600000.SH

# 覆盖周期
kh run config.kh --period 5m
```

## 输出模式

| 参数 | 效果 |
|------|------|
| （默认）| 显示策略信息 + 回测结果摘要 |
| `--quiet` / `-q` | 静默模式，不显示摘要 |
| `--verbose` / `-v` | 详细模式，显示 DEBUG 日志 |
| `--json` | JSON 格式输出（同时静默正常输出）|
| `--report` | 完成后生成 HTML 报告并打开浏览器 |
| `--no-open` | 配合 `--report`，生成报告但不打开 |

## 典型用法

```bash
# 跑回测并自动生成报告（推荐）
kh run D:\CLIstrategies\【1-MA策略案例】双均线精简_使用khMA函数.kh --report

# 快速跑完不看报告
kh run config.kh --quiet

# 脚本自动化（取 JSON 结果）
kh run config.kh --json 2>nul

# 覆盖时间区间再跑
kh run config.kh --start 20230101 --end 20231231 --report
```

## T+0 与 T+1 模式

- **T+1**（默认）：当天买入的股票次日才能卖出（A 股标准规则）
- **T+0**：当天买入当天可卖（适用于部分 ETF）

**T+0 模式由框架自动检测**：当股票池中全部为 T0 ETF 标的时自动启用，混合池（含股票和 ETF）强制 T+1。无需手动配置。T+0 标的列表见 `data/T0stock.txt` 和 `data/T0ETF.txt`。

## 回测结果输出

回测结果保存在 `backtest_results/<时间戳目录>/`：

| 文件 | 内容 |
|------|------|
| `summary.csv` | 总收益率、年化收益率、最大回撤等核心指标 |
| `trades.csv` | 所有交易记录 |
| `daily_stats.csv` | 逐日净值和统计 |
| `config.csv` | 回测使用的配置 |
| `benchmark.csv` | 基准数据（如有）|
| `report.html` | HTML 交互式报告（使用 `--report` 时生成）|

## 全局自动报告

不想每次加 `--report`，可全局开启：

```bash
kh config set auto_report true
```
