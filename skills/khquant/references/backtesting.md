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

## 回测性能与内存模式（v3.3.6+）

khQuant 现在有两层性能设置：

1. **全局性能预设**：写入 `%USERPROFILE%\.khquant\settings.json`，以后所有回测默认使用。
2. **单次回测覆盖**：只影响当前这条 `kh run` 命令，不修改全局配置。

### 全局性能预设

优先用 `performance_preset`，不要一上来就改底层细节：

```bash
# 查看当前性能配置
kh config show

# 智能模式（推荐，默认）：小数据全量，大数据自动分段
kh config set performance_preset balanced

# 全量加载：内存充足、小数据最快；超大数据可能内存不足
kh config set performance_preset performance

# 省内存：强制分段加载，适合大股票池、小周期、长区间
kh config set performance_preset low_memory
```

| 预设 | 数据加载方式 | 适合 |
|------|--------------|------|
| `balanced` | 自动判断全量或分段 | 默认推荐 |
| `performance` | 尽量全量加载 | 小数据、内存充足、追求速度 |
| `low_memory` | 强制分段加载 | 大股票池、分钟线、长区间、内存有限 |

注意：三档只影响速度和内存，不应改变回测结果。改引擎或数据加载后，需要用回归基准验证三档结果一致。

### 单次回测覆盖内存模式

如果只想临时测试某次回测，不改全局配置：

```bash
# 自动判断
kh run config.kh --memory-profile auto

# 强制全量加载
kh run config.kh --memory-profile standard

# 强制低内存分段
kh run config.kh --memory-profile low

# 极低内存分段
kh run config.kh --memory-profile ultra_low
```

也可以临时禁用“内存不足时自动动态分段”：

```bash
kh run config.kh --memory-profile standard --no-auto-dynamic-load
```

### 常用详细参数

一般不需要手动改这些参数；只有在性能排查或压测时才调整：

```bash
kh config set performance_memory_profile auto
kh config set performance_memory_auto_dynamic_load true
kh config set performance_memory_low_chunk_size 20
kh config set performance_memory_ultra_low_chunk_size 20
kh config set performance_framework_history_preload_days 300
kh config set performance_duckdb_parallel_read_workers 4
kh config set performance_duckdb_load_max_connections 800
kh config set performance_duckdb_max_connections 800
```

经验规则：
- 大股票池、小周期、长区间回测优先用 `low_memory`，旧版本容易在这种场景内存爆棚。
- `performance_framework_history_preload_days` 默认 `300`，用于给 `khHistory` 内存快路预热回测开始日前的历史 K 线；可在 GUI「回测性能 → 详细设置」或 CLI 中设为 `0~2000`。
- `chunk_size` 不要盲目调小。实测低于约 20 个交易日会因为换段次数暴增，反而更慢、更容易出现内存抖动。
- 连接池默认 `800` 是压力测试后的折中值；调大可能更慢且更吃内存。

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
