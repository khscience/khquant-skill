# 迁移自 khQuant 内置案例【1-MA策略案例】双均线精简_使用khMA函数（参数固定为 5/20）
# 改动：删掉 from khQuantImport import *；init 改名 kh_init；参数改为固定值
params = {
    'ma_short': 5,
    'ma_long': 20,
}


def kh_init(stocks=None, data=None):
    logging.info(f"=== 双均线策略启动 ===")
    logging.info(f"参数: 短期均线={params['ma_short']}日, 长期均线={params['ma_long']}日")


def khHandlebar(data: Dict) -> List[Dict]:
    signals = []
    stock_code = khGet(data, "first_stock")
    current_price = khPrice(data, stock_code, "open")
    current_date_str = khGet(data, "date_num")

    ma_s = params['ma_short']
    ma_l = params['ma_long']

    try:
        ma_short = khMA(stock_code, ma_s, end_time=current_date_str)
        ma_long = khMA(stock_code, ma_l, end_time=current_date_str)
    except ValueError:
        return signals

    has_position = khHas(data, stock_code)

    if ma_short > ma_long and not has_position:
        signals = generate_signal(data, stock_code, current_price, 1.0, 'buy', f"{ma_s}日线({ma_short:.2f}) 上穿 {ma_l}日线({ma_long:.2f})，全仓买入")
    elif ma_short < ma_long and has_position:
        signals = generate_signal(data, stock_code, current_price, 1.0, 'sell', f"{ma_s}日线({ma_short:.2f}) 下穿 {ma_l}日线({ma_long:.2f})，全仓卖出")

    return signals
