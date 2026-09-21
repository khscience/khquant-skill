# 数据管理指南

## 数据源能力矩阵

| 特性 | xtdata (miniQMT) | BaoStock | Tushare | tx | 同花顺 ths | http (bridge) |
|------|-------------------|----------|---------|----|-----------|---------------|
| 费用 | 券商开户免费 | 完全免费 | 积分制 | 免费，无需账号 | 免费申请 API Key | 取决于桥接端 |
| 日线 1d | OK | OK | OK | OK | OK | OK |
| 1 分钟线 1m | OK | - | OK | 约近 1 个月 | - | OK |
| 5 分钟线 5m | OK | OK | OK | 约近半年 | - | OK |
| Tick 数据 | OK | - | - | - | - | 取决于桥接端 |
| 前复权 front | OK | OK | OK | OK | OK | 取决于桥接端 |
| 后复权 back | OK | OK | OK | OK | OK | 取决于桥接端 |
| 前比例复权 front_ratio | OK | - | - | OK | - | 取决于桥接端 |
| 后比例复权 back_ratio | OK | - | - | OK | - | 取决于桥接端 |
| 安装要求 | QMT 客户端运行 | `pip install baostock` | Token + `pip install tushare` | 无 | `kh config set ths_api_key <API_KEY>` | 先运行 `kh bridge serve` 或配置远端桥接服务 |

所有数据源写入 DuckDB 时，K 线 `volume` 统一以“手”存储，`amount` 以元存储。

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
| `--source` | 无（必需）| `xtdata` / `baostock` / `tushare` / `tx`（同 `tencent`）/ `ths` / `http` |
| `--stocks` | | 股票代码，逗号分隔 |
| `--pool` | | 预设池名称（见 pools-and-codes.md）|
| `--file` | | 股票列表文件路径 |
| `--period` | `1d` | `tick` / `1m` / `5m` / `1d` |
| `--start` | `20200101` | 起始日期 YYYYMMDD |
| `--end` | 至今 | 结束日期 YYYYMMDD |
| `--adj` | `front` | 复权：`none`/`front`/`back`/`front_ratio`/`back_ratio` |
| `--force` | 否 | 强制覆写已有数据 |
| `--workers` | `2` | 并行进程数 |
| `--db-write-mode` | `auto` | DuckDB 写库模式：`auto`/`normal`/`short-lock` |

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

### tx 与同花顺

```bash
# tx：免费，日线/1 分钟/5 分钟，五种复权
kh data download --source tx --stocks 000001.SZ --period 1d,5m --adj none,front

# 同花顺（扶摇）：先配置 API Key，目前只支持日线
kh config set ths_api_key <API_KEY>
kh data download --source ths --pool hs300 --period 1d --adj none,front,back

# 下载到独立目录，不改全局配置
kh data download --source tx --stocks 600000.SH --data-root ./tx_data

# 连通性检查
kh data source test --source tx
kh data source test --source ths
```

- tx 数据来自 tx 财经 / 新浪财经公开网页接口，仅供个人学习研究，联网前会显示来源声明。分钟线历史有限，超出可用窗口的日期没有数据，这不是下载失败。
- tx 分钟线的前/后复权按日线拟合，等比复权使用新浪复权因子。
- 同花顺 Key 也可以用环境变量 `HITHINK_FINANCE_API_KEY` 提供。Key 无效或未配置时命令直接报错，不会退回其他数据源。
- GUI 数据管理顶栏有“tx数据导入”和“同花顺数据导入”两个入口，Key 在导入窗口或 设置 → 数据设置 中配置。

### 数据管理中的 Tushare 补充

- GUI 的“从 Tushare 导入数据”支持日线、1 分钟和 5 分钟行情。原始价是 DuckDB 基础字段并始终保存，可选同时生成前复权、后复权列。
- 增量模式只检查用户选定的日期范围，不会再自动扩展到数据库全部历史区间。
- 分钟线按每日记录数检查完整性：完整 1 分钟日为 241 根，完整 5 分钟日为 48 根；当天只有部分记录时会重新补充。
- 网络、权限、限流和服务端错误与“正常无行情”分开处理，不会再把接口失败显示成“成功写入 0 条”。
- Tushare GUI 默认使用短锁写入：每只股票写完立即释放 `.db`，任务收尾再批量更新 `metadata.db`。
- 文件占用自动重试 5 次后，界面提供“继续重试 / 先跳过 / 停止任务”；结束日志和弹窗会列出占用跳过项。重试写库不会重复请求 Tushare 行情。

### 大批量导入与短锁写入

v3.3.6.1+ 的大批量下载/导入已支持 DuckDB 短锁写入，重点是减少 `metadata.db` 长时间占用：

```bash
# 默认 auto：小任务普通写入，大任务或 tick 自动短锁
kh data download --source xtdata --pool hs300 --period 1m --start 20250101

# 强制短锁，适合大股票池、tick、分钟线长区间
kh data download --source xtdata --pool hs300 --period tick --db-write-mode short-lock

# 强制普通模式，适合少量股票的小任务
kh data download --source baostock --stocks 000001.SZ --period 1d --db-write-mode normal
```

写库模式说明：

| 模式 | 行为 | 适用场景 |
|------|------|----------|
| `auto` | 默认模式；任务数 `>=20` 或包含 `tick` 自动启用短锁 | 推荐 |
| `normal` | 每只股票写完立即更新 `metadata.db` | 小任务、排查问题 |
| `short-lock` | 行情数据先写入各股票 `.db`，收尾再批量刷新 `stock_list` / `sync_log` | 大股票池、tick、分钟线长区间 |

读取边界：

- 导入期间，依赖 `metadata.db` 的股票列表、数据概览、看板通常可以继续读取；收尾批量刷新 metadata 时可能短暂占用。
- 正在写入的同一个股票 `.db` 文件仍受 DuckDB 单写者限制，不保证跨进程同时读取；读取其它股票 `.db` 通常不受影响。
- 当前开发版遇到单股票文件占用时，不会立即中止整批补充：系统先自动重试 5 次；仍未释放时，GUI 可选择继续重试、先跳过或停止任务。
- 选择“先跳过”后，该股票/周期不会写进断点续传的已完成集合，下次补充仍会重新扫描；任务完成日志与完成弹窗会列出占用跳过清单。
- 如果出现“数据已写入，但元数据刷新失败”，说明行情数据通常已入库，只是 `stock_list` / `sync_log` 未刷新。稍后执行扫描/修复元数据即可。

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

### 桌面端定时补充日历

数据管理中的独立“定时数据补充”窗口会在状态栏与运行日志之间显示最近一年的每日执行情况：深蓝表示所选股票池与周期全部成功写入 DuckDB，浅蓝表示部分成功，白色表示跟踪开始后的交易日没有补齐，深灰表示休市或尚未纳入记录。悬停日期可查看完成数量、周期与股票池。

- 统计基于 miniQMT 下载并成功写入 DuckDB 的实际任务结果，不扫描整库历史数据，因此不会拖慢窗口启动。
- 多个周期会在整次任务结束后汇总，再原子写入 `~/.khquant/scheduled_data_sync_coverage.json`。
- 日历只记录开始使用本定时补充模块后的任务结果，不代表数据库历史数据的实际完整情况；此前日期保持“未记录”，不会误判为缺失。
- 从数据管理模块打开独立定时补充时，会先显示屏幕居中的启动提示；独立窗口进入事件循环后自动关闭提示，模块窗口本身也在调用方所在显示器居中打开。

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
