# KhQuant Skill for Claude Code、Codex & Cursor

> 看海量化回测平台 (KhQuant) 的 AI Skill 插件 — 用自然语言完成数据管理、策略开发、桌面/CLI/Web 回测、结果分析和故障排查。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Version](https://img.shields.io/badge/version-1.3.0-blue.svg)](#版本)
[![KhQuant](https://img.shields.io/badge/KhQuant-v3.4.1-green.svg)](https://khsci.com/khQuant/)

---

## 是什么

这是一份面向 Claude Code、Codex、Cursor 等 Agent 工具组织的知识包，包含：

- 一份入口文件 `SKILL.md`（意图路由 + 执行原则）
- 九份 references 子文档（首次配置 / 数据管理 / 策略开发 / 回测执行 / Web 回测 / 结果分析 / 故障排查 / 命令速查 / 股票池规范）

安装后，Agent 会在用户提到“回测”“看海量化”“kh web”“DuckDB”“双均线”“MACD”等任务时加载对应规则，按安全分级和场景流程操作看海量化。

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

内置三色灯安全分级：查询类自动执行，修改类需用户确认，危险类必须明确授权（如 `kh result clean`、`kh data repair`）。

## 适配版本

- **当前 Skill 版本**：v1.3.0
- **主要匹配软件版本**：KhQuant v3.4.1
- **基础兼容范围**：KhQuant v3.x
- **需要 v3.4.1 的能力**：tx 数据源（`--source tx`）、同花顺扶摇数据源（`--source ths`）、`ths_api_key` 配置与脱敏显示、DuckDB 成交量统一按“手”存储。
- **需要 v3.4.0 的能力**：完整 `kh web` 工作台、手机临时访问、Linux Web 发行物、DuckDB 占用诊断，以及 BaoStock/Tushare 按交易日缺口增量补充。
- **需要 v3.3.6 或更高版本的能力**：性能预设 `performance_preset`、`kh run --memory-profile`、`performance_framework_history_preload_days`、`kh tool parquet-cache`、`kh bridge` 以及 `--source http` 桥接数据源。

低于 v3.4.0 时仍可使用基础配置、数据管理、策略开发和普通回测规则，但不要假设 Web 或新版数据管理能力存在；先运行 `kh version` 和对应命令的 `--help` 确认。

## 更新日志

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

**macOS / Linux**：

```bash
mkdir -p ~/.claude/skills
cp -r skills/khquant ~/.claude/skills/
```

**Windows (PowerShell)**：

```powershell
New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.claude\skills" | Out-Null
Copy-Item -Recurse -Force skills\khquant "$env:USERPROFILE\.claude\skills"
```

**Codex（Windows PowerShell）**：

```powershell
New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.codex\skills" | Out-Null
Copy-Item -Recurse -Force skills\khquant "$env:USERPROFILE\.codex\skills"
```

**Codex（macOS / Linux）**：

```bash
mkdir -p ~/.codex/skills
cp -r skills/khquant ~/.codex/skills/
```

**Windows (CMD)**：

```cmd
xcopy /E /I /Y skills\khquant "%USERPROFILE%\.claude\skills\khquant"
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
```

支持显式 Skill 调用的工具，也可以使用 `$khquant` 或该工具提供的同名 Skill 入口。

## 后续更新

如果用 git clone 方式安装，仓库有更新时直接拉取并重新复制即可：

```bash
cd khquant-skill
git pull
cp -r skills/khquant ~/.claude/skills/   # macOS / Linux
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
└── skills/khquant/
    ├── SKILL.md                    技能入口（意图路由 + 执行原则）
    ├── agents/openai.yaml          Codex 界面名称、简介与默认提示
    └── references/
        ├── setup.md                首次配置
        ├── data-management.md      数据管理
        ├── strategy-development.md 策略开发（含 API、MyTT 指标库、.kh 配置）
        ├── backtesting.md          回测执行
        ├── web-backtesting.md      Web 工作台、远程访问与状态排错
        ├── results-analysis.md     结果分析
        ├── troubleshooting.md      故障排查
        ├── command-reference.md    命令速查
        └── pools-and-codes.md      股票池规范
```

## 卸载

删除技能目录即可：

```bash
# macOS / Linux
rm -rf ~/.claude/skills/khquant

# Windows
rmdir /S /Q "%USERPROFILE%\.claude\skills\khquant"
```

## 贡献

欢迎 Issue 和 Pull Request：

- 发现 Bug 或文档错误：[提 Issue](https://github.com/khscience/khquant-skill/issues)
- 想新增策略剧本、扩展 references：欢迎 Fork 后 PR
- 二次创作（改关键词、加新场景）也鼓励通过 Fork 维护，并在 Issue 中分享思路

## 版本

- **v1.3.0** — 主要匹配 KhQuant V3.4.1；新增 tx 与同花顺数据源、API Key 脱敏规则和成交量单位约定
- **v1.2.0** — 主要匹配 KhQuant V3.4.0；新增完整 Web、手机临时访问、Linux Web、数据库锁诊断、增量补充及平台/分发边界
- **v1.0.1** — 主要匹配 KhQuant v3.3.6.1；同步 KhQuant v3.3.6+ CLI 指令，补充性能设置、Parquet 缓存包和桥接数据源说明
- **v1.0.0** — 适配 KhQuant CLI v3.x

## 许可

[MIT](./LICENSE) © 看海量化 (KhQuant)

## 相关链接

- 看海量化官网：[https://khsci.com/khQuant/](https://khsci.com/khQuant/)
- 公众号：**看海的城堡**
