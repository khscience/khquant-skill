# 数据管理指南

## 数据源能力矩阵

| 特性 | xtdata (miniQMT) | BaoStock | Tushare | http (bridge) |
|------|-------------------|----------|---------|---------------|
| 费用 | 券商开户免费 | 完全免费 | 积分制 | 取决于桥接端 |
| 日线 1d | OK | OK | OK | OK |
| 1 分钟线 1m | OK | - | OK | OK |
| 5 分钟线 5m | OK | OK | OK | OK |
| Tick 数据 | OK | - | - | 取决于桥接端 |
| 前复权 front | OK | OK | OK | 取决于桥接端 |
| 后复权 back | OK | OK | OK | 取决于桥接端 |
| 前比例复权 front_ratio | OK | - | - | 取决于桥接端 |
| 后比例复权 back_ratio | OK | - | - | 取决于桥接端 |
| 安装要求 | QMT 客户端运行 | `pip install baostock` | Token + `pip install tushare` | 先运行 `kh bridge serve` 或配置远端桥接服务 |

## 下载数据

### 基本用法

```bash
kh data download --source <数据源> --stocks <代码> --period <周期>
```

### 指定股票

```bash
# 单只股票
kh data download --source baostock --stocks 000001.SZ

# 多只股票（逗号分隔）
kh data download --source baostock --stocks 000001.SZ,600000.SH,000002.SZ

# 使用预设股票池
kh data download --source baostock --pool hs300

# 多个池
kh data download --source baostock --pool hs300,sz50

# 从文件读取
kh data download --source baostock --file stocks.csv
```

### 常用参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--source` | 无（必需）| `xtdata` / `baostock` / `tushare` / `http` |
| `--stocks` | | 股票代码，逗号分隔 |
| `--pool` | | 预设池名称（见 pools-and-codes.md）|
| `--file` | | 股票列表文件路径 |
| `--period` | `1d` | `tick` / `1m` / `5m` / `1d` |
| `--start` | `20200101` | 起始日期 YYYYMMDD |
| `--end` | 至今 | 结束日期 YYYYMMDD |
| `--adj` | `front` | 复权：`none`/`front`/`back`/`front_ratio`/`back_ratio` |
| `--force` | 否 | 强制覆写已有数据 |
| `--workers` | `2` | 并行进程数 |

### 典型场景

```bash
# 新用户快速入门：下载平安银行日线
kh data download --source baostock --stocks 000001.SZ --period 1d

# 批量下载沪深300成分股日线（2010年至今）
kh data download --source baostock --pool hs300 --period 1d --start 20100101

# 用 miniQMT 下载 Tick 数据
kh data download --source xtdata --stocks 000001.SZ --period tick --start 20250101

# 用 Tushare 下载前复权+后复权
kh data download --source tushare --stocks 000001.SZ --adj front,back

# 通过桥接服务下载（先确认桥接服务状态）
kh bridge status
kh data download --source http --stocks 000001.SZ --period 1d
```

### 自动基准下载

每次执行 download 时，系统自动检查 000300.SH（沪深300指数）日线数据是否完整（2010年至今）。如果缺失或不完整，会自动补充下载。

## 查看数据

```bash
# 数据库统计概览
kh data stats

# 列出所有有数据的股票
kh data list

# 按市场过滤
kh data list --market SH

# 按周期过滤
kh data list --period 1d

# 查看单只股票详情（各周期记录数和时间范围）
kh data info 000001.SZ
```

## 导出数据

```bash
kh data export 000001.SZ --period 1d --start 20240101 --output 平安银行.csv
```

注意：在 PowerShell 中不要使用 `-o` 短参数（会与 PowerShell 内置参数冲突），请始终使用 `--output`。

## 扫描数据缺口

```bash
# 扫描所有股票的日线缺口
kh data scan --period 1d

# 扫描指定股票
kh data scan --period 1d --stocks 000001.SZ,000002.SZ

# 扫描并自动补充（需指定数据源）
kh data scan --period 1d --fix --source baostock
```

## 同步当日数据

```bash
# 立即同步
kh data sync --period 1d

# 经桥接服务同步
kh data sync --source http --period 1d

# 定时同步（工作日 15:30 执行，需要 schedule 库）
kh data sync --schedule 15:30
```

## 数据修复

DuckDB 数据库损坏（WAL 文件异常）时：

```bash
kh data repair
```

## 更新股票池成分股

需要 xtquant (miniQMT)：

```bash
kh data update-pool
```
