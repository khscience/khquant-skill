# 首次配置指南

## 前置条件

运行 `kh doctor` 检查环境。核心依赖（numpy, pandas, duckdb 等）缺失时需先安装：

```bash
pip install numpy pandas duckdb matplotlib Pillow holidays requests psutil
```

可选依赖：
- `baostock` — 免费数据源（推荐新用户）：`pip install baostock`
- `xtquant` — miniQMT 数据源（需要券商 QMT 客户端）
- `schedule` — 定时同步功能：`pip install schedule`

## 初始化流程

执行交互式向导：

```bash
kh init
```

### 5 个步骤

**步骤 1/5：选择数据源**
- `[1] DuckDB`（推荐）— 本地数据库，离线快速，新用户首选
- `[2] miniQMT` — 需要券商 QMT 客户端运行，适合已有 QMT 的用户

**步骤 2/5：数据路径**
- DuckDB 模式：输入数据根目录，需包含 `SH/SZ/BJ` 子目录。不存在的目录会在首次下载时自动创建
- miniQMT 模式：输入 `userdata_mini` 路径（如 `D:\国金证券QMT交易端\userdata_mini`）

**步骤 3/5：策略目录**
- 建议使用独立目录（如 `D:\CLIstrategies`），不要放在程序安装目录下
- 初始化会自动复制内置示例策略（.py + .kh）到该目录

**步骤 4/5：数据源配置（可选）**
- Tushare：需要 Token（在 tushare.pro 注册获取），输入后自动验证
- BaoStock：免费无需 Token，建议启用

**步骤 5/5：其他参数**
- 无风险利率：默认 0.03（3%），用于计算夏普比率等指标

## 初始化后验证

```bash
kh doctor          # 确认所有项 OK
kh strategy list   # 确认示例策略已复制
kh data stats      # 查看数据库状态（新安装可能为空）
```

## 修改配置

初始化后可随时修改单项配置：

```bash
kh config show                                    # 查看当前配置
kh config set duckdb_data_path D:\khData          # 修改数据路径
kh config set baostock_enabled true               # 启用 BaoStock
kh config set auto_report true                    # 回测后自动生成报告
kh config reset                                   # 重置为默认值
```

配置文件位置：`~/.khquant/settings.json`

## 常用配置项

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `backtest_data_source` | string | `duckdb` | 数据源：`duckdb` 或 `miniqmt` |
| `duckdb_data_path` | string | | DuckDB 数据根目录 |
| `strategy_dir` | string | | 策略目录 |
| `baostock_enabled` | bool | `false` | 启用 BaoStock |
| `tushare_token` | string | | Tushare Token（base64 存储）|
| `risk_free_rate` | float | `0.03` | 无风险利率 |
| `auto_report` | bool | `false` | 回测后自动生成 HTML 报告 |
| `volume_limit_enabled` | bool | `false` | 启用成交量限制 |
| `participation_rate` | float | `0.1` | 成交量参与率 |
| `allow_partial_fill` | bool | `true` | 允许部分成交 |
