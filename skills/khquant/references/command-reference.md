# 命令速查表

## 总览

```
kh init                 首次使用引导配置
kh config               查看/修改全局配置
kh run                  执行回测
kh data                 数据库管理
kh result               回测结果管理
kh strategy             策略管理
kh tool                 小工具
kh bridge               miniQMT 桥接服务
kh doctor               环境诊断
kh version              版本信息
kh gui                  启动 GUI 界面
```

无需初始化即可运行的命令：`init`、`doctor`、`version`、`gui`

---

## kh init

```bash
kh init
```

5 步交互式向导：数据源 → 数据路径 → 策略目录 → Tushare/BaoStock → 其他参数

---

## kh config

```bash
kh config show                         # 查看配置
kh config set <key> <value>            # 修改配置
kh config reset                        # 重置为默认
```

### 性能设置（v3.3.6+）

```bash
kh config show                                      # 查看当前性能设置
kh config set performance_preset balanced           # 智能模式（推荐，默认）
kh config set performance_preset performance        # 全量加载：内存充足、小数据最快
kh config set performance_preset low_memory         # 省内存：强制分段加载
```

`performance_preset` 是首选入口，会自动展开一组详细性能参数：

| 预设 | 含义 | 适用场景 |
|------|------|----------|
| `balanced` | 智能模式：小数据全量，大数据按内存自动分段 | 默认推荐，绝大多数用户使用 |
| `performance` | 全量加载：一次性把行情载入内存 | 数据量较小、内存充足，追求最快速度 |
| `low_memory` | 省内存：强制分段加载 | 大股票池、小周期、长区间，或机器内存有限 |

常用详细参数（通常不用手动改，除非排查性能问题）：

```bash
kh config set performance_memory_profile auto       # auto/standard/low/ultra_low
kh config set performance_memory_auto_dynamic_load true
kh config set performance_memory_low_chunk_size 20
kh config set performance_memory_ultra_low_chunk_size 20
kh config set performance_framework_history_preload_days 300
kh config set performance_duckdb_parallel_read_workers 4
kh config set performance_duckdb_load_max_connections 800
kh config set performance_duckdb_max_connections 800
```

说明：
- `performance_memory_profile` 控制内存加载策略：`auto` 自动判断，`standard` 全量，`low` / `ultra_low` 分段。
- `performance_framework_history_preload_days` 控制框架在回测开始日前额外预热多少天历史 K 线，供 `khHistory` 内存快路切片使用；默认 `300`，可设 `0~2000`，日线策略通常不需要更大。
- `chunk_size` 峰值内存不是越小越好；实测低于约 20 个交易日会因频繁换段反而更慢、更容易内存抖动。默认下限已设为 `20`。
- 连接池上限当前默认 `800`，是全 A 大股票池压力测试后的折中值；不要随手调大。
- 修改 `performance_preset` 会覆盖详细性能参数，并把“自定义性能细节”状态重置为预设一致。

---

## kh run

```bash
kh run <config.kh> [options]
```

| 选项 | 说明 |
|------|------|
| `-s` / `--strategy <path>` | 覆盖策略文件 |
| `--start YYYYMMDD` | 覆盖开始日期 |
| `--end YYYYMMDD` | 覆盖结束日期 |
| `-c` / `--capital <N>` | 覆盖初始资金 |
| `--stocks <codes>` | 覆盖股票池（逗号分隔）|
| `-p` / `--period <p>` | 覆盖周期 |
| `-q` / `--quiet` | 静默模式 |
| `-v` / `--verbose` | 详细日志 |
| `--report` | 生成 HTML 报告 |
| `--no-open` | 不打开浏览器 |
| `--json` | JSON 输出 |
| `--memory-profile auto|standard|low|ultra_low` | 仅本次回测临时覆盖内存模式 |
| `--no-auto-dynamic-load` | 仅本次回测禁用内存不足时自动动态分段 |

性能相关示例：

```bash
# 全局切到智能模式（推荐）
kh config set performance_preset balanced

# 全局切到省内存模式，适合大股票池/分钟线/长区间
kh config set performance_preset low_memory

# 只让本次回测用低内存模式，不改全局配置
kh run config.kh --memory-profile low --report

# 只让本次回测强制全量加载，不改全局配置
kh run config.kh --memory-profile standard --report
```

---

## kh data

```bash
kh data list [--market SH|SZ|BJ] [--period 1d|1m|5m|tick]
kh data stats
kh data info <code>
kh data download --source <src> [--stocks x] [--pool x] [--file x] [--period 1d] [--start x] [--end x] [--adj front] [--force] [--workers 2]
kh data scan [--period 1d] [--stocks x] [--start x] [--end x] [--fix] [--source x]
kh data export <code> [--period 1d] [--start x] [--end x] [--output x]
kh data repair [--db-path x] [--memory-limit 256MB]
kh data update-pool
kh data sync [--period 1d] [--source x] [--schedule HH:MM]
```

数据源选项：`xtdata`（miniQMT 本地）、`baostock`（免费）、`tushare`（需 Token）、`http`（经桥接服务）

---

## kh result

```bash
kh result list [--all] [--strategy <name>] [--json]
kh result show [dir] [--id N] [--json]
kh result report [dir] [--id N] [--index] [--no-open] [--output <path>]
kh result compare [--last 3]
kh result clean [--keep 10] [--dry-run]
```

---

## kh strategy

```bash
kh strategy list [--dir <path>]
kh strategy create <name> [--dir <path>]
kh strategy validate <path>
kh strategy info <path>
```

---

## kh tool

```bash
kh tool trade-day [YYYYMMDD] [--range-start x --range-end x]
kh tool pool [name] [--all]
kh tool parquet-cache stats [--root x]
kh tool parquet-cache list [--root x]
kh tool parquet-cache clean [--root x] [--older-than-days N] [--dry-run] [--yes]
kh tool parquet-cache check <config.kh> [--root x] [--data-root x]
kh tool parquet-cache build <config.kh> [--root x] [--data-root x] [--batch-size x] [--workers N] [--compression SNAPPY|ZSTD] [--force]
kh tool parquet-cache use-readonly <config.kh> [--root x] [--output x] [--in-place] [--lazy-current-data]
```

`parquet-cache` 是可选缓存包工具，用于把指定 `.kh` 所需 DuckDB 数据预构建为 Parquet 读取包。普通用户通常不用；性能压测或重复跑超大回测时再考虑。`clean` 会删除缓存包，必须先用 `--dry-run` 预览，确认后再加 `--yes`。

---

## kh bridge

```bash
kh bridge serve [--host 0.0.0.0] [--port 8001] [--api-key x] [--qmt-path x]
kh bridge status [--url x] [--port 8001]
```

`bridge serve` 启动 miniQMT 数据桥接服务（数据专用模式），`data download --source http` 和 `data sync --source http` 可经桥接服务获取数据。启动服务会占用端口，应先确认。

---

## kh doctor

```bash
kh doctor
```

检查：Python、核心依赖（9 项）、可选依赖（3 项）、数据目录、配置状态、策略目录、回测历史

---

## kh version / kh gui

```bash
kh version    # 显示版本号
kh gui        # 启动 GUI 界面
```
