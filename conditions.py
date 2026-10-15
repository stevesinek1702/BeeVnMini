"""
Danh mục điều kiện lọc kiểu FireAnt Screener + công thức đánh giá — không dính giao diện / mạng.

Hai loại điều kiện:
  • METRICS — một con số trên mỗi mã (Thay đổi giá 1 tuần, KLTB 20 phiên, KL nước ngoài mua ròng…),
    lọc bằng toán tử > < = ≥ ≤ hoặc "trong khoảng", giống các cột có sẵn của bảng giá.
  • SIGNALS — tín hiệu đúng / sai kèm tham số (giá cắt lên SMA(5), RSI vào vùng quá mua trên 70…).

Công thức chép từ bộ lọc của FireAnt (quote.worker, 10/2026): số thống kê tính ở phiên đã đóng gần nhất
(tech.py) rồi ghép giá hiện tại vào để thấy "hôm nay đã cắt lên / cắt xuống chưa". Giá tính bằng nghìn đồng:
khoảng đệm 0.05 ở EMA / Bollinger là 50đ (một bước giá), y như FireAnt.
"""
import math
import re
from collections import namedtuple

import tech

# ── Nhóm hiển thị (cho bộ chọn điều kiện) ───────────────────────────────
GROUPS = [('price', 'Giá'), ('volume', 'Khối lượng'), ('ma', 'Đường trung bình'),
          ('rsi', 'RSI (14)'), ('mfi', 'MFI (14)'), ('bb', 'Bollinger Band (20)'), ('macd', 'MACD')]

# ── Điều kiện dạng con số ───────────────────────────────────────────────
# (khoá, nhãn đầy đủ, nhãn ngắn trên tiêu đề cột, nhóm, kiểu hiển thị)
METRICS = [
    ('change1w', 'Thay đổi giá 1 tuần (%)', '% 1 tuần', 'price', 'pct'),
    ('change1m', 'Thay đổi giá 1 tháng (%)', '% 1 tháng', 'price', 'pct'),
    ('change3m', 'Thay đổi giá 3 tháng (%)', '% 3 tháng', 'price', 'pct'),
    ('change6m', 'Thay đổi giá 6 tháng (%)', '% 6 tháng', 'price', 'pct'),
    ('change1y', 'Thay đổi giá 1 năm (%)', '% 1 năm', 'price', 'pct'),
    ('upDays', 'Số phiên tăng giá liên tục', 'Phiên tăng', 'price', 'int'),
    ('downDays', 'Số phiên giảm giá liên tục', 'Phiên giảm', 'price', 'int'),
    ('upDaysBeforeDown', 'Số phiên tăng liên tục trước khi đảo chiều giảm', 'Tăng→giảm', 'price', 'int'),
    ('downDaysBeforeUp', 'Số phiên giảm liên tục trước khi đảo chiều tăng', 'Giảm→tăng', 'price', 'int'),
    ('activeBuyPct', '% KL khớp lệnh do bên mua chủ động', '% mua CĐ', 'volume', 'pct0'),
    ('avgVol5', 'KLTB 5 phiên', 'KLTB 5', 'volume', 'vol'),
    ('avgVol10', 'KLTB 10 phiên', 'KLTB 10', 'volume', 'vol'),
    ('avgVol20', 'KLTB 20 phiên', 'KLTB 20', 'volume', 'vol'),
    ('avgVol3m', 'KLTB 3 tháng', 'KLTB 3T', 'volume', 'vol'),
    ('foreignNetVol', 'KL nước ngoài mua ròng', 'KL NN ròng', 'volume', 'svol'),
    ('foreignNetValue', 'GT nước ngoài mua ròng (tỷ)', 'GT NN ròng', 'volume', 'sbil'),
]
METRIC_KEYS = [m[0] for m in METRICS]
METRIC_LABEL = {m[0]: m[1] for m in METRICS}
METRIC_HEAD = {m[0]: m[2] for m in METRICS}
METRIC_GROUP = {m[0]: m[3] for m in METRICS}
METRIC_FMT = {m[0]: m[4] for m in METRICS}
# Cột đứng riêng: khi tính thiếu số (chưa có lịch sử, mã mới…) thì KHÔNG khớp — FireAnt cũng loại những mã đó.

_TECH_PERIOD = {'change1w': '1w', 'change1m': '1m', 'change3m': '3m', 'change6m': '6m', 'change1y': '1y'}
_TECH_AVGVOL = {'avgVol5': 'v5', 'avgVol10': 'v10', 'avgVol20': 'v20', 'avgVol3m': 'v3m'}
# Cột phải có lịch sử nến mới tính được (các cột còn lại lấy thẳng từ quote)
TECH_METRIC_KEYS = (*_TECH_PERIOD, *_TECH_AVGVOL, 'upDays', 'downDays', 'upDaysBeforeDown', 'downDaysBeforeUp')


def quote_metrics(q):
    """Các con số lấy thẳng từ quote FireAnt: % mua chủ động, nước ngoài mua ròng (KL, GT tỷ đồng)."""
    tv = q.get('TotalVolume') or 0
    buy_q, sell_q = q.get('BuyForeignQuantity'), q.get('SellForeignQuantity')
    buy_v, sell_v = q.get('BuyForeignValue'), q.get('SellForeignValue')
    return {
        'activeBuyPct': (q.get('TotalActiveBuyVolume') or 0) * 100 / tv if tv > 0 else None,
        'foreignNetVol': None if buy_q is None and sell_q is None else (buy_q or 0) - (sell_q or 0),
        'foreignNetValue': None if buy_v is None and sell_v is None else ((buy_v or 0) - (sell_v or 0)) / 1e9,
    }


def tech_metrics(st, last, change):
    """Các con số cần lịch sử: thay đổi giá nhiều kỳ, số phiên tăng / giảm liên tục, KLTB.
    st = thống kê tech.stats_from_bars (None nếu chưa có); last = giá hiện tại; change = giá − giá tham chiếu."""
    out = dict.fromkeys(_TECH_PERIOD, None)
    out.update(dict.fromkeys(_TECH_AVGVOL, None))
    out.update(upDays=None, downDays=None, upDaysBeforeDown=None, downDaysBeforeUp=None)
    if not st:
        return out
    if last and last > 0:
        for key, per in _TECH_PERIOD.items():
            px = st.get(f'px{per}')
            if px and px > 0:
                out[key] = (last - px) * 100 / px
    for key, sk in _TECH_AVGVOL.items():
        out[key] = st.get(sk)
    s = st.get('streak')
    if s is not None and change:
        # Phiên hôm nay còn cùng chiều thì cộng thêm 1 (FireAnt: priceChangeConsecutiveDays + 1)
        if change > 0 and s >= 0:
            out['upDays'] = s + 1
        if change < 0 and s <= 0:
            out['downDays'] = -s + 1
        if change < 0 and s > 0:
            out['upDaysBeforeDown'] = s
        if change > 0 and s < 0:
            out['downDaysBeforeUp'] = -s
    return out


# ── Tín hiệu có tham số ─────────────────────────────────────────────────
# choices: danh sách giá trị cho chọn; free=True: ô nhập số tự do (vẫn gợi ý theo choices) trong khoảng lo..hi
Param = namedtuple('Param', 'id name choices default free lo hi')
Signal = namedtuple('Signal', 'id group label params fn')


def _p(pid, name, choices, default, free=False, lo=None, hi=None):
    return Param(pid, name, tuple(choices), default, free, lo, hi)


PERIOD_NAME = {'1w': '1 tuần', '2w': '2 tuần', '1m': '1 tháng', '3m': '3 tháng', '6m': '6 tháng', '1y': '1 năm'}
MA_PERIODS = (5, 10, 15, 20, 45)
P_HIGHLOW = _p('period', 'trong', tuple(PERIOD_NAME), '1y')
P_MA = _p('period', 'kỳ (phiên)', MA_PERIODS, 5)
P_RSI_UP = _p('level', 'ngưỡng quá mua', (60, 65, 70, 75, 80, 85, 90), 70, True, 0, 100)
P_RSI_DOWN = _p('level', 'ngưỡng quá bán', (10, 15, 20, 25, 30, 35, 40), 30, True, 0, 100)
P_MFI_UP = _p('level', 'ngưỡng quá mua', (70, 75, 80, 85, 90), 80, True, 0, 100)
P_MFI_DOWN = _p('level', 'ngưỡng quá bán', (10, 15, 20, 25, 30), 20, True, 0, 100)
P_BB = _p('std', 'độ lệch chuẩn', (2, 3.5), 2, True, 0.5, 6)


def _valid(st, lv):
    return bool(st) and bool(lv) and (lv.get('last') or 0) > 0


# --- Giá vượt đỉnh / thủng đáy -------------------------------------------
def _above_high(st, lv, p):
    hi = st.get('hi' + p['period'])
    return bool(hi) and hi < lv['last']


def _below_low(st, lv, p):
    lo = st.get('lo' + p['period'])
    return bool(lo) and lo > lv['last']


# --- KL dự kiến cả phiên vượt trung bình các phiên trước -------------------
def _est_volume_surge(st, lv, p):
    n = p['period']
    est = lv.get('est')
    prev = st.get(f'v{n - 1}')
    if not est or not prev:
        return False
    avg = (prev * (n - 1) + est) / n        # trung bình n phiên, phiên cuối là phiên dự kiến hôm nay
    return est > (1 + p['pct']) * avg


# --- Giá cắt SMA / EMA; SMA ngắn cắt SMA dài --------------------------------
def _sma_cross(up):
    def fn(st, lv, p):
        n = p['period']
        a, b = st.get(f'p{n}'), st.get(f'p{n - 1}')
        if not a or not b or not st.get('lc'):
            return False
        live = (lv['last'] + (n - 1) * b) / n
        return (st['lc'] <= a and lv['last'] > live) if up else (st['lc'] >= a and lv['last'] < live)
    return fn


def _ema_cross(up):
    def fn(st, lv, p):
        n = p['period']
        e = st.get(f'e{n}')
        if not e or not st.get('lc'):
            return False
        live = (2 * lv['last'] + (n - 1) * e) / (n + 1)
        return (st['lc'] <= e and lv['last'] > live + .05) if up else (st['lc'] >= e and lv['last'] < live - .05)
    return fn


def _sma_pair(up):
    def fn(st, lv, p):
        s, l = p['short'], p['long']
        ps, ps1, pl, pl1 = st.get(f'p{s}'), st.get(f'p{s - 1}'), st.get(f'p{l}'), st.get(f'p{l - 1}')
        if not (ps and ps1 and pl and pl1):
            return False
        live_s = (lv['last'] + (s - 1) * ps1) / s
        live_l = (lv['last'] + (l - 1) * pl1) / l
        return (ps <= pl and live_s > live_l) if up else (ps >= pl and live_s < live_l)
    return fn


# --- RSI(14) --------------------------------------------------------------
def _rsi_of(gain, loss):
    return 100.0 if loss == 0 else 100 - 100 / (1 + gain / loss)


def rsi_now(st, last):
    """(RSI ở phiên đóng gần nhất, RSI nếu giá hiện tại là giá đóng cửa)."""
    ag, al, lc = st.get('ag'), st.get('al'), st.get('lc')
    if ag is None or al is None or lc is None:
        return None, None
    d = last - lc
    return _rsi_of(ag, al), _rsi_of(ag * 13 + max(d, 0), al * 13 + max(-d, 0))


def _rsi(kind):
    def fn(st, lv, p):
        prev, live = rsi_now(st, lv['last'])
        if live is None:
            return False
        a = p['level']
        return {'cross_up': prev <= a < live,         # đi vào vùng quá mua / thoát khỏi vùng quá bán
                'cross_down': prev >= a > live,       # thoát khỏi vùng quá mua / đi vào vùng quá bán
                'above': live > a, 'below': live < a}[kind]
    return fn


# --- MFI(14) --------------------------------------------------------------
def mfi_now(st, lv):
    """(MFI ở phiên đóng gần nhất, MFI tính cả dòng tiền hôm nay). Giá cao / thấp trong ngày thiếu thì lấy giá hiện tại."""
    need = ('lh', 'll', 'lc', 'pmf', 'nmf', 'mfi')
    if any(st.get(k) is None for k in need):
        return None, None
    last = lv['last']
    # Giá điển hình phiên trước tính lại từ cao / thấp / đóng (không lấy số đã làm tròn): giá hôm nay đúng bằng
    # giá điển hình hôm qua thì không có dòng tiền dương cũng không âm — lệch 1e-16 là xếp sai chiều.
    tp_prev = (st['lh'] + st['ll'] + st['lc']) / 3
    tp_now = ((lv.get('high') or last) + (lv.get('low') or last) + last) / 3
    flow = tp_now * (lv.get('volume') or 0)
    pos = st['pmf'] + (flow if tp_now > tp_prev else 0)
    neg = st['nmf'] + (flow if tp_now < tp_prev else 0)
    return st['mfi'], (100.0 if neg == 0 else 100 - 100 / (1 + pos / neg))


def _mfi(kind):
    def fn(st, lv, p):
        prev, live = mfi_now(st, lv)
        if live is None:
            return False
        a = p['level']
        return {'cross_up': live > a and prev < a,
                'cross_down': live < a and prev > a,
                'above': live > a, 'below': live < a}[kind]
    return fn


# --- Bollinger Band (20, k) -----------------------------------------------
def bb_now(st, last, k):
    """((biên trên, biên dưới) ở phiên đóng gần nhất, (biên trên, biên dưới) khi giá hiện tại vào cửa sổ 20 phiên)."""
    p19, p20, s19, s20 = st.get('p19'), st.get('p20'), st.get('sd19'), st.get('sd20')
    if None in (p19, p20, s19, s20):
        return None
    mid = (p19 * 19 + last) / 20
    sd = math.sqrt(19 * (last - p19) ** 2 + 380 * s19 ** 2) / 20     # độ lệch chuẩn tổng thể của 20 giá, có giá hiện tại
    return (p20 + k * s20, p20 - k * s20), (mid + k * sd, mid - k * sd)


def _bb(kind):
    def fn(st, lv, p):
        r = bb_now(st, lv['last'], p['std'])
        lc = st.get('lc')
        if r is None or lc is None:
            return False
        (up0, lo0), (up1, lo1) = r
        last = lv['last']
        return {'cross_above': lc < up0 and last > up1 + .05,        # thoát ra ngoài biên trên
                'back_from_above': lc > up0 and last < up1 - .05,    # cắt xuống từ ngoài biên trên
                'above': last > up1 + .05,
                'cross_below': lc > lo0 and last < lo1 - .05,        # thoát ra ngoài biên dưới
                'back_from_below': lc < lo0 and last > lo1 + .05,    # cắt lên từ ngoài biên dưới
                'below': last < lo1 - .05}[kind]
    return fn


# --- MACD (12, 26, 9) ------------------------------------------------------
def macd_now(st, last):
    """(MACD phiên đóng gần nhất, tín hiệu phiên đóng gần nhất, MACD với giá hiện tại, tín hiệu với giá hiện tại)."""
    e12, e26, sig = st.get('e12'), st.get('e26'), st.get('sig')
    if None in (e12, e26, sig):
        return None
    a12, a26 = 2 / 13, 2 / 27
    live = (a12 * last + (1 - a12) * e12) - (a26 * last + (1 - a26) * e26)
    return e12 - e26, sig, live, .2 * live + .8 * sig


def _macd(kind):
    def fn(st, lv, p):
        r = macd_now(st, lv['last'])
        if r is None:
            return False
        prev, sig, live, live_sig = r
        return {'cross_above_sig': prev < sig and live > live_sig,
                'above_sig': live > live_sig,
                'cross_below_sig': prev > sig and live < live_sig,
                'below_sig': live < live_sig,
                'cross_above_zero': prev < 0 and live > 0,
                'above_zero': live > 0,
                'cross_below_zero': prev > 0 and live < 0,
                'below_zero': live < 0}[kind]
    return fn


def _sig(id_, group, label, params, fn):
    return Signal(id_, group, label, tuple(params), fn)


SIGNAL_LIST = [
    _sig('AbovePreviousHigh', 'price', 'Giá vượt đỉnh {period}', [P_HIGHLOW], _above_high),
    _sig('BelowPreviousLow', 'price', 'Giá thủng đáy {period}', [P_HIGHLOW], _below_low),
    _sig('EstimatedVolumeSurge', 'volume', 'KL dự kiến vượt TB {period} phiên tối thiểu {pct}%',
         [_p('period', 'TB (phiên)', MA_PERIODS, 5), _p('pct', 'vượt tối thiểu (%)', (10, 20, 30, 50, 70, 100, 150, 200, 300),
                                                      50, True, 1, 1000)], _est_volume_surge),
    _sig('PriceCrossAboveSMA', 'ma', 'Giá cắt lên SMA({period})', [P_MA], _sma_cross(True)),
    _sig('PriceCrossBelowSMA', 'ma', 'Giá cắt xuống SMA({period})', [P_MA], _sma_cross(False)),
    _sig('PriceCrossAboveEMA', 'ma', 'Giá cắt lên EMA({period})', [P_MA], _ema_cross(True)),
    _sig('PriceCrossBelowEMA', 'ma', 'Giá cắt xuống EMA({period})', [P_MA], _ema_cross(False)),
    _sig('ShortSMACrossAboveLongSMA', 'ma', 'SMA({short}) cắt lên SMA({long})',
         [_p('short', 'SMA ngắn', (5, 10, 15), 5), _p('long', 'cắt lên SMA dài', (15, 20, 45), 15)], _sma_pair(True)),
    _sig('ShortSMACrossBelowLongSMA', 'ma', 'SMA({short}) cắt xuống SMA({long})',
         [_p('short', 'SMA ngắn', (5, 10, 15), 5), _p('long', 'cắt xuống SMA dài', (15, 20, 45), 15)], _sma_pair(False)),
    _sig('RSICrossAboveOverBoughtLine', 'rsi', 'RSI(14) đi vào vùng quá mua (trên {level})', [P_RSI_UP], _rsi('cross_up')),
    _sig('RSICrossBelowOverBoughtLine', 'rsi', 'RSI(14) thoát khỏi vùng quá mua (trên {level})', [P_RSI_UP], _rsi('cross_down')),
    _sig('RSIAboveOverBoughtLine', 'rsi', 'RSI(14) đang trong vùng quá mua (trên {level})', [P_RSI_UP], _rsi('above')),
    _sig('RSICrossBelowOverSoldLine', 'rsi', 'RSI(14) đi vào vùng quá bán (dưới {level})', [P_RSI_DOWN], _rsi('cross_down')),
    _sig('RSICrossAboveOverSoldLine', 'rsi', 'RSI(14) thoát khỏi vùng quá bán (dưới {level})', [P_RSI_DOWN], _rsi('cross_up')),
    _sig('RSIBelowOverSoldLine', 'rsi', 'RSI(14) đang trong vùng quá bán (dưới {level})', [P_RSI_DOWN], _rsi('below')),
    _sig('MFICrossAboveOverBoughtLine', 'mfi', 'MFI(14) đi vào vùng quá mua (trên {level})', [P_MFI_UP], _mfi('cross_up')),
    _sig('MFICrossBelowOverBoughtLine', 'mfi', 'MFI(14) thoát khỏi vùng quá mua (trên {level})', [P_MFI_UP], _mfi('cross_down')),
    _sig('MFIAboveOverBoughtLine', 'mfi', 'MFI(14) đang trong vùng quá mua (trên {level})', [P_MFI_UP], _mfi('above')),
    _sig('MFICrossBelowOverSoldLine', 'mfi', 'MFI(14) đi vào vùng quá bán (dưới {level})', [P_MFI_DOWN], _mfi('cross_down')),
    _sig('MFICrossAboveOverSoldLine', 'mfi', 'MFI(14) thoát khỏi vùng quá bán (dưới {level})', [P_MFI_DOWN], _mfi('cross_up')),
    _sig('MFIBelowOverSoldLine', 'mfi', 'MFI(14) đang trong vùng quá bán (dưới {level})', [P_MFI_DOWN], _mfi('below')),
    _sig('PriceCrossAboveBollingerBands', 'bb', 'Giá thoát ra ngoài biên trên Bollinger (20, {std})', [P_BB], _bb('cross_above')),
    _sig('PriceCrossFromAboveBollingerBands', 'bb', 'Giá cắt xuống từ ngoài biên trên Bollinger (20, {std})', [P_BB],
         _bb('back_from_above')),
    _sig('PriceAboveBollingerBands', 'bb', 'Giá đang ở ngoài biên trên Bollinger (20, {std})', [P_BB], _bb('above')),
    _sig('PriceCrossBelowBollingerBands', 'bb', 'Giá thoát ra ngoài biên dưới Bollinger (20, {std})', [P_BB], _bb('cross_below')),
    _sig('PriceCrossFromBelowBollingerBands', 'bb', 'Giá cắt lên từ ngoài biên dưới Bollinger (20, {std})', [P_BB],
         _bb('back_from_below')),
    _sig('PriceBelowBollingerBands', 'bb', 'Giá đang ở ngoài biên dưới Bollinger (20, {std})', [P_BB], _bb('below')),
    _sig('MACDCrossAboveSignalLine', 'macd', 'MACD cắt lên đường tín hiệu', [], _macd('cross_above_sig')),
    _sig('MACDAboveSignalLine', 'macd', 'MACD đang ở trên đường tín hiệu', [], _macd('above_sig')),
    _sig('MACDCrossBelowSignalLine', 'macd', 'MACD cắt xuống đường tín hiệu', [], _macd('cross_below_sig')),
    _sig('MACDBelowSignalLine', 'macd', 'MACD đang ở dưới đường tín hiệu', [], _macd('below_sig')),
    _sig('MACDCrossAboveZeroLine', 'macd', 'MACD cắt lên đường 0', [], _macd('cross_above_zero')),
    _sig('MACDAboveZeroLine', 'macd', 'MACD đang ở trên đường 0', [], _macd('above_zero')),
    _sig('MACDCrossBelowZeroLine', 'macd', 'MACD cắt xuống đường 0', [], _macd('cross_below_zero')),
    _sig('MACDBelowZeroLine', 'macd', 'MACD đang ở dưới đường 0', [], _macd('below_zero')),
]
SIGNALS = {s.id: s for s in SIGNAL_LIST}


def normalize_signal(raw):
    """{'id', 'params'} từ cài đặt (có thể cũ / sai) → bản sạch: tham số thiếu lấy mặc định, tham số hỏng
    bị thay bằng mặc định. Trả None nếu không có tín hiệu đó (vd bản sau bỏ bớt)."""
    if not isinstance(raw, dict) or raw.get('id') not in SIGNALS:
        return None
    sig = SIGNALS[raw['id']]
    given = raw.get('params') if isinstance(raw.get('params'), dict) else {}
    params = {}
    for p in sig.params:
        v = given.get(p.id, p.default)
        if p.free:
            try:
                v = float(v)
                v = int(v) if v.is_integer() else v
                ok = p.lo <= v <= p.hi
            except (TypeError, ValueError, OverflowError):
                ok = False
        else:
            ok = v in p.choices
            if ok:
                v = p.choices[p.choices.index(v)]      # 5.0 → 5: khoá thống kê là p5, không phải p5.0
        params[p.id] = v if ok else p.default
    if raw['id'] in ('ShortSMACrossAboveLongSMA', 'ShortSMACrossBelowLongSMA') and params['short'] >= params['long']:
        params['short'], params['long'] = 5, 15      # SMA ngắn phải ngắn hơn SMA dài
    return {'id': sig.id, 'params': params}


def _show(v):
    return str(int(v)) if isinstance(v, float) and v.is_integer() else str(v)


def param_text(value):
    """Giá trị tham số như người dùng thấy: '1w' → '1 tuần', 3.5 → '3.5', 70.0 → '70'."""
    return PERIOD_NAME.get(value, _show(value))


def signal_title(sig):
    """Tên tín hiệu cho bộ chọn: chỗ tham số thay bằng '…', vd 'Giá cắt lên SMA(…)'."""
    return re.sub(r'\{\w+\}', '…', sig.label)


def catalog():
    """{nhóm: [(tên, 'metric' | 'signal', khoá)]} cho bộ chọn điều kiện; trong mỗi nhóm cột số trước, tín hiệu sau."""
    out = {g: [] for g, _ in GROUPS}
    for key, label, _, group, _ in METRICS:
        out[group].append((label, 'metric', key))
    for s in SIGNAL_LIST:
        out[s.group].append((signal_title(s), 'signal', s.id))
    return out


def describe_signal(sig):
    """Câu mô tả 1 tín hiệu, vd 'Giá cắt lên SMA(5)'."""
    s = SIGNALS.get(sig.get('id'))
    if s is None:
        return str(sig.get('id'))
    return s.label.format(**{k: param_text(v) for k, v in (sig.get('params') or {}).items()})


def eval_signal(sig, st, lv):
    """Tín hiệu `sig` có đang đúng với mã có thống kê `st` và giá hiện tại `lv` không.
    lv = {'last', 'high', 'low', 'volume', 'est'} (giá nghìn đồng). Thiếu số → False."""
    s = SIGNALS.get(sig.get('id'))
    if s is None or not _valid(st, lv):
        return False
    params = dict(sig.get('params') or {})
    if 'pct' in params:
        params['pct'] = params['pct'] / 100        # lưu theo % (50), tính theo tỷ lệ (0.5)
    try:
        return bool(s.fn(st, lv, params))
    except (KeyError, TypeError, ZeroDivisionError, ValueError):
        return False
