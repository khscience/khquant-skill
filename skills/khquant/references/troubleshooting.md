# 故障排查指南

## 已知错误速查表

### 1. 尚未初始化

```
ERR 尚未初始化，请先运行: kh init
```

**原因**：`~/.khquant/settings.json` 不存在。
**修复**：运行 `kh init` 完成首次配置。

---

### 2. PowerShell 无法识别 kh 命令

```
kh : 无法将"kh"项识别为 cmdlet、函数、脚本文件或可运行程序的名称
```

**修复方案**（任选一种）：
- 在项目根目录执行：`.\kh init`
- 执行一次 `.\setup_kh_profile.ps1` 配置 PATH
- 直接用：`python kh.py <command>`

---

### 3. PowerShell 参数歧义（-o 报错）

```
kh : 无法处理参数，因为参数名称"o"具有二义性。可能的匹配项包括: -OutVariable -OutBuffer
```

**原因**：PowerShell 把 `-o` 当成自己的内置参数前缀。
**修复**：使用 `--output` 代替 `-o`：

```bash
# 错误
kh data export 000001.SZ -o output.csv

# 正确
kh data export 000001.SZ --output output.csv
```

---

### 4. xtquant 无法连接

```
ERR xtquant 无法连接，请确认 QMT 客户端已启动并登录
```

**修复**：
- 确保 QMT 客户端正在运行且已登录
- 如果只用 DuckDB 本地数据，可切换数据源：`kh config set backtest_data_source duckdb`

---

### 5. DuckDB 数据库被锁定

```
ERR DuckDB 数据库被其他进程占用，无法打开
> 被锁文件: D:\khData\metadata.db
> 占用进程: python.exe (PID 12345)
```

**原因**：DuckDB 允许多个只读进程，或一个读写进程，但不同配置的跨进程连接不能同时打开同一个 `.db`。回测长期读取某只股票时，该股票文件可能阻止另一进程写入。

**当前开发版行为**：
- 单股票文件的读取和写入都会先自动重试 5 次，采用指数退避。
- GUI 重试耗尽后可选择继续重试、先跳过或停止任务；不要默认结束占用进程。
- 数据补充跳过项会出现在完成日志/弹窗中，且不会记为已完成。
- 回测跳过项写入结果目录 `duckdb_lock_skips.csv`，`summary.csv` 同时记录数量；占用异常不会再被误判为普通“无数据”。
- CLI/网页回测无法阻塞等待桌面弹窗时，重试耗尽后默认跳过并在结果中醒目标记。

**人工处理**：如果必须立即写入同一股票，可先停止正在读取它的回测；只有确认该进程可以结束时，才使用任务管理器或 `taskkill /pid 12345 /f`。

---

### 6. DuckDB 数据库损坏

```
ERR 数据库文件可能损坏
```

**修复**：

```bash
kh data repair
```

---

### 7. BaoStock 未安装

```
ERR baostock 未安装，请运行: pip install baostock
```

**修复**：

```bash
pip install baostock
```

---

### 8. Tushare Token 未配置

```
ERR Tushare Token 未配置，请运行: kh config set tushare_token <token>
```

**修复**：
1. 在 https://tushare.pro 注册并获取 Token
2. `kh config set tushare_token <你的token>`

如果数据管理日志显示 `Tushare ... 接口调用失败`，这是网络、积分权限、限流或服务端异常，不是“该股票无行情”。先根据错误文字检查 API 地址和权限，再重试；程序不会再把这类错误记成成功 0 条。

如果弹出“数据库文件正在使用”，系统已经自动重试 5 次。可选择继续重试、先跳过或停止任务；跳过清单会出现在结束日志中。行情已经写入但仅 `metadata.db` 刷新失败时，稍后执行数据目录扫描修复即可，无需重新下载行情。

---

### 9. schedule 库缺失（定时同步）

```
WARN schedule 未安装（影响: kh data sync --schedule）
```

**修复**：

```bash
pip install schedule
```

---

### 10. update-pool 失败

```
ERR 更新失败: 'KhQuTools' object has no attribute...
```

**原因**：`kh data update-pool` 需要 xtquant (miniQMT) 支持。
**修复**：确保 QMT 客户端已启动并登录，且 xtquant 已正确安装。

---

### 11. 回测进程不退出

回测完成后终端无响应。

**原因**：xtquant 后台线程阻止进程正常退出。CLI 已内置 `os._exit()` 强制退出机制，正常使用无需关注。如果仍然卡住，按 `Ctrl+C` 终止。

---

### 12. 策略文件找不到

```
ERR 文件未找到: xxx.py
```

**修复**：
- 检查 .kh 配置中 `strategy_file` 路径是否正确
- 使用绝对路径，或确保路径相对于 .kh 文件所在目录

---

### 13. 首次下载时基准数据下载慢

首次执行 `kh data download` 时会自动下载 000300.SH（沪深300指数）2010 年至今的日线数据，这是正常行为。根据网络情况可能需要几分钟。

---

## 通用排查步骤

遇到未知错误时：

1. **运行诊断**：`kh doctor` 查看环境状态
2. **查看配置**：`kh config show` 确认路径和参数
3. **详细模式**：`kh run config.kh --verbose` 查看 DEBUG 日志
4. **检查数据**：`kh data info <代码>` 确认数据是否存在
5. **获取帮助**：`kh <command> --help` 查看命令用法
