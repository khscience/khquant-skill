#coding:gbk
# =============================================================================
# khQuant -> 大QMT 内置 Python 回测兼容层（模板）
#
# 用法：把整个文件复制进 QMT「策略编辑器」新建的 Python 模型；
#       只改「一、回测参数」和「三、khQuant 策略代码」两段，其余不动。
#       运行位置选「副图」，在「回测参数」里填好起止时间、初始资金、基准和费用，
#       先在「数据管理」补齐股票池对应周期的历史数据，再点「回测」。
#
# 适用：大QMT 内置 Python 3.6、回测模式（handlebar 逐 K 线）。
#       实盘不要直接用这个兼容层，见 references/live-trading.md。
#
# 本文件以 UTF-8 保存便于阅读；交给用户的成品要另存为 GBK 编码，
# 或让用户直接复制粘贴进 QMT 策略编辑器。
# =============================================================================
import math
import datetime as dt
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import numpy as np
import pandas as pd


# =============================================================================
# 一、回测参数：照搬 khQuant .kh 的取值
# =============================================================================
KH_CONFIG = {
    # 股票池（.kh 的 data.stock_list）
    'stock_list': ['000001.SZ'],
    # 回测区间（.kh 的 backtest.start_time / end_time），init 里会写入 C.start / C.end
    'start_date': '20240101',
    'end_date': '20241231',
    # 初始资金（.kh 的 backtest.init_capital），init 里会写入 C.capital
    'init_capital': 1000000.0,
    # 周期：'1d' / '1m' / '5m'（.kh 的 data.kline_period，要与 QMT 主图周期一致）
    'period': '1d',
    # 复权（.kh 的 data.dividend_type）：none / front / back / front_ratio / back_ratio
    'dividend_type': 'front',
    # 回测账号：任意字符串，查询和下单用同一个
    'account_id': 'kh_backtest',
    # 以下费用只用于「算能买多少股」，QMT 实际扣费以回测参数界面为准
    'commission_rate': 0.0001,
    'min_commission': 5.0,
    'stamp_tax_rate': 0.0005,
    'stamp_tax_mode': '',          # 'a_share_legal'：2023-08-28 前 0.1%，之后 0.05%
    'flow_fee': 0.0,
    'transfer_fee_enabled': True,  # 按 khQuant 口径估算过户费
    # 滑点（.kh 的 backtest.trade_cost.slippage）
    'slippage': {'type': 'ratio', 'ratio': 0.001, 'tick_size': 0.01, 'tick_count': 2},
    # 滑点怎么交给 QMT：
    #   'commission'（默认）：委托价不加滑点（总在当根高低点内），把单边滑点折进 QMT 的佣金率；
    #                         init 会打印 QMT 回测参数该填的佣金率。资金曲线最接近 khQuant。
    #   'price'：按 khQuant 口径把滑点加进委托价；超出当根高低点的只能按端点下单，滑点会被吞掉一部分。
    # 两种模式 QMT 回测参数里的「滑点」都填 0。
    'slippage_mode': 'commission',
    # 模拟 khQuant 的涨跌停拒单（只在不复权时生效，和 khQuant 一致）
    'check_price_limit': True,
    # T+1：None 表示按股票池自动判断（全部在 t0_codes 里才按 T+0）
    't_plus_1': None,
    't0_codes': [],                # 从 khQuant 的 data/T0型ETF.csv（或同目录其他 T0*.csv）复制需要的代码
    # 第一次在 QMT 回测时打印自检信息（账号资金、K 线时间格式、前几笔委托后 QMT 查到的持仓和资金）
    'selfcheck': True,
    # 盘前盘后回调（.kh 的 market_callback），只支持日线周期
    'pre_market_enabled': False,
    'pre_market_time': '08:30:00',
    'post_market_enabled': False,
    'post_market_time': '15:30:00',
    # 日内多次触发（.kh 的 backtest.trigger.daily_trigger_cap），只支持日线周期
    'daily_trigger_cap': 1,
    # 取历史数据时不填充停牌日（False 更接近 khQuant 本地库）
    'fill_data': False,
    # 打印信号和成交明细
    'verbose': True,
}


# =============================================================================
# 二、兼容层（一般不用改）
# =============================================================================
class _PrintLogger(object):
    """QMT 日志面板只显示 print，策略里的 logging.xxx 统一转成 print。"""

    def _out(self, level, msg, *args, **kwargs):
        if args:
            try:
                msg = msg % args
            except Exception:
                msg = '%s %s' % (msg, args)
        print('[%s] %s' % (level, msg))

    def debug(self, msg, *args, **kwargs):
        pass

    def info(self, msg, *args, **kwargs):
        self._out('INFO', msg, *args)

    def warning(self, msg, *args, **kwargs):
        self._out('WARNING', msg, *args)

    warn = warning

    def error(self, msg, *args, **kwargs):
        self._out('ERROR', msg, *args)


logging = _PrintLogger()


class _State(object):
    pass


_S = _State()
_S.C = None
_S.bar14 = ''
_S.trade_date = ''
_S.last_date = ''
_S.prev_day_data = None
_S.pending = []
_S.next_order_id = 1
_S.today_bought = {}
_S.local_account = {}
_S.local_positions = {}
_S.daily_trigger_count = 0
_S.retrigger_requested = False
_S.in_handlebar = False
_S.warned = set()
_S.t0_mode = False
_S.trade_log = []   # (K线时间, 代码, 方向, 股数, 委托价, khQuant 口径成交价)
_S.qmt_cash = 0.0
_S.selfcheck_done = 0
_S.selfcheck_pending = []
_S.selfcheck_env_done = False


def _warn_once(key, msg):
    if key in _S.warned:
        return
    _S.warned.add(key)
    logging.warning(msg)


def _finite_positive(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    if math.isnan(number) or math.isinf(number) or number <= 0:
        return 0.0
    return number


def _to14(value):
    """各种时间表示统一成 YYYYMMDDHHMMSS 字符串。"""
    digits = ''.join(ch for ch in str(value) if ch.isdigit())
    if len(digits) == 13 and digits[0] == '1':  # 毫秒时间戳
        return timetag_to_datetime(int(digits), '%Y%m%d%H%M%S')
    if len(digits) < 8:
        return ''
    return (digits + '000000')[:14]


def _same_bar(t14, bar14):
    if KH_CONFIG['period'] == '1d':
        return t14[:8] == bar14[:8]
    return t14[:12] == bar14[:12]


def _parse_cutoff(value):
    """khHistory 的 current_time 规则：支持 YYYYMMDD、YYYY-MM-DD、带空格的时分秒。"""
    text = str(value).strip()
    if ' ' not in text and len(''.join(ch for ch in text if ch.isdigit())) > 8:
        raise ValueError('current_time 不支持 YYYYMMDDHHMMSS 连写：%s' % value)
    digits = ''.join(ch for ch in text if ch.isdigit())
    if len(digits) < 8:
        raise ValueError('无法解析的时间：%s' % value)
    return (digits + '000000')[:14]


def _is_listed_fund(code):
    """场内基金（ETF/LOF）：沪市 5 开头，深市 15/16/18 开头。"""
    num, _, market = str(code).partition('.')
    market = market.upper()
    if market == 'SH':
        return num.startswith('5')
    if market == 'SZ':
        return num[:2] in ('15', '16', '18')
    return False


def get_price_decimals(data=None, stock_code=None):
    if stock_code and _is_listed_fund(stock_code):
        return 3
    if stock_code:
        return 2
    return 3 if any(_is_listed_fund(c) for c in KH_CONFIG['stock_list']) else 2


def round_price(price, decimals=None, data=None, stock_code=None):
    if decimals is None:
        decimals = get_price_decimals(data, stock_code)
    return round(float(price), decimals)


def _fq_to_qmt(fq):
    mapping = {None: KH_CONFIG['dividend_type'], 'pre': 'front', 'post': 'back', 'none': 'none',
               'front': 'front', 'back': 'back', 'front_ratio': 'front_ratio', 'back_ratio': 'back_ratio'}
    if fq not in mapping:
        raise ValueError('不支持的复权方式：%s' % fq)
    return mapping[fq]


def _load(codes, fields, end14, count, period=None, fq=None):
    C = _S.C
    return C.get_market_data_ex(
        fields, list(codes), period=period or KH_CONFIG['period'],
        end_time=end14, count=count, dividend_type=_fq_to_qmt(fq),
        fill_data=KH_CONFIG['fill_data'], subscribe=False)


# ---------- 交易费用（照 khQuant khTrade.py 的口径） ----------
def _slipped(price, action, code):
    """khQuant 口径的加滑点价格（算股数、记本地账都用它，和滑点模式无关）。"""
    cfg = KH_CONFIG['slippage']
    decimals = get_price_decimals(stock_code=code)
    if cfg.get('type') == 'tick':
        slip = cfg.get('tick_size', 0.01) * cfg.get('tick_count', 0)
        return round(price + slip if action == 'buy' else price - slip, decimals)
    half = cfg.get('ratio', 0.0) / 2.0
    return round(price * (1 + half) if action == 'buy' else price * (1 - half), decimals)


def _slip_ratio(code=None, price=None):
    """单边滑点折成比例。按跳数的滑点要用价格换算，价格不同比例就不同。"""
    cfg = KH_CONFIG['slippage']
    if cfg.get('type') == 'tick':
        if not price:
            return None
        return cfg.get('tick_size', 0.01) * cfg.get('tick_count', 0) / float(price)
    return cfg.get('ratio', 0.0) / 2.0


def qmt_ui_settings(code=None, price=None):
    """QMT 回测参数里费用该填的值（按成交额比例的手续费类型）。"""
    stock_like = [c for c in KH_CONFIG['stock_list'] if not _is_listed_fund(c)]
    is_fund = _is_listed_fund(code) if code else not stock_like
    rate = KH_CONFIG['commission_rate']
    if KH_CONFIG['transfer_fee_enabled'] and not is_fund:
        rate += 0.00001  # 过户费（2022-04-29 之后口径），QMT 没有这一项，折进佣金
    slip = None
    if KH_CONFIG['slippage_mode'] == 'commission':
        slip = _slip_ratio(code, price)
        if slip is not None:
            rate += slip
    stamp = 0.0 if is_fund else KH_CONFIG['stamp_tax_rate']
    return {'commission_rate': rate, 'min_commission': KH_CONFIG['min_commission'], 'stamp_tax_sell': stamp,
            'stamp_tax_buy': 0.0, 'slippage': 0.0, 'slip_ratio_folded': slip}


def _qmt_buy_cost(code, price, volume):
    """按 QMT 回测参数（qmt_ui_settings）估算买入要花的钱。"""
    ui = qmt_ui_settings(code, price)
    amount = price * volume
    rate = ui['commission_rate'] if ui['commission_rate'] is not None else KH_CONFIG['commission_rate']
    return amount + max(amount * rate, ui['min_commission'])


def _pct(x):
    """小数费率换成 QMT 回测参数界面要填的数（界面单位是 %，0.00511 填 0.511）。"""
    return ('%.6f' % (x * 100)).rstrip('0').rstrip('.') or '0'


def _print_ui_settings():
    s = qmt_ui_settings()
    print('[设置] QMT 回测参数（界面单位是 %%，照下面的数填）：滑点类型=按成交额比例，滑点值=0；手续费类型=按成交额比例；'
          '买入印花税=0；卖出印花税=%s；最低佣金=%s 元；最大成交比例=100'
          % (_pct(s['stamp_tax_sell']), s['min_commission']))
    if KH_CONFIG['slippage_mode'] == 'commission' and s['slip_ratio_folded'] is None:
        print('[设置] 滑点按跳数，折进佣金的比例要按价格换算，第一根 K 线会按各股票价格打印佣金')
        return
    print('[设置] 买入佣金=平昨佣金=平今佣金=%s' % _pct(s['commission_rate']))
    if KH_CONFIG['flow_fee']:
        print('[设置] 流量费每笔 %s 元，QMT 没有对应项，金额小可以忽略' % KH_CONFIG['flow_fee'])
    if KH_CONFIG['stamp_tax_mode'] == 'a_share_legal':
        print('[设置] 印花税按日期切换（2023-08-28 前 0.1%），QMT 只能填一个值，跨这一天要分段回测或接受误差')
    if any(_is_listed_fund(c) for c in KH_CONFIG['stock_list']) and any(not _is_listed_fund(c) for c in KH_CONFIG['stock_list']):
        print('[设置] 股票池里同时有股票和 ETF：QMT 只能填一组费率，ETF 不收印花税和过户费，这部分会有差异')


def _transfer_fee(code, price, volume, date8):
    if not KH_CONFIG['transfer_fee_enabled'] or volume <= 0 or _is_listed_fund(code):
        return 0.0
    market = str(code).upper()[-2:]
    amount = price * volume
    d = date8 or '99999999'
    if d >= '20220429':
        return amount * 0.00001
    if market == 'BJ':
        return amount * 0.000025
    if d >= '20150709':
        return amount * 0.00002
    if market == 'SZ':
        return amount * 0.0000255
    return volume * 0.0003


def _trade_cost(price, volume, action, code, date8):
    if volume <= 0:
        return 0.0
    commission = max(price * volume * KH_CONFIG['commission_rate'], KH_CONFIG['min_commission'])
    stamp = 0.0
    if action == 'sell' and not _is_listed_fund(code):
        rate = KH_CONFIG['stamp_tax_rate']
        if KH_CONFIG['stamp_tax_mode'] == 'a_share_legal':
            rate = 0.001 if date8 < '20230828' else 0.0005
        stamp = price * volume * rate
    return commission + stamp + _transfer_fee(code, price, volume, date8) + KH_CONFIG['flow_fee']


# ---------- 涨跌停（照 khQuant khTrade.py 的口径） ----------
def _limit_rate(code):
    prefix = code[:3]
    if prefix in ('688', '689', '300', '301'):
        return 0.20
    if code[:2] in ('43', '83', '87') or code.upper().endswith('.BJ'):
        return 0.30
    return 0.10


def _price_limits(code, bar):
    pre_close = _finite_positive(bar.get('preClose'))
    if pre_close <= 0:
        return None
    rate = _limit_rate(code)
    up = round(pre_close * (1 + rate), 2)
    down = max(round(pre_close * (1 - rate), 2), 0.01)
    high, low = _finite_positive(bar.get('high')), _finite_positive(bar.get('low'))
    if (high > 0 and high > up + 0.011) or (low > 0 and low < down - 0.011):
        return None  # 昨收与行情口径不一致（除权日、新股等），跳过校验
    return up, down


def _limit_reject(code, action, bar, order_price=None):
    """返回拒单原因；空字符串表示可以交易。"""
    if not KH_CONFIG['check_price_limit'] or KH_CONFIG['dividend_type'] != 'none':
        return ''
    limits = _price_limits(code, bar)
    if limits is None:
        return ''
    up, down = limits
    o, h, l, c = (_finite_positive(bar.get(k)) for k in ('open', 'high', 'low', 'close'))
    if action == 'buy' and abs(o - up) < 0.01 and abs(h - up) < 0.01 and abs(l - up) < 0.01:
        return '一字涨停，无法买入'
    if action == 'sell' and abs(o - down) < 0.01 and abs(h - down) < 0.01 and abs(l - down) < 0.01:
        return '一字跌停，无法卖出'
    if action == 'buy' and c >= up - 0.001:
        return '涨停无法买入'
    if action == 'sell' and c <= down + 0.001:
        return '跌停无法卖出'
    if order_price is not None:
        if action == 'buy' and order_price > up + 0.001:
            return '委托价高于涨停价'
        if action == 'sell' and order_price < down - 0.001:
            return '委托价低于跌停价'
    return ''


# ---------- 账户与持仓 ----------
def _read_account():
    acc = get_trade_detail_data(KH_CONFIG['account_id'], 'stock', 'account')
    if not acc:
        _warn_once('no_account', '查不到回测账号 %s 的资金，检查 account_id' % KH_CONFIG['account_id'])
        return {'cash': 0.0, 'total_asset': 0.0, 'market_value': 0.0, 'frozen_cash': 0.0}
    a = acc[0]
    return {'cash': float(a.m_dAvailable), 'total_asset': float(a.m_dBalance),
            'market_value': float(getattr(a, 'm_dInstrumentValue', 0.0)),
            'frozen_cash': float(getattr(a, 'm_dFrozenCash', 0.0))}


def _read_positions():
    result = {}
    for p in get_trade_detail_data(KH_CONFIG['account_id'], 'stock', 'position'):
        code = '%s.%s' % (p.m_strInstrumentID, p.m_strExchangeID)
        volume = int(p.m_nVolume)
        if volume <= 0:
            continue
        can_use = int(getattr(p, 'm_nCanUseVolume', volume))
        if _S.t0_mode:
            can_use = volume
        else:
            can_use = min(can_use, max(0, volume - _S.today_bought.get(code, 0)))
        result[code] = {'volume': volume, 'can_use_volume': can_use,
                        'avg_price': float(getattr(p, 'm_dOpenPrice', 0.0)),
                        'current_price': 0.0,
                        'market_value': float(getattr(p, 'm_dMarketValue', 0.0))}
    return result


# ---------- 当前 K 线 ----------
_BAR_FIELDS = ['open', 'high', 'low', 'close', 'volume', 'amount', 'preClose', 'suspendFlag']


def _current_bars(codes):
    raw = _load(codes, _BAR_FIELDS, _S.bar14, 1)
    bars = {}
    for code in codes:
        df = raw.get(code) if raw else None
        if df is None or len(df) == 0:
            continue
        if not _same_bar(_to14(df.index[-1]), _S.bar14):
            continue  # 当天没有这根 K 线（停牌等）
        row = df.iloc[-1]
        if _finite_positive(row.get('close')) <= 0:
            continue
        bars[code] = row.copy()
    return bars


def _time_info(bar14, time_text=None):
    date_str = '%s-%s-%s' % (bar14[:4], bar14[4:6], bar14[6:8])
    if time_text is None:
        time_text = '09:30:00' if KH_CONFIG['period'] == '1d' else '%s:%s:%s' % (bar14[8:10], bar14[10:12], bar14[12:14])
    dt_obj = datetime.strptime(date_str + ' ' + time_text, '%Y-%m-%d %H:%M:%S')
    return {'date': date_str, 'time': time_text, 'datetime': date_str + ' ' + time_text,
            'timestamp': int(dt_obj.timestamp()), 'raw_time': bar14, '_dt': dt_obj}


def _build_data(bars, time_text=None):
    data = {'__current_time__': _time_info(_S.bar14, time_text),
            '__account__': dict(_S.local_account),
            '__positions__': {k: dict(v) for k, v in _S.local_positions.items()},
            '__stock_list__': list(KH_CONFIG['stock_list']),
            '__framework__': None}
    for code, pos in data['__positions__'].items():
        if code in bars:
            pos['current_price'] = float(bars[code]['close'])
    data.update(bars)
    return data


# =============================================================================
# khQuant 同名函数
# =============================================================================
def khGet(data, key):
    t = data.get('__current_time__', {})
    acc = data.get('__account__', {})
    if key in ('date', 'date_str'):
        return t.get('date', '')
    if key == 'date_num':
        return t.get('date', '').replace('-', '')
    if key in ('time', 'time_str'):
        return t.get('time', '')
    if key in ('datetime', 'datetime_str'):
        return t.get('datetime', '')
    if key == 'datetime_obj':
        return t.get('_dt')
    if key == 'timestamp':
        return t.get('timestamp')
    if key in ('cash', 'market_value', 'total_asset'):
        return float(acc.get(key, 0.0))
    if key == 'stocks':
        return list(data.get('__stock_list__', []))
    if key == 'first_stock':
        stocks = data.get('__stock_list__', [])
        return stocks[0] if stocks else None
    if key == 'positions':
        return {k: dict(v) for k, v in data.get('__positions__', {}).items()}
    return data.get(key)


def khPrice(data, stock_code, field='close'):
    bar = data.get(stock_code)
    if bar is None:
        return 0.0
    try:
        value = bar.get(field)
        if field == 'close' and (value is None or value != value):
            value = bar.get('lastPrice')
        value = float(value)
    except (TypeError, ValueError):
        return 0.0
    return 0.0 if value != value else value


def khHas(data, stock_code):
    pos = data.get('__positions__', {}).get(stock_code)
    return bool(pos and pos.get('volume', 0) > 0)


def khHistory(symbol_list, fields, bar_count, fre_step, current_time=None,
              skip_paused=False, fq=None, force_download=False):
    """取 current_time 之前（不含）的 bar_count 根 K 线，和 khQuant 同口径。"""
    if isinstance(symbol_list, str):
        symbol_list = [symbol_list]
    if not symbol_list or not fields or int(bar_count) <= 0:
        raise ValueError('khHistory 参数错误')
    cutoff = _S.bar14 if current_time is None else _parse_cutoff(current_time)
    want = [f for f in fields if f != 'time']
    raw = _load(symbol_list, want, cutoff, int(bar_count) + 1, period=fre_step, fq=fq)
    result = {}
    for code in symbol_list:
        df = raw.get(code) if raw else None
        if df is None or len(df) == 0:
            result[code] = pd.DataFrame(columns=['time'] + want)
            continue
        times = [_to14(i) for i in df.index]
        if fre_step == '1d':
            keep = [t[:8] < cutoff[:8] for t in times]
        else:
            keep = [t < cutoff for t in times]
        part = df.loc[keep, want].copy()
        part.insert(0, 'time', [t for t, k in zip(times, keep) if k])
        part = part.dropna(subset=[c for c in want if c in ('close', 'open')] or None)
        if skip_paused and 'volume' in part.columns:
            part = part[part['volume'] > 0]
        result[code] = part.tail(int(bar_count)).reset_index(drop=True)
        if len(result[code]) < int(bar_count):
            _warn_once('hist_short_' + code + fre_step,
                       '%s 历史数据不足 %d 根（只有 %d 根），检查 QMT 是否已补数据' % (code, int(bar_count), len(result[code])))
    return result


def khMA(stock_code, period, field='close', fre_step='1d', end_time=None, fq=None, data=None):
    hist = khHistory([stock_code], [field], period, fre_step, current_time=end_time, fq=fq)
    df = hist.get(stock_code)
    if df is None or len(df) < period:
        raise ValueError('%s 数据量不足，无法计算 %d 周期均线' % (stock_code, period))
    return round(float(df[field].astype(float).mean()), get_price_decimals(data, stock_code))


def calculate_max_buy_volume(data, stock_code, price, cash_ratio=1.0):
    cash = float(data.get('__account__', {}).get('cash', 0.0)) * cash_ratio
    if price <= 0:
        return 0
    price = round(price, get_price_decimals(data, stock_code))
    date8 = khGet(data, 'date_num')
    transfer_rate = 0.00001 if not _is_listed_fund(stock_code) else 0.0
    shares = int(math.floor(math.floor(cash / price / (1 + KH_CONFIG['commission_rate'] + transfer_rate)) / 100) * 100)
    while shares >= 100:
        actual = _slipped(price, 'buy', stock_code)
        if actual * shares + _trade_cost(actual, shares, 'buy', stock_code, date8) <= cash:
            return shares
        shares -= 100
    return 0


def generate_signal(data, stock_code, price, ratio, action, reason=''):
    price = round(price, get_price_decimals(data, stock_code))
    ts = data.get('__current_time__', {}).get('timestamp')
    if action == 'buy':
        if ratio > 1:
            target = int(ratio)
            if target % 100 != 0:
                logging.error('买入股数必须是100的整数倍: %s %s' % (stock_code, target))
                return []
            max_volume = calculate_max_buy_volume(data, stock_code, price, 1.0)
            if max_volume == 0:
                return []
            volume = min(target, max_volume)
        else:
            volume = calculate_max_buy_volume(data, stock_code, price, ratio)
            if volume <= 0:
                return []
        return [{'code': stock_code, 'action': 'buy', 'price': price, 'volume': volume,
                 'reason': reason, 'timestamp': ts}]
    if action == 'sell':
        pos = data.get('__positions__', {}).get(stock_code)
        if not pos:
            return []
        available = pos.get('can_use_volume', pos.get('volume', 0))
        volume = int(math.floor(available * ratio / 100) * 100)
        if volume <= 0:
            return []
        return [{'code': stock_code, 'action': 'sell', 'price': price, 'volume': volume,
                 'reason': reason, 'timestamp': ts}]
    return []


def khRequestNextDailyTrigger():
    if KH_CONFIG['period'] != '1d' or not _S.in_handlebar:
        return False
    if _S.daily_trigger_count >= KH_CONFIG['daily_trigger_cap']:
        return False
    _S.retrigger_requested = True
    return True


def khGetPendingOrders(data=None, code=None):
    return [dict(o) for o in _S.pending if code is None or o['code'] == code]


def khGetPendingSummary(data=None):
    buys = [o for o in _S.pending if o['action'] == 'buy']
    sells = [o for o in _S.pending if o['action'] == 'sell']
    return {'total_count': len(_S.pending), 'buy_count': len(buys), 'sell_count': len(sells),
            'total_buy_volume': sum(o['remaining_volume'] for o in buys),
            'total_sell_volume': sum(o['remaining_volume'] for o in sells)}


def khCancelOrder(data, order_id):
    for o in list(_S.pending):
        if o['order_id'] == order_id:
            _S.pending.remove(o)
            return True
    return False


def khCancelOrdersByCode(data, code):
    before = len(_S.pending)
    _S.pending = [o for o in _S.pending if o['code'] != code]
    return before - len(_S.pending)


def khCancelAllOrders(data=None):
    count = len(_S.pending)
    _S.pending = []
    return count


def khIsMatchEngineEnabled(data=None):
    return True


# =============================================================================
# 撮合（照 khQuant 规则算出成交价，再用 QMT 指定价下单）
# =============================================================================
def _match_price(order, bar):
    """返回成交基准价（未加滑点）；None 表示本根不成交。"""
    o, h, l = (_finite_positive(bar.get(k)) for k in ('open', 'high', 'low'))
    if o <= 0 or h <= 0 or l <= 0:
        return None
    action, kind, price = order['action'], order['order_type'], float(order['price'])
    if kind in ('stop', 'stop_limit') and not order.get('triggered'):
        stop = float(order['stop_price'])
        hit = h >= stop if action == 'buy' else l <= stop
        if not hit:
            return None
        order['triggered'] = True
        if kind == 'stop':
            fill = max(stop, o) if action == 'buy' else min(stop, o)
            return min(max(fill, l), h)
        kind = 'limit'
    if kind == 'limit' or kind == 'stop_limit':
        if action == 'buy':
            return (o if o <= price else price) if l <= price else None
        return (o if o >= price else price) if h >= price else None
    # 市价单：按信号价；买价高于最高、卖价低于最低时改按开盘价。
    # 和 khQuant（khFrame._clamp_market_price_to_bar）一样，先把高低点按价格精度取整再比较：
    # 前复权价常有三位小数（如最高 9.218），信号价 9.22 不算越界。
    decimals = get_price_decimals(stock_code=order['code'])
    if action == 'buy' and price > round(h, decimals) + 1e-9:
        return round(o, decimals)
    if action == 'sell' and price < round(l, decimals) - 1e-9:
        return round(o, decimals)
    return price


def _execute(order, bar, data, date8):
    """按 khQuant 口径检查后，用 QMT 指定价下单，并更新本地账户副本。返回是否成交。"""
    code, action, volume = order['code'], order['action'], int(order['remaining_volume'])
    reject = _limit_reject(code, action, bar,
                           float(order['price']) if order['order_type'] in ('limit', 'stop_limit') else None)
    if reject:
        if order['order_type'] in ('limit', 'stop_limit') and reject.startswith('委托价'):
            order['remaining_volume'] = 0
        logging.warning('拒单 %s %s %d股：%s' % (code, action, volume, reject))
        return False
    base = _match_price(order, bar)
    if base is None:
        return False
    decimals = get_price_decimals(stock_code=code)
    # fill：khQuant 口径的成交价（含滑点），用来记本地账、算资金
    fill = _slipped(base, action, code)
    if order['order_type'] in ('limit', 'stop_limit'):
        fill = min(fill, float(order['price'])) if action == 'buy' else max(fill, float(order['price']))
    fill = round(fill, decimals)
    # order_price：真正发给 QMT 的委托价。commission 模式不加滑点，滑点在 QMT 佣金率里收
    order_price = fill if KH_CONFIG['slippage_mode'] == 'price' else round(base, decimals)
    low, high = _finite_positive(bar.get('low')), _finite_positive(bar.get('high'))
    if order_price < low - 1e-9 or order_price > high + 1e-9:  # 容差：行情价可能带浮点尾数（如 1.7510000000000001）
        # QMT 回测里指定价超出当根高低点会改按收盘价成交，只能按端点下单。
        # 用区间端点原值（复权价可能有三位小数，不再取整，否则又会掉出区间）。
        _warn_once('clip_' + code, '%s 委托价 %.3f 超出当根 [%.3f, %.3f]，已按端点下单（khQuant 允许越界，会有小差异）'
                   % (code, order_price, low, high))
        order_price = low if order_price < low else high
    cost = _trade_cost(fill, volume, action, code, date8)
    acc, positions = _S.local_account, _S.local_positions
    if action == 'buy':
        if fill * volume + cost > acc.get('cash', 0.0) + 1e-6:
            logging.warning('拒单 %s 买入 %d股：资金不足' % (code, volume))
            order['remaining_volume'] = 0
            return False
        # 再按 QMT 实际收费口径（委托价 + 回测参数里的佣金率）核一遍资金，
        # 避免 QMT 因差几十元拒单、而兼容层以为已经买进
        while volume >= 100 and _qmt_buy_cost(code, order_price, volume) > _S.qmt_cash + 1e-6:
            volume -= 100
        if volume < int(order['remaining_volume']):
            _warn_once('qmt_cash_' + code, '%s 按 QMT 收费口径资金不够，买入数量从 %d 减到 %d 股（khQuant 口径够用，会有小差异）'
                       % (code, int(order['remaining_volume']), volume))
            if volume < 100:
                order['remaining_volume'] = 0
                return False
            cost = _trade_cost(fill, volume, action, code, date8)
        passorder(23, 1101, KH_CONFIG['account_id'], code, 11, order_price, volume, _S.C)
        _S.qmt_cash -= _qmt_buy_cost(code, order_price, volume)
        acc['cash'] = acc.get('cash', 0.0) - fill * volume - cost
        pos = positions.setdefault(code, {'volume': 0, 'can_use_volume': 0, 'avg_price': 0.0,
                                          'current_price': fill, 'market_value': 0.0})
        total = pos['volume'] + volume
        pos['avg_price'] = (pos['avg_price'] * pos['volume'] + fill * volume) / total
        pos['volume'] = total
        if _S.t0_mode:
            pos['can_use_volume'] += volume
        _S.today_bought[code] = _S.today_bought.get(code, 0) + volume
    else:
        pos = positions.get(code)
        if not pos or pos.get('can_use_volume', 0) < volume:
            logging.warning('拒单 %s 卖出 %d股：可用持仓不足' % (code, volume))
            order['remaining_volume'] = 0
            return False
        passorder(24, 1101, KH_CONFIG['account_id'], code, 11, order_price, volume, _S.C)
        ui = qmt_ui_settings(code, order_price)
        amount = order_price * volume
        _S.qmt_cash += amount - max(amount * ui['commission_rate'], ui['min_commission']) - amount * ui['stamp_tax_sell']
        acc['cash'] = acc.get('cash', 0.0) + fill * volume - cost
        pos['volume'] -= volume
        pos['can_use_volume'] -= volume
        if pos['volume'] <= 0:
            positions.pop(code, None)
    order['remaining_volume'] = 0
    _S.trade_log.append((_S.bar14, code, action, volume, order_price, fill))
    if KH_CONFIG['verbose']:
        print('[TRADE] %s %s %s %d股 委托价%s khQuant口径成交价%s 原因:%s'
              % (_S.bar14, code, '买入' if action == 'buy' else '卖出', volume, order_price, fill,
                 order.get('reason', '')))
    _selfcheck_record(code, action, volume, order_price, fill)
    return True


# ---------- 自检：第一次在 QMT 回测时核对环境 ----------
_SELFCHECK_MAX_ORDERS = 3


def _selfcheck_record(code, action, volume, order_price, fill):
    if not KH_CONFIG['selfcheck'] or _S.selfcheck_done >= _SELFCHECK_MAX_ORDERS:
        return
    _S.selfcheck_done += 1
    s = qmt_ui_settings(code, order_price)
    print('[自检] 第 %d 笔委托 %s %s %s %d股 委托价 %s；khQuant 口径成交价 %s；按设置 QMT 佣金 %s%%'
          % (_S.selfcheck_done, _S.bar14, code, '买入' if action == 'buy' else '卖出', volume, order_price, fill,
             _pct(s['commission_rate'])))
    _S.selfcheck_pending.append({'code': code, 'action': action, 'volume': volume, 'bar14': _S.bar14})


def _selfcheck_bar(C, expect_cash):
    """每根 K 线开头调用：打印环境信息，并核对上一根下的委托在 QMT 里的结果。
    expect_cash：上一根 K 线结束时，兼容层按 QMT 收费口径推算的资金（含那根 K 线的全部成交）。"""
    if not KH_CONFIG['selfcheck']:
        return
    if not _S.selfcheck_env_done:
        _S.selfcheck_env_done = True
        acc = get_trade_detail_data(KH_CONFIG['account_id'], 'stock', 'account')
        print('[自检] 第一根 K 线 %s；主图周期 %s；回测账号 %s 查到资金 %s' % (
            _S.bar14, getattr(C, 'period', '?'), KH_CONFIG['account_id'],
            ('%.2f' % acc[0].m_dAvailable) if acc else '查不到（检查 account_id，回测里查询和下单要用同一个字符串）'))
        raw = _load(KH_CONFIG['stock_list'][:1], ['close'], _S.bar14, 2)
        df = raw.get(KH_CONFIG['stock_list'][0]) if raw else None
        if df is not None and len(df):
            print('[自检] get_market_data_ex 行索引样例 %r，最后一行收盘价 %s' % (df.index[-1], df['close'].iloc[-1]))
        else:
            print('[自检] %s 在这根 K 线取不到数据，检查是否已补数据' % KH_CONFIG['stock_list'][0])
        if KH_CONFIG['slippage_mode'] == 'commission' and KH_CONFIG['slippage'].get('type') == 'tick' and df is not None and len(df):
            for code in KH_CONFIG['stock_list'][:10]:
                one = _load([code], ['close'], _S.bar14, 1).get(code)
                if one is not None and len(one):
                    s = qmt_ui_settings(code, float(one['close'].iloc[-1]))
                    print('[设置] %s 按当前价 %.3f 折算，买入佣金=平昨佣金=平今佣金约 %s'
                          % (code, float(one['close'].iloc[-1]), _pct(s['commission_rate'])))
    if not _S.selfcheck_pending or _S.selfcheck_pending[0]['bar14'] == _S.bar14:
        return
    acc = get_trade_detail_data(KH_CONFIG['account_id'], 'stock', 'account')
    held = {}
    for p in get_trade_detail_data(KH_CONFIG['account_id'], 'stock', 'position'):
        held['%s.%s' % (p.m_strInstrumentID, p.m_strExchangeID)] = p
    for item in _S.selfcheck_pending:
        p = held.get(item['code'])
        same_day = item['bar14'][:8] == _S.bar14[:8]
        print('[自检] %s 下的 %s %s %d股，到 %s 时 QMT 持仓 %s 股、可卖 %s 股%s' % (
            item['bar14'], item['code'], '买入' if item['action'] == 'buy' else '卖出', item['volume'], _S.bar14,
            getattr(p, 'm_nVolume', 0), getattr(p, 'm_nCanUseVolume', 0),
            '（同一天：T+0 品种可卖应包含刚买的部分）' if same_day and item['action'] == 'buy' else ''))
    order_bar = _S.selfcheck_pending[0]['bar14']
    n = sum(1 for t in _S.trade_log if t[0] == order_bar)
    print('[自检] 到 %s 时 QMT 查到资金 %s；兼容层按 QMT 收费推算 %.2f（含 %s 那根 K 线的全部 %d 笔成交，'
          '两者应只差几分钱，差得多说明回测参数没填对）' % (
              _S.bar14, ('%.2f' % acc[0].m_dAvailable) if acc else '查不到', expect_cash, order_bar, n))
    _S.selfcheck_pending = []


def _new_order(signal, default_type, default_tif, create_date, expire_date=None):
    order = {
        'order_id': 'KH%06d' % _S.next_order_id,
        'code': signal['code'], 'action': signal['action'],
        'price': float(signal['price']), 'volume': int(signal['volume']),
        'remaining_volume': int(signal['volume']),
        'order_type': signal.get('order_type', default_type),
        'stop_price': signal.get('stop_price'),
        'time_in_force': signal.get('time_in_force', default_tif),
        'expire_date': signal.get('expire_date', expire_date),
        'max_pending_bars': int(signal.get('max_pending_bars') or 0),
        'bars_waited': 0, 'create_date': create_date, 'triggered': False,
        'reason': signal.get('reason', ''),
    }
    _S.next_order_id += 1
    return order


def _process_signals(signals, data, bars, default_type='market', default_tif='day', queue_only=False,
                     expire_date=None):
    if not signals:
        return
    if not isinstance(signals, list):
        logging.error('回调必须返回信号列表，收到 %s' % type(signals))
        return
    date8 = khGet(data, 'date_num')
    for signal in signals:
        if not isinstance(signal, dict):
            logging.error('信号必须是字典（多股票循环里要用 extend）：%s' % (signal,))
            continue
        if int(signal.get('volume', 0)) <= 0:
            continue
        order = _new_order(signal, default_type, default_tif, khGet(data, 'date'), expire_date)
        if order['order_type'] in ('stop', 'stop_limit') and order['stop_price'] is None:
            logging.error('止损单缺少 stop_price：%s' % (signal,))
            continue
        bar = bars.get(order['code'])
        if not queue_only and bar is not None:
            _execute(order, bar, data, date8)
        if order['remaining_volume'] > 0:
            if order['order_type'] == 'market':
                if bar is None:
                    logging.warning('%s 当前没有行情，市价单作废' % order['code'])
                continue
            _S.pending.append(order)


def _match_pending(bars, data):
    date8 = khGet(data, 'date_num')
    for order in list(_S.pending):
        bar = bars.get(order['code'])
        if bar is not None:
            _execute(order, bar, data, date8)
            order['bars_waited'] += 1
        if order['remaining_volume'] <= 0:
            _S.pending.remove(order)
        elif order['max_pending_bars'] and order['bars_waited'] >= order['max_pending_bars']:
            _S.pending.remove(order)


def _expire_orders(today_dash):
    keep = []
    for o in _S.pending:
        if o['time_in_force'] == 'day' and o['create_date'] < today_dash:
            continue
        if o['time_in_force'] == 'gtd' and o.get('expire_date') and o['expire_date'] < today_dash:
            continue
        keep.append(o)
    _S.pending = keep


def _call(name, *args):
    func = globals().get(name)
    if func is None:
        return None
    return func(*args)


# =============================================================================
# 三、khQuant 策略代码：原样贴在这里，再按 SKILL.md 的清单改
#     - init(stock_codes, init_data) 改名为 kh_init(stock_codes, init_data)
#     - 删掉 from khQuantImport import *
#     - 用到的 MyTT 指标函数从 khQuant 的 MyTT.py 复制进来
# =============================================================================
def kh_init(stock_codes, init_data):
    pass


def khHandlebar(data):
    return []


# def khPreMarket(data):
#     return []


# def khPostMarket(data):
#     return []


# =============================================================================
# 四、QMT 入口（一般不用改）
# =============================================================================
def init(C):
    _S.C = C
    C.start = '%s-%s-%s 00:00:00' % (KH_CONFIG['start_date'][:4], KH_CONFIG['start_date'][4:6], KH_CONFIG['start_date'][6:8])
    C.end = '%s-%s-%s 23:59:59' % (KH_CONFIG['end_date'][:4], KH_CONFIG['end_date'][4:6], KH_CONFIG['end_date'][6:8])
    C.capital = KH_CONFIG['init_capital']
    if KH_CONFIG['t_plus_1'] is None:
        pool = set(KH_CONFIG['stock_list'])
        _S.t0_mode = bool(pool) and pool.issubset(set(KH_CONFIG['t0_codes']))
    else:
        _S.t0_mode = not KH_CONFIG['t_plus_1']
    if C.period != KH_CONFIG['period']:
        print('[WARNING] QMT 主图周期 %s 与 KH_CONFIG period %s 不一致，handlebar 按主图周期触发' % (C.period, KH_CONFIG['period']))
    if (KH_CONFIG['pre_market_enabled'] or KH_CONFIG['post_market_enabled'] or KH_CONFIG['daily_trigger_cap'] > 1) \
            and KH_CONFIG['period'] != '1d':
        print('[WARNING] 盘前盘后回调和日内多次触发在兼容层里只支持日线周期')
    _print_ui_settings()
    init_data = {'__account__': {'cash': KH_CONFIG['init_capital'], 'total_asset': KH_CONFIG['init_capital'],
                                 'market_value': 0.0},
                 '__positions__': {}, '__stock_list__': list(KH_CONFIG['stock_list']),
                 '__framework__': None, '__current_time__': {}}
    kh_init(list(KH_CONFIG['stock_list']), init_data)


def handlebar(C):
    _S.C = C
    _S.bar14 = timetag_to_datetime(C.get_bar_timetag(C.barpos), '%Y%m%d%H%M%S')
    date8 = _S.bar14[:8]
    if date8 < KH_CONFIG['start_date'] or date8 > KH_CONFIG['end_date']:
        return
    is_daily = KH_CONFIG['period'] == '1d'
    new_day = date8 != _S.last_date
    if new_day:
        # 新的一天：昨天买入的部分今天可卖；再用 QMT 账户刷新本地副本（上一交易日收盘后的状态）
        _S.today_bought = {}
        _S.local_account = _read_account()
        _S.local_positions = _read_positions()
        if _S.last_date and is_daily and KH_CONFIG['post_market_enabled'] and _S.prev_day_data is not None:
            prev = _S.prev_day_data
            prev['__account__'] = dict(_S.local_account)
            prev['__positions__'] = {k: dict(v) for k, v in _S.local_positions.items()}
            post_t = KH_CONFIG['post_market_time']
            prev['__current_time__'] = _time_info(_S.last_date + '000000', post_t)
            today14 = _S.bar14
            _S.bar14 = _S.last_date + post_t.replace(':', '')  # 回调里 khHistory 默认截止到盘后那一刻
            try:
                post = _call('khPostMarket', prev)
            finally:
                _S.bar14 = today14
            # 盘后信号：限价挂单，有效到下一个交易日（即今天）收盘
            today_dash = '%s-%s-%s' % (date8[:4], date8[4:6], date8[6:8])
            _process_signals(post, prev, {}, default_type='limit', default_tif='gtd', queue_only=True,
                             expire_date=today_dash)
        _expire_orders('%s-%s-%s' % (date8[:4], date8[4:6], date8[6:8]))
        _S.daily_trigger_count = 0
        _S.last_date = date8
        if is_daily and KH_CONFIG['pre_market_enabled']:
            pre = dict(_S.prev_day_data) if _S.prev_day_data is not None else {}
            pre['__account__'] = dict(_S.local_account)
            pre['__positions__'] = {k: dict(v) for k, v in _S.local_positions.items()}
            pre['__stock_list__'] = list(KH_CONFIG['stock_list'])
            pre['__current_time__'] = _time_info(_S.bar14, KH_CONFIG['pre_market_time'])
            _process_signals(_call('khPreMarket', pre), pre, {}, default_type='limit', default_tif='day',
                             queue_only=True)
    else:
        _S.local_account = _read_account()
        _S.local_positions = _read_positions()

    prev_qmt_cash = _S.qmt_cash  # 上一根 K 线结束时按 QMT 收费口径推算的资金，给自检核对
    _S.qmt_cash = _S.local_account.get('cash', 0.0)  # QMT 账户可用资金，下单时按 QMT 收费口径扣减
    _selfcheck_bar(C, prev_qmt_cash)
    bars = _current_bars(KH_CONFIG['stock_list'])
    data = _build_data(bars)
    _match_pending(bars, data)
    if not bars:
        print('[WARNING] %s 股票池全部没有行情，跳过本次 khHandlebar' % _S.bar14)
        return
    while True:
        data = _build_data(bars)
        _S.in_handlebar = True
        _S.retrigger_requested = False
        _S.daily_trigger_count += 1
        try:
            signals = khHandlebar(data)
        finally:
            _S.in_handlebar = False
        _process_signals(signals, data, bars)
        if not (is_daily and _S.retrigger_requested and _S.daily_trigger_count < KH_CONFIG['daily_trigger_cap']):
            break
    _S.prev_day_data = _build_data(bars)
