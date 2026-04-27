# 结果分析指南

## 查看回测列表

```bash
# 最近 20 次
kh result list

# 显示全部
kh result list --all

# 按策略名过滤
kh result list --strategy 双均线

# JSON 格式
kh result list --json
```

## 查看回测摘要

```bash
# 最近一次
kh result show

# 按序号查看（1 = 最新）
kh result show --id 3

# 指定目录
kh result show strategy_cf1bc5f7_20250101_20250703_20260220_175244

# JSON 格式
kh result show --json
```

### 输出示例

```
  > 回测: strategy_cf1bc5f7_20250101_20250703
  > 策略: 双均线精简_使用khMA函数.py
  > 区间: 20250101 ~ 20250703

  ══════════════════════════════════════════════════
  绩效指标
  ──────────────────────────────────────────────────
  初始资金:      1,000,000.00
  最终资金:      1,081,391.77
  总收益率:      +8.14%        ← 红色（A 股涨红配色）
  年化收益率:    +17.71%       ← 红色
  最大回撤:      4.82%
  交易天数:      120 天
  ══════════════════════════════════════════════════
```

### 指标含义

| 指标 | 含义 | 参考标准 |
|------|------|---------|
| **总收益率** | 回测期间净收益百分比 | >0 为盈利 |
| **年化收益率** | 折算为一年的收益率 | >10% 较好，>20% 优秀 |
| **最大回撤** | 净值从峰值到谷值的最大跌幅 | <10% 良好，>20% 需关注风控 |
| **交易天数** | 回测覆盖的交易日数量 | 越多越有统计意义 |

### 配色约定

采用 A 股配色：正收益为红色（涨），负收益为绿色（跌）。

## 生成 HTML 报告

```bash
# 最近一次回测
kh result report

# 按序号
kh result report --id 2

# 不自动打开浏览器
kh result report --no-open

# 自定义输出路径
kh result report --output D:\reports\my_report.html

# 生成所有回测的索引页
kh result report --index
```

### 报告包含内容

- 净值曲线（策略 vs 基准）
- 回撤曲线
- 月度收益热力图
- 交易记录表
- 逐日收益表
- 个股分析
- 收益分布直方图

## 对比多次回测

```bash
# 对比最近 3 次
kh result compare

# 对比最近 5 次
kh result compare --last 5
```

输出横向对比表格，包含策略名、总收益率、年化收益率、最大回撤、交易天数。

## 清理旧回测

```bash
# 预览将要删除的内容（不实际删除）
kh result clean --dry-run

# 保留最近 10 次，删除其余
kh result clean --keep 10

# 保留最近 5 次
kh result clean --keep 5
```

注意：此操作不可逆，建议先用 `--dry-run` 预览。

## summary.csv 字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `init_capital` | float | 初始资金 |
| `final_capital` | float | 最终资金 |
| `total_return` | float | 总收益率（%）|
| `annual_return` | float | 年化收益率（%）|
| `max_drawdown` | float | 最大回撤（%）|
| `trade_days` | int | 交易天数 |
