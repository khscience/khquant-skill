# -*- coding: utf-8 -*-
"""离线自检：在装了 khQuant 的电脑上，用本地 DuckDB 数据模拟大QMT回测撮合，
跑「兼容层 + 迁移后的策略」，再和 khQuant 回测的 trades.csv 逐笔对照。

模拟的 QMT 规则只取迅投知识库写明的部分：
  - 指定价落在当根 [最低, 最高] 内按指定价成交，否则按收盘价成交
  - 卖出数量超过可用数量时按可用数量成交；股票 T+1
  - 费用按兼容层 qmt_ui_settings() 给出的「QMT 回测参数该填的值」收：佣金（含最低）双边、卖出印花税
策略可以另取不同复权的数据（如用不复权价算指标），脚本会按需读取对应的复权列。

两种滑点模式（KH_CONFIG['slippage_mode']）各跑一遍，推荐期末资产更接近 khQuant 的那种：
  - commission：委托价不加滑点，滑点折进 QMT 佣金率。滑点大（每股一分钱以上）时更准
  - price：滑点加进委托价。滑点不到一分钱时 khQuant 取整后常常没有滑点，这种模式更准
QMT 真实回测还会受行情源、复权口径、费用设置影响，自检通过不代表 QMT 结果一定相同。

用法（在任意目录，用装了 duckdb/pandas 的 Python 3.8+）：
  python offline_check.py --compat kh_compat_qmt.py --strategy 迁移后策略段.py \
      --data-root D:/khData --stocks 000001.SZ --start 20230101 --end 20241231 \
      --period 1d --dividend-type front --kh-trades <khQuant回测目录>/trades.csv \
      --config '{"commission_rate": 0.0001, "min_commission": 5, "stamp_tax_rate": 0.0005}'
--strategy 只放 khQuant 策略那一段（kh_init / khHandlebar / khPreMarket / khPostMarket 及其依赖），
不要包含兼容层本身。--config 里的键会覆盖 KH_CONFIG（费用、滑点、盘前盘后等要和 .kh 一致）。
退出码：0 通过（成交时间、代码、方向逐笔一致），1 不通过。
"""
import argparse
import ast
import json
import os
import sys
from datetime import datetime

import duckdb
import pandas as pd

ADJ_FIELDS = ('open', 'high', 'low', 'close')


def parse_args():
    p = argparse.ArgumentParser(description='khQuant -> 大QMT 迁移离线自检')
    p.add_argument('--compat', required=True, help='kh_compat_qmt.py 路径')
    p.add_argument('--strategy', required=True, help='迁移后的策略段（不含兼容层）')
    p.add_argument('--data-root', required=True, help='khQuant DuckDB 数据目录（只读）')
    p.add_argument('--stocks', required=True, help='股票池，逗号分隔')
    p.add_argument('--start', required=True)
    p.add_argument('--end', required=True)
    p.add_argument('--period', default='1d', choices=['1d', '1m', '5m'])
    p.add_argument('--dividend-type', default='front')
    p.add_argument('--capital', type=float, default=1000000.0)
    p.add_argument('--kh-trades', help='khQuant 回测结果里的 trades.csv，用来对照（同目录有 daily_stats.csv 时还会比期末资产）')
    p.add_argument('--config', default='{}', help='覆盖 KH_CONFIG 的 JSON')
    p.add_argument('--slippage-mode', default='auto', choices=['auto', 'commission', 'price'],
                   help='auto：两种模式都跑并推荐一种')
    p.add_argument('--warmup-days', type=int, default=400, help='回测开始前多读的自然日数')
    return p.parse_args()


def db_path(root, code):
    num, market = code.split('.')
    for m in (market.upper(), market.lower()):
        path = os.path.join(root, m, num + '.db')
        if os.path.exists(path):
            return path
    raise SystemExit('找不到 %s 的数据库：%s' % (code, os.path.join(root, market.upper(), num + '.db')))


def load_bars(root, code, period, start, end, warmup_days):
    table = {'1d': 'kline_1d', '1m': 'kline_1m', '5m': 'kline_5m'}[period]
    begin = (pd.Timestamp(start) - pd.Timedelta(days=warmup_days)).strftime('%Y-%m-%d')
    stop = (pd.Timestamp(end) + pd.Timedelta(days=1)).strftime('%Y-%m-%d')
    con = duckdb.connect(db_path(root, code), read_only=True)
    try:
        df = con.execute('SELECT * FROM %s WHERE time >= ? AND time < ? ORDER BY time' % table,
                         [begin, stop]).fetchdf()
    finally:
        con.close()
    fmt = '%Y%m%d' if period == '1d' else '%Y%m%d%H%M%S'
    df['key'] = pd.to_datetime(df['time']).dt.strftime(fmt)
    return df.drop_duplicates('key', keep='last').set_index('key')


def check_syntax(compat_src, strategy_src):
    for name, src in (('兼容层', compat_src), ('策略', strategy_src)):
        try:
            ast.parse(src, feature_version=(3, 6))
        except SyntaxError as exc:
            raise SystemExit('%s 不符合 Python 3.6 语法（QMT 内置版本）：%s' % (name, exc))
    print('Python 3.6 语法检查通过')


def simulate(args, bars, timeline, compat_src, strategy_src, mode):
    """在模拟的 QMT 回测里跑一遍，返回成交和期末资产。"""
    codes = list(bars)
    period, div = args.period, args.dividend_type
    fmt = '%Y%m%d' if period == '1d' else '%Y%m%d%H%M%S'
    warned_div = set()

    def col(df, field, use_div=None):
        use_div = div if use_div in (None, 'follow') else use_div
        if use_div != 'none' and field in ADJ_FIELDS:
            name = field + '_' + use_div
            if name not in df.columns:
                raise AssertionError('本地库没有 %s 列，策略要的复权价在 khQuant 里没下载' % name)
            return df[name]
        return df[field]

    def timetag_to_datetime(tag, f):
        return datetime.fromtimestamp(tag / 1000.0).strftime(f)

    class Obj(object):
        pass

    class MockC(object):
        def __init__(self):
            self.period, self.barpos = period, 0
            self.stockcode, self.market = codes[0].split('.')

        def get_bar_timetag(self, pos):
            return int(datetime.strptime(timeline[pos], fmt).timestamp() * 1000)

        def get_market_data_ex(self, fields, stock_code, period=period, start_time='', end_time='', count=-1,
                               dividend_type='follow', fill_data=True, subscribe=True):
            if subscribe:
                raise AssertionError('回测里取数要用 subscribe=False')
            use_div = div if dividend_type in ('follow', None) else dividend_type
            if use_div != div and use_div not in warned_div:
                warned_div.add(use_div)
                print('提示：策略另取了 %s 复权的数据（回测主复权是 %s）' % (use_div, div))
            out = {}
            for code in stock_code:
                df = bars[code]
                part = df
                if end_time:
                    limit = str(end_time)[:8] if period == '1d' else (str(end_time) + '000000')[:14]
                    part = part[part.index <= limit]
                if start_time:
                    s = str(start_time)[:8] if period == '1d' else (str(start_time) + '000000')[:14]
                    part = part[part.index >= s]
                if count and count > 0:
                    part = part.tail(count)
                out[code] = pd.DataFrame({f: col(part, f, use_div).values for f in fields}, index=part.index)
            return out

    C = MockC()
    account = {'cash': args.capital}
    positions = {}
    fills = []
    ns = {}

    def cur_bar(code):
        k = timeline[C.barpos]
        df = bars[code]
        if k not in df.index:
            return None
        row = df.loc[[k]]
        return {f: float(col(row, f).iloc[0]) for f in ADJ_FIELDS}

    def passorder(op, otype, acc, code, prtype, price, volume, ContextInfo, *rest):
        if otype != 1101 or prtype != 11:
            raise AssertionError('兼容层应只用 1101 + 指定价 11，收到 %s/%s' % (otype, prtype))
        bar = cur_bar(code)
        if bar is None:
            fills.append((timeline[C.barpos], code, 'NO_BAR', price, volume))
            return
        fill = price if bar['low'] - 1e-9 <= price <= bar['high'] + 1e-9 else bar['close']
        pos = positions.setdefault(code, {'volume': 0, 'can_use': 0, 'cost': 0.0})
        if op == 24:
            volume = min(volume, pos['can_use'])
        if volume <= 0:
            return
        action = 'buy' if op == 23 else 'sell'
        ui = ns['qmt_ui_settings'](code, fill)
        amount = fill * volume
        cost = max(amount * ui['commission_rate'], ui['min_commission'])
        if action == 'sell':
            cost += amount * ui['stamp_tax_sell']
        if action == 'buy':
            if amount + cost > account['cash'] + 1e-6:
                fills.append((timeline[C.barpos], code, 'REJECT_CASH', fill, volume))
                return
            account['cash'] -= amount + cost
            pos['cost'] = (pos['cost'] * pos['volume'] + amount) / (pos['volume'] + volume)
            pos['volume'] += volume
            if ns['_S'].t0_mode:
                pos['can_use'] += volume
        else:
            account['cash'] += amount - cost
            pos['volume'] -= volume
            pos['can_use'] -= volume
        fills.append((timeline[C.barpos], code, action, round(fill, 3), volume))

    def market_value():
        total = 0.0
        for code, p in positions.items():
            if p['volume'] <= 0:
                continue
            df = bars[code]
            k = [x for x in df.index if x <= timeline[C.barpos]][-1]
            total += p['volume'] * float(col(df.loc[[k]], 'close').iloc[0])
        return total

    def get_trade_detail_data(acc, atype, kind, *rest):
        if kind == 'account':
            a = Obj()
            mv = market_value()
            a.m_dAvailable, a.m_dBalance, a.m_dInstrumentValue, a.m_dFrozenCash = account['cash'], account['cash'] + mv, mv, 0.0
            return [a]
        if kind == 'position':
            res = []
            for code, p in positions.items():
                if p['volume'] <= 0:
                    continue
                o = Obj()
                o.m_strInstrumentID, o.m_strExchangeID = code.split('.')
                o.m_nVolume, o.m_nCanUseVolume, o.m_dOpenPrice, o.m_dMarketValue = p['volume'], p['can_use'], p['cost'], 0.0
                res.append(o)
            return res
        return []

    ns.update({'__name__': 'qmt_strategy', 'timetag_to_datetime': timetag_to_datetime,
               'passorder': passorder, 'get_trade_detail_data': get_trade_detail_data})
    exec(compile(compat_src, os.path.basename(args.compat), 'exec'), ns)
    exec(compile(strategy_src, os.path.basename(args.strategy), 'exec'), ns)
    cfg = {'stock_list': codes, 'start_date': args.start, 'end_date': args.end, 'init_capital': args.capital,
           'period': period, 'dividend_type': div, 'verbose': False, 'selfcheck': False}
    cfg.update(json.loads(args.config))
    cfg['slippage_mode'] = mode
    ns['KH_CONFIG'].update(cfg)

    ns['init'](C)
    last_day = None
    for i, k in enumerate(timeline):
        C.barpos = i
        if k[:8] != last_day:
            if not ns['_S'].t0_mode:
                for p in positions.values():
                    p['can_use'] = p['volume']
            last_day = k[:8]
        ns['handlebar'](C)

    out = pd.DataFrame(fills, columns=['time', 'code', 'action', 'price', 'volume'])
    cut = 8 if period == '1d' else 14
    log = pd.DataFrame([(t[:cut], c, a, round(kf, 3), v, op) for t, c, a, v, op, kf in ns['_S'].trade_log],
                       columns=['time', 'code', 'action', 'price', 'volume', 'order_price'])
    ui = ns['qmt_ui_settings']()
    return {'mode': mode, 'fills': out, 'log': log, 'final_asset': account['cash'] + market_value(), 'ui': ui}


def compare(res, kh, kh_final, period):
    """打印一种模式的对照结果，返回 (是否通过, 期末差距%)。"""
    out, qm = res['fills'], res['log']
    qmt_fills = out[out.action.isin(['buy', 'sell'])]
    bad = out[~out.action.isin(['buy', 'sell'])]
    print('—— 滑点模式 %s ——' % res['mode'])
    ui = res['ui']
    if ui.get('slip_ratio_folded') is not None or res['mode'] == 'price':
        pct = lambda x: ('%.6f' % (x * 100)).rstrip('0').rstrip('.') or '0'  # 界面单位是 %
        print('QMT 回测参数（界面单位是 %%）：买入佣金=平昨佣金=平今佣金=%s，最低佣金=%s 元，卖出印花税=%s，滑点值=0，最大成交比例=100'
              % (pct(ui['commission_rate']), ui['min_commission'], pct(ui['stamp_tax_sell'])))
    print('模拟 QMT 成交 %d 笔，期末资产 %.2f' % (len(qmt_fills), res['final_asset']))
    if len(bad):
        print('模拟 QMT 拒单或无行情 %d 笔：' % len(bad))
        print(bad.head(10).to_string(index=False))
    if kh is None:
        print(qm.to_string(index=False))
        return len(qm) > 0, None
    ok = True
    if len(qm) == 0:
        print('不通过：兼容层一笔都没成交。先看日志里的拒单、取不到数据、账号查不到等提示')
        ok = False
    elif len(qm) != len(kh):
        print('不通过：成交笔数不同（兼容层 %d，khQuant %d）' % (len(qm), len(kh)))
    same_path = len(qm) > 0 and list(zip(qm.time, qm.code, qm.action)) == list(zip(kh.time, kh.code, kh.action))
    print('成交时间、代码、方向逐笔一致：%s' % ('是' if same_path else '否'))
    ok = ok and same_path
    rows = []
    for i in range(min(len(qm), len(kh))):
        a, b = qm.iloc[i], kh.iloc[i]
        if (a.time, a.code, a.action) != (b.time, b.code, b.action) or abs(a.price - b.price) > 1e-9 or int(a.volume) != int(b.volume):
            rows.append((i, a.time, a.code, a.action, a.price, int(a.volume), a.order_price, b.time, b.action, b.price, int(b.volume)))
    if rows:
        diff = pd.DataFrame(rows, columns=['序号', '兼容层时间', '代码', '方向', 'khQuant口径价', '股数', '委托价',
                                           'khQuant时间', 'khQuant方向', 'khQuant价', 'khQuant股数'])
        print('khQuant 口径价格或股数有差异的成交 %d 笔（前 10 笔）：' % len(diff))
        print(diff.head(10).to_string(index=False))
    elif len(qm):
        print('khQuant 口径的价格和股数也逐笔一致')
    gap = None
    if kh_final:
        gap = (res['final_asset'] / kh_final - 1) * 100
        print('期末资产：模拟 QMT %.2f，khQuant %.2f，差 %+.2f%%' % (res['final_asset'], kh_final, gap))
    return ok, gap


def main():
    args = parse_args()
    codes = [c.strip().upper() for c in args.stocks.split(',') if c.strip()]
    bars = {c: load_bars(args.data_root, c, args.period, args.start, args.end, args.warmup_days) for c in codes}
    div = args.dividend_type
    for c, df in bars.items():
        if div != 'none':
            missing = [f + '_' + div for f in ADJ_FIELDS if f + '_' + div not in df.columns]
            if missing:
                raise SystemExit('%s 缺少复权列 %s，先在 khQuant 补下载对应复权价' % (c, missing))
    # QMT 的 handlebar 按主图 K 线触发；这里用股票池里所有出现过的 K 线时间当主图
    keys = sorted(set().union(*[set(df.index) for df in bars.values()]))
    timeline = [k for k in keys if args.start <= k[:8] <= args.end]

    compat_src = open(args.compat, encoding='utf-8').read()
    strategy_src = open(args.strategy, encoding='utf-8').read()
    check_syntax(compat_src, strategy_src)

    kh, kh_final = None, None
    if args.kh_trades:
        cut = 8 if args.period == '1d' else 14
        kh = pd.read_csv(args.kh_trades, encoding='utf-8-sig')
        kh['time'] = kh['datetime'].astype(str).str.replace(r'\D', '', regex=True).str[:cut]
        kh = kh[['time', 'code', 'action', 'price', 'volume']].reset_index(drop=True)
        print('khQuant 成交 %d 笔' % len(kh))
        daily = os.path.join(os.path.dirname(os.path.abspath(args.kh_trades)), 'daily_stats.csv')
        if os.path.exists(daily):
            kh_final = float(pd.read_csv(daily, encoding='utf-8-sig')['total_asset'].iloc[-1])

    modes = ['commission', 'price'] if args.slippage_mode == 'auto' else [args.slippage_mode]
    results = []
    for mode in modes:
        res = simulate(args, bars, timeline, compat_src, strategy_src, mode)
        ok, gap = compare(res, kh, kh_final, args.period)
        results.append((mode, ok, gap))
        print()
    if len(results) > 1:
        usable = [r for r in results if r[1]]
        with_gap = [r for r in usable if r[2] is not None]
        if with_gap:
            best = min(with_gap, key=lambda r: abs(r[2]))
            print('推荐滑点模式：%s（期末资产和 khQuant 差 %+.2f%%）。把成品 KH_CONFIG 的 slippage_mode 设成它，'
                  'QMT 回测参数按这个模式打印的值填' % (best[0], best[2]))
        elif usable:
            print('推荐滑点模式：%s（没有 daily_stats.csv，无法比期末资产，按默认推荐）' % usable[0][0])
    overall = any(r[1] for r in results)
    print('结论：%s' % ('通过' if overall else '不通过'))
    return 0 if overall else 1


if __name__ == '__main__':
    sys.exit(main())
