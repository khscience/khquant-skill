# KhQuant Skill for Claude Code & Cursor

> 看海量化回测平台 (KhQuant) 的 AI Skill 插件 — 用自然语言驱动 `kh` 命令完成数据管理、策略开发、回测执行和结果分析。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)](#版本)
[![KhQuant](https://img.shields.io/badge/KhQuant-v3.x-green.svg)](https://khsci.com/khQuant/)

---

## 是什么

这是一份按 [Anthropic Skill 规范](https://docs.anthropic.com/en/docs/build-with-claude/skills) 组织的知识包，包含：

- 一份入口文件 `SKILL.md`（意图路由 + 执行原则）
- 八份 references 子文档（首次配置 / 数据管理 / 策略开发 / 回测执行 / 结果分析 / 故障排查 / 命令速查 / 股票池规范）

安装后，Claude Code 会在用户提到"回测"、"看海量化"、"kh 命令"、"双均线"、"MACD"等关键词时自动激活，按 Skill 中的安全分级和场景剧本调用 `kh` 命令完成操作。

> 关于该 Skill 的设计思路与详细说明，可参考公众号文章「看海量化专属 Skill 插件全解析」。

## 主要能力

- **首次配置** — 引导完成 `kh init` 初始化
- **数据管理** — 下载、查看、导出、扫描、同步股票数据
- **策略开发** — 创建、校验策略，理解回调函数与信号格式
- **回测执行** — 运行回测、参数覆盖、生成 HTML 报告
- **结果分析** — 查看摘要、对比多次回测、解读绩效指标
- **故障排查** — 自动识别常见错误并给出修复方案

内置三色灯安全分级：查询类自动执行，修改类需用户确认，危险类必须明确授权（如 `kh result clean`、`kh data repair`）。

## 前提条件

- **Claude Code** 桌面端、CLI 或 VS Code 扩展任意一种；或 **Cursor**（CLI / IDE）
- **看海量化回测平台 v3.x**（`kh` 命令可用）— 本 Skill 仅适配 v3，不兼容 v2
- Python 3.8+ 及核心依赖（运行 `kh doctor` 检查）

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

### 第二步：复制到 Claude Code 技能目录

**macOS / Linux**：

```bash
mkdir -p ~/.claude/skills
cp -r skills/khquant ~/.claude/skills/
```

**Windows (PowerShell)**：

```powershell
New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.claude\skills" | Out-Null
Copy-Item -Recurse -Force skills\khquant "$env:USERPROFILE\.claude\skills\khquant"
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

重启 Claude Code，用自然语言即可触发：

```
帮我跑一下双均线策略
下载沪深300日线数据
查看上次回测结果
创建一个新的 RSI 策略
我的环境有什么问题？
```

也可以通过 `/khquant` 手动调用。

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
    └── references/
        ├── setup.md                首次配置
        ├── data-management.md      数据管理
        ├── strategy-development.md 策略开发（含 API、MyTT 指标库、.kh 配置）
        ├── backtesting.md          回测执行
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

- **v1.0.0** — 适配 KhQuant CLI v3.x

## 许可

[MIT](./LICENSE) © 看海量化 (KhQuant)

## 相关链接

- 看海量化官网：[https://khsci.com/khQuant/](https://khsci.com/khQuant/)
- 公众号：**看海的城堡**
