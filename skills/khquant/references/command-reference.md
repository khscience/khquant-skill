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
kh data sync [--period 1d] [--schedule HH:MM]
```

数据源选项：`xtdata`（miniQMT）、`baostock`（免费）、`tushare`（需 Token）

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
```

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
