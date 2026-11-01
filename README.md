# KhQuant Skill for Claude Code、Codex & Cursor

> 看海量化回测平台 (KhQuant) 的 AI Skill 插件 — 用自然语言完成数据管理、策略开发、桌面/CLI/Web 回测、结果分析和故障排查，并能把 khQuant 回测策略迁移到大QMT 内置 Python。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Version](https://img.shields.io/badge/version-1.4.1-blue.svg)](#版本)
[![KhQuant](https://img.shields.io/badge/KhQuant-v3.4.1.7-green.svg)](https://khsci.com/khQuant/)

---

## 是什么

这是一份面向 Claude Code、Codex、Cursor 等 Agent 工具组织的知识包，包含两个 Skill：

| Skill | 用途 | 内容 |
|---|---|---|
| `khquant` | 操作看海量化：配置、数据、策略、回测、结果分析 | 入口 `SKILL.md`（意图路由 + 执行原则）和九份 references（首次配置 / 数据管理 / 策略开发 / 回测执行 / Web 回测 / 结果分析 / 故障排查 / 命令速查 / 股票池规范） |
| `khquant-to-qmt` | 把 khQuant 回测策略迁移到迅投大QMT 内置 Python 回测 | 入口 `SKILL.md`（迁移流程）、兼容层底稿 `kh_compat_qmt.py`、离线自检脚本 `offline_check.py`、四份 references（大QMT 做不到或做法不同的清单 / 回测设置对照 / 函数对照 / 转实盘注意事项） |

安装后，Agent 会在用户提到“回测”“看海量化”“kh web”“DuckDB”“双均线”“MACD”等任务时加载 `khquant`；提到“把策略搬到QMT”“迁移到大QMT”“QMT回测和khQuant对不上”等任务时加载 `khquant-to-qmt`。

> 关于该 Skill 的设计思路与详细说明，可参考公众号文章「看海量化专属 Skill 插件全解析」。

## 主要能力

- **首次配置** — 引导完成 `kh init` 初始化
- **数据管理** — 下载、查看、导出、扫描、同步股票数据
- **策略开发** — 创建、校验策略，理解回调函数与信号格式
- **回测执行** — 运行回测、参数覆盖、生成 HTML 报告
- **Web 工作台** — 导入项目、运行/停止回测、读取实时日志、查看报告和排查状态异常
- **结果分析** — 查看摘要、对比多次回测、解读绩效指标
- **故障排查** — 自动识别常见错误并给出修复方案
- **跨平台边界** — 区分 Windows、macOS、Linux 的 GUI/CLI/Web、miniQMT 与发行范围
- **迁移到大QMT**（`khquant-to-qmt`）— 先按清单列出大QMT 做不到或做法不同的部分，再生成能直接粘贴进大QMT 策略编辑器的 `.py`；本机用 khQuant 数据离线模拟 QMT 撮合，逐笔对照 khQuant 的成交，并打印 QMT 回测参数该填的值

内置三色灯安全分级：查询类自动执行，修改类需用户确认，危险类必须明确授权（如 `kh result clean`、`kh data repair`）。

## 适配版本

- **当前 Skill 版本**：v1.4.1
- **`khquant-to-qmt`**：依据 KhQuant V3.4.1.11 源码和迅投内置 Python 手册（线上文件时间 2026-07-27）编写，2026-11-01 在券商版大QMT 实际回测验证；离线自检需要本机装有 KhQuant 和对应的本地数据
- **主要匹配软件版本**：KhQuant v3.4.1.7
- **基础兼容范围**：KhQuant v3.x
- **需要 v3.4.1.7 的行为**：`khHistory` / `khMA` 不指定 `fq` 时跟随回测的复权方式（更早版本固定前复权），回测中不传时间参数时以当前 K 线为截止。
- **需要 v3.4.1 的能力**：tx 数据源（`--source tx`）、同花顺扶摇数据源（`--source ths`）、`ths_api_key` 配置与脱敏显示、DuckDB 成交量统一按“手”存储。
- **需要 v3.4.0 的能力**：完整 `kh web` 工作台、手机临时访问、Linux Web 发行物、DuckDB 占用诊断，以及 BaoStock/Tushare 按交易日缺口增量补充。
- **需要 v3.3.6 或更高版本的能力**：性能预设 `performance_preset`、`kh run --memory-profile`、`performance_framework_history_preload_days`、`kh tool parquet-cache`、`kh bridge` 以及 `--source http` 桥接数据源。

低于 v3.4.0 时仍可使用基础配置、数据管理、策略开发和普通回测规则，但不要假设 Web 或新版数据管理能力存在；先运行 `kh version` 和对应命令的 `--help` 确认。

## 更新日志

### v1.4.1 (2026-11-01)

- `khquant-to-qmt` 做了一轮全面测试：12 个功能场景和 8 个 khQuant 内置策略，成交全部和 khQuant 引擎逐笔一致。
- 兼容层按 khQuant 的实际行为修正三处：涨跌停校验（市价单不校验，限价、止损单有 `preClose` 就校验）、挂单 `max_pending_bars` 的计数、持仓均价 `avg_price` 的口径。
- `[设置]` 行直接打印回测参数界面要填的百分数；`[自检]` 打印 QMT 内置 Python 版本，资金核对改为按 QMT 收费推算。
- 离线自检比对同一根 K 线里的多笔成交时不再受记录顺序影响。
- 清单增加持仓均价口径（B18）和 `__file__` 路径（C14），共 46 项。

### v1.4.0 (2026-11-01)

- 新增 `khquant-to-qmt` Skill：把 khQuant 回测策略迁移到大QMT 内置 Python（Python 3.6）回测。
- 兼容层 `kh_compat_qmt.py` 在大QMT 里模拟 khQuant 的信号列表、市价/限价/止损单与有效期、盘前盘后回调、日内多次触发、T+1、涨跌停拒单和股数计算，策略代码基本原样粘贴。
- 离线自检 `offline_check.py` 用 khQuant 本地数据模拟 QMT 撮合，逐笔对照成交，比较期末资产，并在两种滑点处理方式里推荐更接近的一种。
- 列出 14 项大QMT 做不到、18 项做法不同、14 项需要实测的内容；其中账号写法、行情索引格式、前复权差异等已在真实大QMT 回测里确认。

### v1.3.3 (2026-10-10)

- 更正订单字段：`khHandlebar` 信号不写 `order_type` 时按市价单处理；`time_in_force` 只认 `day` / `gtd`；`expire_date` 须写成 `YYYY-MM-DD`。
- 精简平台与分发说明，去掉内部发布细节。

### v1.3.2 (2026-10-09)

- 修正策略开发文档：`init(stock_codes, init_data)` 是必需回调且必须带两个参数；`khHistory` 的 `current_time` 不支持 `YYYYMMDDHHMMSS` 连写；信号 `volume` 单位是股。
- 补充 `order_type` / `stop_price` / `time_in_force` / `expire_date` 可选字段、盘前盘后信号转挂单的规则，以及日志 `[TRADE]` 高亮。
- 提示 V3.4.1.9 及更早版本 `kh strategy create` 模板的 init 签名和 .kh 缺 trigger/fields 的问题及处理方法。

### v1.3.1 (2026-10-04)

- 适配 KhQuant V3.4.1.7：`khHistory` / `khMA` 的 `fq` 默认值改为跟随回测复权方式（独立调用仍为前复权），回测中不传时间参数时自动以当前 K 线为截止，分钟级指标在回测中不再受电脑当前时间限制。

### v1.3.0 (2026-09-22)

- 适配 KhQuant V3.4.1，新增 tx 与同花顺（扶摇开放平台）两个数据源的下载、连通性检查和能力边界说明。
- 数据源能力矩阵扩展到 6 个数据源，标明 tx 分钟线的可用历史窗口和同花顺目前只支持日线。
- 敏感信息规则加入同花顺 API Key：由用户自己配置，Skill 不复述、不记录 Key。
- 补充 DuckDB K 线成交量统一以“手”存储的规则，避免建议用户整表换算。
- 故障排查新增“同花顺 API Key 未配置或无效”的处理流程。

### v1.2.0 (2026-08-09)

- 全面适配 KhQuant V3.4.0，新增完整 Web 回测工作台知识与 `kh web` 命令说明。
- 补充浏览器导入项目、参数配置、预检、运行/停止、实时日志、本次结果、历史报告与状态排错流程。
- 加入局域网随机访问密钥、Cloudflare Quick Tunnel 手机临时访问，以及 Nginx/Caddy + 自有域名长期部署的安全边界。
- 更新 Windows、macOS、Linux 平台能力：Linux wheel/Docker 正式包含 CLI 与完整 Web，但不包含 PyQt GUI、miniQMT/xtquant 或 Windows 实盘。
- 明确分发边界：Windows/macOS V3 桌面安装包仅面向官网 VIP 用户；V2.1 保留公开下载；CSkhQuant 公开源码和 Linux 发行物可在 GitHub 发布。
- 补充 DuckDB 短锁写入、数据库占用跳过清单、BaoStock/Tushare 增量补充、Tushare 指数基准与错误返回规则。
- 更新 Claude Code、Codex、Cursor 安装说明，并清理开发机专属路径。
- 新增 Codex 使用的 `agents/openai.yaml` 界面元数据，提供统一名称、简介和默认调用提示。

### v1.0.1 (2026-07-02)

- 同步 KhQuant v3.3.6+ 的 CLI 能力说明，补齐 `performance_preset` 三档性能预设、`kh run --memory-profile` 和 `performance_framework_history_preload_days`（默认 `300`）等性能设置。
- 补充 `kh tool parquet-cache` 缓存包命令，覆盖统计、检查、构建、只读使用和清理流程。
- 补充 `kh bridge serve/status` 与 `kh data download/sync --source http` 的桥接数据源用法。
- 调整 Skill 的安全分级与意图路由，让查询类、修改类和危险类命令边界更清晰。
- 明确 Skill v1.0.1 主要匹配 KhQuant v3.3.6.1；基础功能兼容 KhQuant v3.x，新增性能与桥接命令要求 v3.3.6+。

## 前提条件

- **Claude Code**、**Codex** 或 **Cursor** 等支持 Skill/规则目录的 Agent 工具
- **看海量化回测平台 v3.x**（推荐 V3.4.1，且 `kh` 命令可用）— 本 Skill 不兼容 v2
- 运行 `kh doctor` 检查当前平台、Python、核心依赖和数据目录

> 如尚未安装看海量化回测平台，请前往官网获取：**[https://khsci.com/khQuant/](https://khsci.com/khQuant/)**

## 安装

### 第一步：获取仓库

**方式 A：git clone（推荐，便于后续更新）**

```bash
git clone https://github.com/khscience/khquant-skill.git
cd khquant-skill
```

**方式 B：直接下载 ZIP**

打开 [https://github.com/khscience/khquant-skill](https://github.com/khscience/khquant-skill)，点击 **Code → Download ZIP**，解压到本地。

### 第二步：复制到 Agent 技能目录

两个 Skill 是独立的目录，用哪个复制哪个；下面的命令两个都复制。

**macOS / Linux**：

```bash
mkdir -p ~/.claude/skills
cp -r skills/khquant ~/.claude/skills/
cp -r skills/khquant-to-qmt ~/.claude/skills/
```

**Windows (PowerShell)**：

```powershell
New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.claude\skills" | Out-Null
Copy-Item -Recurse -Force skills\khquant "$env:USERPROFILE\.claude\skills"
Copy-Item -Recurse -Force skills\khquant-to-qmt "$env:USERPROFILE\.claude\skills"
```

**Codex（Windows PowerShell）**：

```powershell
New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.codex\skills" | Out-Null
Copy-Item -Recurse -Force skills\khquant "$env:USERPROFILE\.codex\skills"
Copy-Item -Recurse -Force skills\khquant-to-qmt "$env:USERPROFILE\.codex\skills"
```

**Codex（macOS / Linux）**：

```bash
mkdir -p ~/.codex/skills
cp -r skills/khquant ~/.codex/skills/
cp -r skills/khquant-to-qmt ~/.codex/skills/
```

**Windows (CMD)**：

```cmd
xcopy /E /I /Y skills\khquant "%USERPROFILE%\.claude\skills\khquant"
xcopy /E /I /Y skills\khquant-to-qmt "%USERPROFILE%\.claude\skills\khquant-to-qmt"
```

### 第三步：在 Cursor 中使用（可选）

Cursor 用户可以二选一：

- **Cursor CLI 全局 Skill**：把 `skills/khquant` 复制到 `~/.cursor/skills/`（与 Claude Code 同样的逻辑）
- **项目级规则**：把 `skills/khquant/SKILL.md` 内容粘贴到项目根的 `AGENTS.md`，references 子目录直接放进项目内即可

### 第四步：触发

重启对应 Agent 工具，用自然语言即可触发：

```
帮我跑一下双均线策略
下载沪深300日线数据
查看上次回测结果
创建一个新的 RSI 策略
我的环境有什么问题？
把 allstrategies 里的双均线策略迁移到大QMT
这个策略搬到大QMT 回测，哪些功能做不到？
QMT 回测结果和 khQuant 对不上，帮我对账
```

支持显式 Skill 调用的工具，也可以使用 `$khquant`、`$khquant-to-qmt` 或该工具提供的同名 Skill 入口。

## 后续更新

如果用 git clone 方式安装，仓库有更新时直接拉取并重新复制即可：

```bash
cd khquant-skill
git pull
cp -r skills/khquant ~/.claude/skills/          # macOS / Linux
cp -r skills/khquant-to-qmt ~/.claude/skills/
```

如果希望省掉手动复制，可以用软链接（macOS / Linux）或目录联接（Windows）让两个目录始终保持一致：

```bash
# macOS / Linux
rm -rf ~/.claude/skills/khquant
ln -s "$(pwd)/skills/khquant" ~/.claude/skills/khquant
```

```powershell
# Windows，需以管理员身份执行
Remove-Item -Recurse -Force "$env:USERPROFILE\.claude\skills\khquant" -ErrorAction SilentlyContinue
New-Item -ItemType Junction -Path "$env:USERPROFILE\.claude\skills\khquant" -Target "$PWD\skills\khquant"
```

## 目录结构

```
khquant-skill/
├── README.md                       本文件
├── LICENSE                         MIT
├── skills/khquant/
│   ├── SKILL.md                    技能入口（意图路由 + 执行原则）
│   ├── agents/openai.yaml          Codex 界面名称、简介与默认提示
│   └── references/
│       ├── setup.md                首次配置
│       ├── data-management.md      数据管理
│       ├── strategy-development.md 策略开发（含 API、MyTT 指标库、.kh 配置）
│       ├── backtesting.md          回测执行
│       ├── web-backtesting.md      Web 工作台、远程访问与状态排错
│       ├── results-analysis.md     结果分析
│       ├── troubleshooting.md      故障排查
│       ├── command-reference.md    命令速查
│       └── pools-and-codes.md      股票池规范
└── skills/khquant-to-qmt/
    ├── SKILL.md                    迁移流程、两条路线、报告模板、Python 3.6 清单
    ├── agents/openai.yaml          Codex 界面名称、简介与默认提示
    ├── assets/
    │   ├── kh_compat_qmt.py        兼容层底稿（粘贴进大QMT 的策略文件就从它开始）
    │   └── example_dual_ma_section.py  双均线策略迁移后的示例
    ├── scripts/
    │   └── offline_check.py        本机离线自检：模拟 QMT 撮合并逐笔对照 khQuant
    └── references/
        ├── not-supported.md        大QMT 做不到 / 做法不同 / 需实测的清单
        ├── backtest-settings.md    .kh 配置到 QMT 回测设置的对照
        ├── function-mapping.md     khQuant 函数到 QMT 原生写法的对照
        └── live-trading.md         转模拟盘或实盘的注意事项
```

## 卸载

删除技能目录即可：

```bash
# macOS / Linux
rm -rf ~/.claude/skills/khquant ~/.claude/skills/khquant-to-qmt

# Windows
rmdir /S /Q "%USERPROFILE%\.claude\skills\khquant"
rmdir /S /Q "%USERPROFILE%\.claude\skills\khquant-to-qmt"
```

## 贡献

欢迎 Issue 和 Pull Request：

- 发现 Bug 或文档错误：[提 Issue](https://github.com/khscience/khquant-skill/issues)
- 想新增策略剧本、扩展 references：欢迎 Fork 后 PR
- 二次创作（改关键词、加新场景）也鼓励通过 Fork 维护，并在 Issue 中分享思路

## 版本

- **v1.4.1** — `khquant-to-qmt` 全面测试后修正涨跌停、挂单计数和持仓均价口径，补真实大QMT 实测结论
- **v1.4.0** — 新增 `khquant-to-qmt`：把 khQuant 回测策略迁移到大QMT 内置 Python，含兼容层、离线自检和做不到清单
- **v1.3.3** — 更正订单类型默认值与 expire_date 格式，精简分发说明
- **v1.3.2** — 修正策略开发文档（init 签名、current_time 格式、volume 单位），补充订单类型与挂单规则
- **v1.3.1** — 主要匹配 KhQuant V3.4.1.7；更新 khHistory / khMA 的复权与截止时间默认行为
- **v1.3.0** — 主要匹配 KhQuant V3.4.1；新增 tx 与同花顺数据源、API Key 脱敏规则和成交量单位约定
- **v1.2.0** — 主要匹配 KhQuant V3.4.0；新增完整 Web、手机临时访问、Linux Web、数据库锁诊断、增量补充及平台/分发边界
- **v1.0.1** — 主要匹配 KhQuant v3.3.6.1；同步 KhQuant v3.3.6+ CLI 指令，补充性能设置、Parquet 缓存包和桥接数据源说明
- **v1.0.0** — 适配 KhQuant CLI v3.x

## 许可

[MIT](./LICENSE) © 看海量化 (KhQuant)

## 相关链接

- 看海量化官网：[https://khsci.com/khQuant/](https://khsci.com/khQuant/)
- 公众号：**看海的城堡**
