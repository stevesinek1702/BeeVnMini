"""
Danh mục điều kiện lọc kiểu FireAnt Screener + công thức đánh giá — không dính giao diện / mạng.

Hai loại điều kiện:
  • METRICS — một con số trên mỗi mã (Thay đổi giá 1 tuần, KLTB 20 phiên, KL nước ngoài mua ròng…),
    lọc bằng toán tử > < = ≥ ≤ hoặc "trong khoảng", giống các cột có sẵn của bảng giá.
  • SIGNALS — tín hiệu đúng / sai kèm tham số (giá cắt lên SMA(5), RSI vào vùng quá mua trên 70…).

Công thức chép từ bộ lọc của FireAnt (quote.worker, 10/2026): số thống kê tính ở phiên đã đóng gần nhất
(tech.py) rồi ghép giá hiện tại vào để thấy "hôm nay đã cắt lên / cắt xuống chưa". Giá tính bằng nghìn đồng:
khoảng đệm 0.05 ở EMA / Bollinger là 50đ (một bước giá), y như FireAnt.
Tín hiệu có tham số 'tf' (khung) = '15m' thì tính trên nến 15 phút đã chốt (lv['intra']['15m']) thay cho nến ngày.
"""
import math
import re
from collections import namedtuple

import tech

# ── Nhóm hiển thị (cho bộ chọn điều kiện) ───────────────────────────────
GROUPS = [('price', 'Giá'), ('volume', 'Khối lượng & dòng tiền'), ('ma', 'Đường trung bình'),
          ('rsi', 'RSI (14)'), ('mfi', 'MFI (14)'), ('stoch', 'Stochastic (14, 3, 3)'), ('osc', 'Williams %R & CCI'),
          ('bb', 'Bollinger Band (20)'), ('macd', 'MACD'), ('adx', 'ADX / DMI (14)'), ('sar', 'Parabolic SAR'),
          ('ichimoku', 'Ichimoku (9, 26, 52)'), ('pullback', 'Pullback & trendline')]

# ── Điều kiện dạng con số ───────────────────────────────────────────────
# (khoá, nhãn đầy đủ, nhãn ngắn trên tiêu đề cột, nhóm, kiểu hiển thị)
METRICS = [
    ('change1w', 'Thay đổi giá 1 tuần (%)', '% 1 tuần', 'price', 'pct'),
    ('change1m', 'Thay đổi giá 1 tháng (%)', '% 1 tháng', 'price', 'pct'),
    ('change3m', 'Thay đổi giá 3 tháng (%)', '% 3 tháng', 'price', 'pct'),
    ('change6m', 'Thay đổi giá 6 tháng (%)', '% 6 tháng', 'price', 'pct'),
    ('change1y', 'Thay đổi giá 1 năm (%)', '% 1 năm', 'price', 'pct'),
    ('fromHigh1m', 'Giá cách đỉnh 1 tháng (%)', '↓ đỉnh 1T', 'price', 'upct'),
    ('fromHigh3m', 'Giá cách đỉnh 3 tháng (%)', '↓ đỉnh 3T', 'price', 'upct'),
    ('fromHigh6m', 'Giá cách đỉnh 6 tháng (%)', '↓ đỉnh 6T', 'price', 'upct'),
    ('fromHigh1y', 'Giá cách đỉnh 1 năm (%)', '↓ đỉnh 1N', 'price', 'upct'),
    ('fromLow1m', 'Giá cách đáy 1 tháng (%)', '↑ đáy 1T', 'price', 'upct'),
    ('fromLow3m', 'Giá cách đáy 3 tháng (%)', '↑ đáy 3T', 'price', 'upct'),
    ('fromLow6m', 'Giá cách đáy 6 tháng (%)', '↑ đáy 6T', 'price', 'upct'),
    ('fromLow1y', 'Giá cách đáy 1 năm (%)', '↑ đáy 1N', 'price', 'upct'),
    ('upDays', 'Số phiên tăng giá liên tục', 'Phiên tăng', 'price', 'int'),
    ('downDays', 'Số phiên giảm giá liên tục', 'Phiên giảm', 'price', 'int'),
    ('upDaysBeforeDown', 'Số phiên tăng liên tục trước khi đảo chiều giảm', 'Tăng→giảm', 'price', 'int'),
    ('downDaysBeforeUp', 'Số phiên giảm liên tục trước khi đảo chiều tăng', 'Giảm→tăng', 'price', 'int'),
    ('activeBuyPct', '% KL khớp lệnh do bên mua chủ động', '% mua CĐ', 'volume', 'pct0'),
    ('avgVol5', 'KLTB 5 phiên', 'KLTB 5', 'volume', 'vol'),
    ('avgVol10', 'KLTB 10 phiên', 'KLTB 10', 'volume', 'vol'),
    ('avgVol20', 'KLTB 20 phiên', 'KLTB 20', 'volume', 'vol'),
    ('avgVol50', 'KLTB 50 phiên', 'KLTB 50', 'volume', 'vol'),
    ('avgVol100', 'KLTB 100 phiên', 'KLTB 100', 'volume', 'vol'),
    ('avgVol3m', 'KLTB 3 tháng', 'KLTB 3T', 'volume', 'vol'),
    ('avgValue20', 'GTTB 20 phiên (tỷ đồng)', 'GTTB 20', 'volume', 'bil'),
    ('volVs20', 'KL dự kiến hôm nay so với KLTB 20 phiên (%)', 'KL/TB20', 'volume', 'ratio'),
    ('volVs50', 'KL dự kiến hôm nay so với KLTB 50 phiên (%)', 'KL/TB50', 'volume', 'ratio'),
    ('foreignNetVol', 'KL nước ngoài mua ròng', 'KL NN ròng', 'volume', 'svol'),
    ('foreignNetValue', 'GT nước ngoài mua ròng (tỷ)', 'GT NN ròng', 'volume', 'sbil'),
    ('rsi14', 'RSI(14) hiện tại', 'RSI', 'rsi', 'num'),
    ('mfi14', 'MFI(14) hiện tại', 'MFI', 'mfi', 'num'),
    ('stochK', 'Stochastic %K (14, 3, 3)', '%K', 'stoch', 'num'),
    ('willR', 'Williams %R (14)', '%R', 'osc', 'num'),
    ('cci20', 'CCI (20)', 'CCI', 'osc', 'num'),
    ('bbWidth', 'Độ rộng dải Bollinger (20, 2) (% so với đường giữa)', 'BB rộng', 'bb', 'upct'),
    ('adx14', 'ADX (14)', 'ADX', 'adx', 'num'),
    ('atrPct', 'Biên độ ATR (14) so với giá (%)', 'ATR %', 'adx', 'upct'),
    ('distSMA20', 'Khoảng cách giá tới SMA20 (%)', '↕SMA20', 'pullback', 'pct'),
    ('distSMA50', 'Khoảng cách giá tới SMA50 (%)', '↕SMA50', 'pullback', 'pct'),
    ('brkTL3m', 'Vượt trendline giảm 3 tháng cách đây (phiên)', 'Vượt TL 3T', 'pullback', 'ago'),
    ('brkTL3mPx', 'Giá vượt trendline giảm 3 tháng (giá đóng cửa phiên vượt)', 'Giá vượt 3T', 'pullback', 'price'),
    ('brkTL3mPct', '% giá hiện tại so với giá vượt trendline giảm 3 tháng', '% từ vượt 3T', 'pullback', 'pct'),
    ('brkTL6m', 'Vượt trendline giảm 6 tháng cách đây (phiên)', 'Vượt TL 6T', 'pullback', 'ago'),
    ('brkTL6mPx', 'Giá vượt trendline giảm 6 tháng (giá đóng cửa phiên vượt)', 'Giá vượt 6T', 'pullback', 'price'),
    ('brkTL6mPct', '% giá hiện tại so với giá vượt trendline giảm 6 tháng', '% từ vượt 6T', 'pullback', 'pct'),
]
METRIC_KEYS = [m[0] for m in METRICS]
METRIC_LABEL = {m[0]: m[1] for m in METRICS}
METRIC_HEAD = {m[0]: m[2] for m in METRICS}
METRIC_GROUP = {m[0]: m[3] for m in METRICS}
METRIC_FMT = {m[0]: m[4] for m in METRICS}
# Cột đứng riêng: khi tính thiếu số (chưa có lịch sử, mã mới…) thì KHÔNG khớp — FireAnt cũng loại những mã đó.

_TECH_PERIOD = {'change1w': '1w', 'change1m': '1m', 'change3m': '3m', 'change6m': '6m', 'change1y': '1y'}
_TECH_AVGVOL = {'avgVol5': 'v5', 'avgVol10': 'v10', 'avgVol20': 'v20', 'avgVol50': 'v50', 'avgVol100': 'v100',
                'avgVol3m': 'v3m', 'avgValue20': 'gv20'}
_TECH_DIST = {'distSMA20': 20, 'distSMA50': 50}
_TECH_VOLVS = {'volVs20': 'v20', 'volVs50': 'v50'}      # KL dự kiến cả phiên hôm nay / KLTB n phiên đã đóng × 100
# Phiên vượt trendline giảm gần nhất (0 = hôm nay): cần quét lùi tech.last_break — nặng, chỉ tính khi có tiêu chí dùng.
# Mỗi cột kèm 2 cột đi cùng (giá vượt, % hiện tại so với giá vượt): lọc cột nào trong nhóm thì cả 3 cùng hiện.
BREAK_METRIC_KEYS = {'brkTL3m': '3m', 'brkTL6m': '6m'}
BREAK_COMPANIONS = {k: (k + 'Px', k + 'Pct') for k in BREAK_METRIC_KEYS}
BREAK_ALL_KEYS = {k: grp for grp, ks in BREAK_COMPANIONS.items() for k in (grp, *ks)}      # cột → cột chính của nhóm
# Cột tính từ chỉ báo + phiên hôm nay (giá / cao / thấp / KL hiện tại): indicator_metrics
INDICATOR_KEYS = ('rsi14', 'mfi14', 'stochK', 'willR', 'cci20', 'bbWidth', 'adx14', 'atrPct',
                  *(f'from{s}{p}' for s in ('High', 'Low') for p in ('1m', '3m', '6m', '1y')))
# Cột phải có lịch sử nến mới tính được (các cột còn lại lấy thẳng từ quote)
TECH_METRIC_KEYS = (*_TECH_PERIOD, *_TECH_AVGVOL, *_TECH_DIST, *_TECH_VOLVS, *BREAK_ALL_KEYS, *INDICATOR_KEYS,
                    'upDays', 'downDays', 'upDaysBeforeDown', 'downDaysBeforeUp')


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


def tech_metrics(st, last, change, est=None):
    """Các con số cần lịch sử: thay đổi giá nhiều kỳ, số phiên tăng / giảm liên tục, KLTB, phiên vượt trendline giảm.
    st = thống kê tech.stats_from_bars (None nếu chưa có); last = giá hiện tại; change = giá − giá tham chiếu;
    est = KL dự kiến cả phiên hôm nay. Phiên vượt trendline kèm khoá '<cột>Day' = ngày 'dd/mm' để hiện ra ô."""
    out = dict.fromkeys(_TECH_PERIOD, None)
    out.update(dict.fromkeys(_TECH_AVGVOL, None))
    out.update(dict.fromkeys(_TECH_DIST, None))
    out.update(dict.fromkeys(_TECH_VOLVS, None))
    out.update(dict.fromkeys(BREAK_ALL_KEYS, None))
    out.update(upDays=None, downDays=None, upDaysBeforeDown=None, downDaysBeforeUp=None)
    if not st:
        return out
    for key, sk in _TECH_VOLVS.items():
        if est and st.get(sk):
            out[key] = est * 100 / st[sk]
    if last and last > 0:
        for key, per in _TECH_PERIOD.items():
            px = st.get(f'px{per}')
            if px and px > 0:
                out[key] = (last - px) * 100 / px
        for key, n in _TECH_DIST.items():
            ma = sma_live(st, last, n)
            if ma:
                out[key] = (last - ma) * 100 / ma
        for key, per in BREAK_METRIC_KEYS.items():
            # Hôm nay đang vượt (cùng luật tín hiệu "Vượt lên trendline giảm" mặc định) thì là 0, không thì lấy lần quét lùi
            px_key, pct_key = BREAK_COMPANIONS[key]
            if _break_down_line(st, {'last': last, 'est': est}, {'period': per, 'brk': tech.BREAK_UP * 100, 'vol': 'có'}):
                out[key], out[key + 'Day'], out[px_key] = 0, None, last          # vượt ngay hôm nay: giá vượt = giá hiện tại
            elif st.get('tb' + per):
                tb = st['tb' + per]
                out[key], out[key + 'Day'], out[px_key] = tb['k'], f"{tb['d'][8:10]}/{tb['d'][5:7]}", tb['p']
            if out[px_key]:
                out[pct_key] = (last - out[px_key]) * 100 / out[px_key]
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
MA_PERIODS = (5, 10, 15, 20, 45, 50, 100, 200)
P_HIGHLOW = _p('period', 'trong', tuple(PERIOD_NAME), '1y')
P_MA = _p('period', 'kỳ (phiên)', MA_PERIODS, 5)
P_RSI_UP = _p('level', 'ngưỡng quá mua', (60, 65, 70, 75, 80, 85, 90), 70, True, 0, 100)
P_RSI_DOWN = _p('level', 'ngưỡng quá bán', (10, 15, 20, 25, 30, 35, 40), 30, True, 0, 100)
TF_NAME = {'15m': '15 phút', 'D': 'ngày'}
P_TF = _p('tf', 'khung', tuple(TF_NAME), '15m')
P_RSI_LOOK = _p('look', 'đáy trong (nến)', (8, 12, 16, 20, 24, tech.RSI_KEEP), 16)
P_MA_STATE = _p('period', 'kỳ (phiên)', MA_PERIODS, 20)
P_STO_UP = _p('level', 'ngưỡng quá mua', (70, 75, 80, 85, 90), 80, True, 0, 100)
P_STO_DOWN = _p('level', 'ngưỡng quá bán', (10, 15, 20, 25, 30), 20, True, 0, 100)
P_WR_DOWN = _p('level', 'ngưỡng quá bán (−)', (70, 80, 90), 80, True, 0, 100)
P_WR_UP = _p('level', 'ngưỡng quá mua (−)', (10, 20, 30), 20, True, 0, 100)
P_CCI = _p('level', 'ngưỡng (±)', (100, 150, 200), 100, True, 0, 500)
P_ADX = _p('level', 'ADX tối thiểu', (20, 25, 30, 40), 25, True, 0, 100)
P_MFI_UP = _p('level', 'ngưỡng quá mua', (70, 75, 80, 85, 90), 80, True, 0, 100)
P_MFI_DOWN = _p('level', 'ngưỡng quá bán', (10, 15, 20, 25, 30), 20, True, 0, 100)
P_BB = _p('std', 'độ lệch chuẩn', (2, 3.5), 2, True, 0.5, 6)
P_PB_MA = _p('period', 'SMA (phiên)', tuple(tech.PB_SMA), 20)
P_PB_TL = _p('period', 'trendline trong', tuple(tech.TL_WINDOWS), '6m')
P_PB_TOL = _p('tol', 'vùng ± (%)', (1, 1.5, 2, 3), 2, True, 0.5, 5)
P_PB_DRY = _p('dry', 'KL cạn dần', ('có', 'không'), 'có')
P_BRK = _p('brk', 'vượt đường tối thiểu (%)', (0.5, 1, 2, 3), 1, True, 0, 10)
P_BRK_VOL = _p('vol', 'KL dự kiến ≥ KLTB 20', ('có', 'không'), 'có')


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
def rsi_now(st, last):
    """(RSI ở phiên đóng gần nhất, RSI nếu giá hiện tại là giá đóng cửa)."""
    ag, al, lc = st.get('ag'), st.get('al'), st.get('lc')
    if ag is None or al is None or lc is None:
        return None, None
    d = last - lc
    return tech.rsi_of(ag, al), tech.rsi_of(ag * 13 + max(d, 0), al * 13 + max(-d, 0))


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


def _rsi_bottom(st, lv, p):
    """RSI tạo đáy (luật Long của anh bên hệ phái sinh): trong `look` nến gần nhất RSI(14) từng ≤ ngưỡng quá bán, nay đã
    thoát lên trên ngưỡng + RSI trên Signal (WMA14 của RSI) + giá đóng cửa trên MA10 (SMA10).
    Khung ngày: ghép giá hiện tại làm giá đóng cửa hôm nay như các tín hiệu khác. Khung 15 phút: xét nến đã chốt gần
    nhất — danh sách đổi mỗi lần chốt nến, không nhảy ra nhảy vào theo từng nhịp giá."""
    rs = list(st.get('rs') or [])
    if p['tf'] == 'D':
        rs.append(rsi_now(st, lv['last'])[1])
        price, ma = lv['last'], sma_live(st, lv['last'], 10)
    else:
        price, ma = st.get('lc'), st.get('p10')
    n, k = tech.RSI_SIGNAL_N, p['look']
    if None in rs or len(rs) < max(n, k) or not price or not ma:
        return False
    signal = sum(i * r for i, r in enumerate(rs[-n:], 1)) / (n * (n + 1) / 2)    # WMA: nến mới nhất nặng nhất
    return min(rs[-k:]) <= p['level'] < rs[-1] and rs[-1] > signal and price > ma


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


# --- Pullback: đang xu hướng tăng, điều chỉnh về kiểm định SMA / trendline tăng ------------
def sma_live(st, last, n):
    """SMA(n) nếu giá hiện tại là giá đóng cửa hôm nay (như _sma_cross); None nếu thiếu số."""
    prev = st.get(f'p{n - 1}')
    return (last + (n - 1) * prev) / n if prev else None


def _pb_line(st, last, p, source):
    """(giá trị đường hôm nay, nhịp tăng → điều chỉnh, ngưỡng "đã đi xa") — None nếu đường không dốc lên / thiếu số."""
    if source == 'sma':
        n = p['period']
        line, ref, leg = sma_live(st, last, n), st.get(f'ps{n}'), st.get(f'pb{n}')
        if not line or not ref or not leg or not (st.get(f'p{n}') or 0) > ref:
            return None
        return line, leg, tech.PB_SMA[n][1]
    tl = st.get('tl' + p['period'])
    return (tl['v'] + tl['s'], tl, tech.TL_EXT) if tl else None


def _pullback(source, bounce):
    """Chung cho SMA / trendline. Xu hướng: đường dốc lên, đỉnh nhịp vừa rồi cách đường đủ xa, từ sau đỉnh không phiên nào
    đóng cửa thủng dưới vùng ±tol, (KL cạn) KLTB từ sau đỉnh kể cả KL dự kiến hôm nay < KLTB 20.
    Đang kiểm định: giá thấp hôm nay chạm vùng trên đường, giá hiện tại chưa rơi khỏi vùng dưới đường.
    Bật lên: chạm vùng trong 3 phiên gần nhất (gồm hôm nay), hôm nay giá trên đường và cao hơn giá đóng cửa hôm qua."""
    def fn(st, lv, p):
        last = lv['last']
        r = _pb_line(st, last, p, source)
        if r is None:
            return False
        line, leg, ext = r
        tol = p['tol'] / 100
        if line <= 0 or leg['ext'] < ext or (leg['mr'] is not None and leg['mr'] < 1 - tol):
            return False
        if p['dry'] == 'có':
            est, v20 = lv.get('est'), st.get('v20')
            total = (leg['vpb'] * leg['pk'] if leg['vpb'] else 0) + (est or 0)
            count = (leg['pk'] if leg['vpb'] else 0) + (1 if est else 0)
            if not count or not v20 or total / count >= v20:
                return False
        touched = min(lv.get('low') or last, last) <= line * (1 + tol)
        if bounce:
            return (touched or leg['lr'] <= 1 + tol) and last > line and last > st['lc']
        return touched and last >= line * (1 - tol)
    return fn


def _first_above(ratios, k):
    """Vị trí phiên đầu tiên đóng cửa ≥ k lần giá trị đường; None nếu chưa có."""
    return next((j for j, r in enumerate(ratios) if r >= k), None)


def _break_down_line(st, lv, p):
    """Vượt lên trendline giảm: các phiên trước chưa phiên nào đóng cửa vượt đường ≥ brk%, hôm nay giá vượt đường
    (kéo tới hôm nay) ≥ brk%, (vol) KL dự kiến cả phiên ≥ KLTB 20."""
    td = st.get('td' + p['period'])
    if not td:
        return False
    k = 1 + p['brk'] / 100
    if _first_above(td['cr'], k) is not None or lv['last'] < (td['v'] + td['s']) * k:
        return False
    if p['vol'] == 'có':
        est, v20 = lv.get('est'), st.get('v20')
        return bool(est and v20 and est >= v20)
    return True


BROKE = 1.01      # đóng cửa trên trendline giảm ≥ 1% = đã vượt (để tìm nhịp pullback sau đó)


def _retest_down_line(bounce):
    """Đã vượt trendline giảm (trong TL_RECENT phiên gần nhất) rồi quay lại kiểm định đường từ phía trên.
    Từ phiên vượt tới nay không phiên nào đóng cửa rơi khỏi vùng dưới đường (vượt hụt). Đang pullback: hôm nay giá thấp
    chạm vùng trên đường. Bật lên: chạm vùng trong 3 phiên gần nhất (sau phiên vượt), hôm nay xanh và trên đường."""
    def fn(st, lv, p):
        td = st.get('td' + p['period'])
        if not td:
            return False
        j = _first_above(td['cr'], BROKE)
        if j is None:
            return False
        tol, last = p['tol'] / 100, lv['last']
        line = td['v'] + td['s']
        if min(td['cr'][j:]) < 1 - tol or last < line * (1 - tol):
            return False
        touched = min(lv.get('low') or last, last) <= line * (1 + tol)
        if bounce:
            touched = touched or any(r <= 1 + tol for r in td['lr'][max(j + 1, len(td['lr']) - 2):])
            return touched and last > line and last > st['lc']
        return touched
    return fn


# --- Chỉ báo bổ sung (tech.py): mọi số ghép phiên hôm nay = giá / cao / thấp hiện tại ------------------------
def _hl(lv):
    """(cao nhất, thấp nhất) của phiên hôm nay tính cả giá hiện tại; quote thiếu cao / thấp thì lấy giá hiện tại."""
    last = lv['last']
    return max(lv.get('high') or last, last), min(lv.get('low') or last, last)


def ema_live(st, last, n):
    """EMA(n) nếu giá hiện tại là giá đóng cửa hôm nay (như _ema_cross); None nếu thiếu số."""
    e = st.get(f'e{n}')
    return (2 * last + (n - 1) * e) / (n + 1) if e else None


def _price_vs_ma(kind, above):
    def fn(st, lv, p):
        line = (sma_live if kind == 'sma' else ema_live)(st, lv['last'], p['period'])
        return bool(line) and (lv['last'] > line if above else lv['last'] < line)
    return fn


def _sma_above(st, lv, p):
    s, l = sma_live(st, lv['last'], p['short']), sma_live(st, lv['last'], p['long'])
    return bool(s and l) and s > l


def _ema_pair(up):
    def fn(st, lv, p):
        es, el = st.get(f"e{p['short']}"), st.get(f"e{p['long']}")
        s, l = ema_live(st, lv['last'], p['short']), ema_live(st, lv['last'], p['long'])
        if not (es and el and s and l):
            return False
        return (es <= el and s > l) if up else (es >= el and s < l)
    return fn


def _sar(kind):
    """Parabolic SAR: phiên hôm nay (giá cao / thấp hiện tại) đi qua SAR là đảo chiều (tech.sar_step)."""
    def fn(st, lv, p):
        if any(st.get(k) is None for k in ('sart', 'sar', 'sep', 'saf')):
            return False
        hi, lo = _hl(lv)
        *_, up, flip = tech.sar_step(st['sar'], st['sep'], st['saf'], st['sart'] == 1, hi, lo)
        if kind == 'flip_up':
            return flip and up
        if kind == 'flip_down':
            return flip and not up
        return up if kind == 'up' else not up
    return fn


def raw_k_now(st, lv):
    """%K thô (14) tính cả phiên hôm nay; None nếu thiếu số / cao nhất = thấp nhất."""
    hh, ll = st.get('hh13'), st.get('ll13')
    if hh is None or ll is None:
        return None
    hi, lo = _hl(lv)
    hh, ll = max(hh, hi), min(ll, lo)
    return (lv['last'] - ll) / (hh - ll) * 100 if hh > ll else None


def stoch_now(st, lv):
    """(%K, %D phiên đóng gần nhất, %K, %D tính cả phiên hôm nay) — Stochastic chậm 14, 3, 3; None nếu thiếu số."""
    kr, ks, d = st.get('skr'), st.get('sks'), st.get('skd')
    raw = raw_k_now(st, lv)
    if raw is None or d is None or not kr or not ks or None in kr or None in ks:
        return None
    k = (kr[0] + kr[1] + raw) / 3
    return ks[1], d, k, (ks[0] + ks[1] + k) / 3


def _stoch(kind):
    def fn(st, lv, p):
        r = stoch_now(st, lv)
        if r is None:
            return False
        k0, d0, k1, d1 = r
        if kind == 'cross_up':
            return k0 <= d0 and k1 > d1
        if kind == 'cross_down':
            return k0 >= d0 and k1 < d1
        a = p['level']
        if kind == 'cross_up_os':                     # %K cắt lên %D, lúc cắt %K còn trong vùng quá bán
            return k0 <= d0 and k1 > d1 and k0 <= a
        if kind == 'exit_os':
            return k0 <= a < k1
        if kind == 'exit_ob':
            return k0 >= a > k1
        return k1 < a if kind == 'below' else k1 > a
    return fn


def _willr(kind):
    """Williams %R (14) = %K thô − 100 (từ −100 đến 0). Thoát quá bán: cắt lên −level; thoát quá mua: cắt xuống −level."""
    def fn(st, lv, p):
        kr, raw = st.get('skr'), raw_k_now(st, lv)
        if raw is None or not kr or kr[-1] is None:
            return False
        w0, w1, a = kr[-1] - 100, raw - 100, -p['level']
        return (w0 <= a < w1) if kind == 'exit_os' else (w0 >= a > w1)
    return fn


def cci_now(st, lv):
    """(CCI(20) phiên đóng gần nhất, CCI tính cả phiên hôm nay); None nếu thiếu số."""
    tps, prev = st.get('tp19'), st.get('cci')
    if not tps or len(tps) < tech.CCI_N - 1 or prev is None:
        return None
    hi, lo = _hl(lv)
    cur = tech.cci(tps + [(hi + lo + lv['last']) / 3])
    return None if cur is None else (prev, cur)


def _cci(kind):
    def fn(st, lv, p):
        r = cci_now(st, lv)
        if r is None:
            return False
        c0, c1, a = r[0], r[1], p['level']
        if kind == 'exit_os':
            return c0 <= -a < c1
        if kind == 'exit_ob':
            return c0 >= a > c1
        return c1 > a if kind == 'above' else c1 < -a
    return fn


def dmi_now(st, lv):
    """(+DI, −DI phiên đóng gần nhất, +DI, −DI, ADX, ATR tính cả phiên hôm nay); None nếu thiếu số."""
    need = ('atr', 'pdm', 'mdm', 'dxa', 'lh', 'll', 'lc')
    if any(st.get(k) is None for k in need):
        return None
    hi, lo = _hl(lv)
    n = tech.DMI_N
    p, m, tr = tech.dm_tr((None, None, st['lh'], st['ll'], st['lc']), (None, None, hi, lo, lv['last']))
    atr = (st['atr'] * (n - 1) + tr) / n
    pdm = (st['pdm'] * (n - 1) + p) / n
    mdm = (st['mdm'] * (n - 1) + m) / n
    pd1, md1 = tech.di(pdm, atr), tech.di(mdm, atr)
    adx = 100 * (st['dxa'] * (n - 1) + tech.dx_frac(pd1, md1)) / n
    return tech.di(st['pdm'], st['atr']), tech.di(st['mdm'], st['atr']), pd1, md1, adx, atr


def _dmi(kind):
    def fn(st, lv, p):
        r = dmi_now(st, lv)
        if r is None:
            return False
        pd0, md0, pd1, md1, adx, _ = r
        if kind == 'cross_up':
            return pd0 <= md0 and pd1 > md1
        if kind == 'cross_down':
            return pd0 >= md0 and pd1 < md1
        if kind == 'adx':
            return adx > p['level']
        return pd1 > md1 and adx > p['level']           # xu hướng tăng mạnh
    return fn


def obv_now(st, lv):
    """(OBV, TB 20 phiên của OBV ở phiên đóng gần nhất, OBV, TB 20 tính cả hôm nay); KL hôm nay = KL dự kiến cả phiên."""
    obv, s19, m, lc = st.get('obv'), st.get('ob19'), st.get('obm'), st.get('lc')
    if None in (obv, s19, m, lc):
        return None
    vol, last = lv.get('est') or lv.get('volume') or 0, lv['last']
    cur = obv + (vol if last > lc else (-vol if last < lc else 0))
    return obv, m, cur, (s19 + cur) / tech.OBV_N


def _obv(kind):
    def fn(st, lv, p):
        r = obv_now(st, lv)
        if r is None:
            return False
        o0, m0, o1, m1 = r
        if kind == 'cross_up':
            return o0 <= m0 and o1 > m1
        if kind == 'cross_down':
            return o0 >= m0 and o1 < m1
        return o1 > m1
    return fn


def _ichimoku(kind):
    """Mây hôm nay = Span A / B tính 25 phiên trước (st['ca']), mây hôm qua st['cb']; Tenkan / Kijun ghép phiên hôm nay."""
    def fn(st, lv, p):
        need = ('tk', 'kj', 'ih8', 'il8', 'ih25', 'il25', 'ca', 'cb', 'lc')
        if any(st.get(k) is None for k in need):
            return False
        last, ca, cb = lv['last'], st['ca'], st['cb']
        if kind == 'above':
            return last > max(ca)
        if kind == 'below':
            return last < min(ca)
        if kind == 'break_up':
            return st['lc'] <= max(cb) and last > max(ca)
        hi, lo = _hl(lv)
        tk = (max(st['ih8'], hi) + min(st['il8'], lo)) / 2
        kj = (max(st['ih25'], hi) + min(st['il25'], lo)) / 2
        return (st['tk'] <= st['kj'] and tk > kj) if kind == 'tk_up' else (st['tk'] >= st['kj'] and tk < kj)
    return fn


def indicator_metrics(st, lv):
    """Các cột số tính từ chỉ báo + phiên hôm nay (INDICATOR_KEYS): RSI, MFI, Stochastic %K, Williams %R, CCI,
    độ rộng Bollinger, ADX, ATR %, % giá cách đỉnh / đáy (đỉnh / đáy tính cả giá cao / thấp hôm nay). Thiếu số → None."""
    out = dict.fromkeys(INDICATOR_KEYS, None)
    if not _valid(st, lv):
        return out
    last = lv['last']
    out['rsi14'] = rsi_now(st, last)[1]
    out['mfi14'] = mfi_now(st, lv)[1]
    s = stoch_now(st, lv)
    out['stochK'] = s[2] if s else None
    raw = raw_k_now(st, lv)
    out['willR'] = None if raw is None else raw - 100
    c = cci_now(st, lv)
    out['cci20'] = c[1] if c else None
    b = bb_now(st, last, 2)
    if b:
        mid = (st['p19'] * 19 + last) / 20
        out['bbWidth'] = (b[1][0] - b[1][1]) / mid * 100 if mid else None
    d = dmi_now(st, lv)
    if d:
        out['adx14'], out['atrPct'] = d[4], d[5] / last * 100
    hi, lo = _hl(lv)
    for per in ('1m', '3m', '6m', '1y'):
        h, l_ = st.get('hi' + per), st.get('lo' + per)
        if h:
            h = max(h, hi)
            out['fromHigh' + per] = (h - last) / h * 100
        if l_:
            l_ = min(l_, lo)
            out['fromLow' + per] = (last - l_) / l_ * 100 if l_ > 0 else None
    return out


def _sig(id_, group, label, params, fn):
    return Signal(id_, group, label, tuple(params), fn)


SIGNAL_LIST = [
    _sig('AbovePreviousHigh', 'price', 'Giá vượt đỉnh {period}', [P_HIGHLOW], _above_high),
    _sig('BelowPreviousLow', 'price', 'Giá thủng đáy {period}', [P_HIGHLOW], _below_low),
    _sig('EstimatedVolumeSurge', 'volume', 'KL dự kiến vượt TB {period} phiên tối thiểu {pct}%',
         [_p('period', 'TB (phiên)', MA_PERIODS, 5), _p('pct', 'vượt tối thiểu (%)', (10, 20, 30, 50, 70, 100, 150, 200, 300),
                                                      50, True, 1, 1000)], _est_volume_surge),
    _sig('OBVCrossAboveMA', 'volume', 'OBV cắt lên đường TB 20 phiên của OBV', [], _obv('cross_up')),
    _sig('OBVCrossBelowMA', 'volume', 'OBV cắt xuống đường TB 20 phiên của OBV', [], _obv('cross_down')),
    _sig('OBVAboveMA', 'volume', 'OBV đang trên đường TB 20 phiên (dòng tiền vào)', [], _obv('above')),
    _sig('PriceCrossAboveSMA', 'ma', 'Giá cắt lên SMA({period})', [P_MA], _sma_cross(True)),
    _sig('PriceCrossBelowSMA', 'ma', 'Giá cắt xuống SMA({period})', [P_MA], _sma_cross(False)),
    _sig('PriceCrossAboveEMA', 'ma', 'Giá cắt lên EMA({period})', [P_MA], _ema_cross(True)),
    _sig('PriceCrossBelowEMA', 'ma', 'Giá cắt xuống EMA({period})', [P_MA], _ema_cross(False)),
    _sig('ShortSMACrossAboveLongSMA', 'ma', 'SMA({short}) cắt lên SMA({long})',
         [_p('short', 'SMA ngắn', (5, 10, 15, 20, 50), 5), _p('long', 'cắt lên SMA dài', (15, 20, 45, 50, 100, 200), 15)], _sma_pair(True)),
    _sig('ShortSMACrossBelowLongSMA', 'ma', 'SMA({short}) cắt xuống SMA({long})',
         [_p('short', 'SMA ngắn', (5, 10, 15, 20, 50), 5), _p('long', 'cắt xuống SMA dài', (15, 20, 45, 50, 100, 200), 15)], _sma_pair(False)),
    _sig('PriceAboveSMA', 'ma', 'Giá đang trên SMA({period})', [P_MA_STATE], _price_vs_ma('sma', True)),
    _sig('PriceBelowSMA', 'ma', 'Giá đang dưới SMA({period})', [P_MA_STATE], _price_vs_ma('sma', False)),
    _sig('PriceAboveEMA', 'ma', 'Giá đang trên EMA({period})', [P_MA_STATE], _price_vs_ma('ema', True)),
    _sig('PriceBelowEMA', 'ma', 'Giá đang dưới EMA({period})', [P_MA_STATE], _price_vs_ma('ema', False)),
    _sig('ShortSMAAboveLongSMA', 'ma', 'SMA({short}) đang trên SMA({long})',
         [_p('short', 'SMA ngắn', (5, 10, 15, 20, 50), 50), _p('long', 'trên SMA dài', (15, 20, 45, 50, 100, 200), 200)],
         _sma_above),
    _sig('ShortEMACrossAboveLongEMA', 'ma', 'EMA({short}) cắt lên EMA({long})',
         [_p('short', 'EMA ngắn', (5, 10, 15, 20, 50), 10), _p('long', 'cắt lên EMA dài', (15, 20, 45, 50, 100, 200), 20)],
         _ema_pair(True)),
    _sig('ShortEMACrossBelowLongEMA', 'ma', 'EMA({short}) cắt xuống EMA({long})',
         [_p('short', 'EMA ngắn', (5, 10, 15, 20, 50), 10), _p('long', 'cắt xuống EMA dài', (15, 20, 45, 50, 100, 200), 20)],
         _ema_pair(False)),
    _sig('RSICrossAboveOverBoughtLine', 'rsi', 'RSI(14) đi vào vùng quá mua (trên {level})', [P_RSI_UP], _rsi('cross_up')),
    _sig('RSICrossBelowOverBoughtLine', 'rsi', 'RSI(14) thoát khỏi vùng quá mua (trên {level})', [P_RSI_UP], _rsi('cross_down')),
    _sig('RSIAboveOverBoughtLine', 'rsi', 'RSI(14) đang trong vùng quá mua (trên {level})', [P_RSI_UP], _rsi('above')),
    _sig('RSICrossBelowOverSoldLine', 'rsi', 'RSI(14) đi vào vùng quá bán (dưới {level})', [P_RSI_DOWN], _rsi('cross_down')),
    _sig('RSICrossAboveOverSoldLine', 'rsi', 'RSI(14) thoát khỏi vùng quá bán (dưới {level})', [P_RSI_DOWN], _rsi('cross_up')),
    _sig('RSIBelowOverSoldLine', 'rsi', 'RSI(14) đang trong vùng quá bán (dưới {level})', [P_RSI_DOWN], _rsi('below')),
    _sig('RSIBottom', 'rsi', 'RSI tạo đáy khung {tf}: thoát quá bán {level} (đáy trong {look} nến), RSI trên Signal, '
                             'giá trên MA10', [P_TF, P_RSI_DOWN, P_RSI_LOOK], _rsi_bottom),
    _sig('MFICrossAboveOverBoughtLine', 'mfi', 'MFI(14) đi vào vùng quá mua (trên {level})', [P_MFI_UP], _mfi('cross_up')),
    _sig('MFICrossBelowOverBoughtLine', 'mfi', 'MFI(14) thoát khỏi vùng quá mua (trên {level})', [P_MFI_UP], _mfi('cross_down')),
    _sig('MFIAboveOverBoughtLine', 'mfi', 'MFI(14) đang trong vùng quá mua (trên {level})', [P_MFI_UP], _mfi('above')),
    _sig('MFICrossBelowOverSoldLine', 'mfi', 'MFI(14) đi vào vùng quá bán (dưới {level})', [P_MFI_DOWN], _mfi('cross_down')),
    _sig('MFICrossAboveOverSoldLine', 'mfi', 'MFI(14) thoát khỏi vùng quá bán (dưới {level})', [P_MFI_DOWN], _mfi('cross_up')),
    _sig('MFIBelowOverSoldLine', 'mfi', 'MFI(14) đang trong vùng quá bán (dưới {level})', [P_MFI_DOWN], _mfi('below')),
    _sig('StochKCrossAboveD', 'stoch', 'Stochastic: %K cắt lên %D', [], _stoch('cross_up')),
    _sig('StochKCrossBelowD', 'stoch', 'Stochastic: %K cắt xuống %D', [], _stoch('cross_down')),
    _sig('StochKCrossAboveDOverSold', 'stoch', 'Stochastic: %K cắt lên %D từ vùng quá bán (dưới {level})', [P_STO_DOWN],
         _stoch('cross_up_os')),
    _sig('StochCrossAboveOverSoldLine', 'stoch', 'Stochastic thoát khỏi vùng quá bán (dưới {level})', [P_STO_DOWN],
         _stoch('exit_os')),
    _sig('StochCrossBelowOverBoughtLine', 'stoch', 'Stochastic thoát khỏi vùng quá mua (trên {level})', [P_STO_UP],
         _stoch('exit_ob')),
    _sig('StochBelowOverSoldLine', 'stoch', 'Stochastic đang trong vùng quá bán (dưới {level})', [P_STO_DOWN], _stoch('below')),
    _sig('StochAboveOverBoughtLine', 'stoch', 'Stochastic đang trong vùng quá mua (trên {level})', [P_STO_UP], _stoch('above')),
    _sig('WillRCrossAboveOverSoldLine', 'osc', 'Williams %R thoát vùng quá bán (cắt lên −{level})', [P_WR_DOWN],
         _willr('exit_os')),
    _sig('WillRCrossBelowOverBoughtLine', 'osc', 'Williams %R thoát vùng quá mua (cắt xuống −{level})', [P_WR_UP],
         _willr('exit_ob')),
    _sig('CCICrossAboveOverSoldLine', 'osc', 'CCI(20) thoát vùng quá bán (cắt lên −{level})', [P_CCI], _cci('exit_os')),
    _sig('CCICrossBelowOverBoughtLine', 'osc', 'CCI(20) thoát vùng quá mua (cắt xuống +{level})', [P_CCI], _cci('exit_ob')),
    _sig('CCIAboveOverBoughtLine', 'osc', 'CCI(20) đang trên +{level}', [P_CCI], _cci('above')),
    _sig('CCIBelowOverSoldLine', 'osc', 'CCI(20) đang dưới −{level}', [P_CCI], _cci('below')),
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
    _sig('ADXAboveLevel', 'adx', 'ADX(14) trên {level} (có xu hướng mạnh)', [P_ADX], _dmi('adx')),
    _sig('DIPlusCrossAboveDIMinus', 'adx', '+DI cắt lên −DI', [], _dmi('cross_up')),
    _sig('DIPlusCrossBelowDIMinus', 'adx', '+DI cắt xuống −DI', [], _dmi('cross_down')),
    _sig('ADXStrongUptrend', 'adx', 'Xu hướng tăng mạnh: +DI trên −DI, ADX trên {level}', [P_ADX], _dmi('strong_up')),
    _sig('SARFlipUp', 'sar', 'Parabolic SAR đảo chiều tăng (giá vượt lên SAR)', [], _sar('flip_up')),
    _sig('SARFlipDown', 'sar', 'Parabolic SAR đảo chiều giảm (giá thủng SAR)', [], _sar('flip_down')),
    _sig('SARUptrend', 'sar', 'Parabolic SAR đang báo xu hướng tăng (SAR dưới giá)', [], _sar('up')),
    _sig('SARDowntrend', 'sar', 'Parabolic SAR đang báo xu hướng giảm (SAR trên giá)', [], _sar('down')),
    _sig('IchimokuAboveCloud', 'ichimoku', 'Giá đang trên mây Ichimoku', [], _ichimoku('above')),
    _sig('IchimokuBelowCloud', 'ichimoku', 'Giá đang dưới mây Ichimoku', [], _ichimoku('below')),
    _sig('IchimokuBreakAboveCloud', 'ichimoku', 'Giá vượt lên trên mây Ichimoku', [], _ichimoku('break_up')),
    _sig('IchimokuTenkanCrossAboveKijun', 'ichimoku', 'Tenkan cắt lên Kijun', [], _ichimoku('tk_up')),
    _sig('IchimokuTenkanCrossBelowKijun', 'ichimoku', 'Tenkan cắt xuống Kijun', [], _ichimoku('tk_down')),
    _sig('PullbackToSMA', 'pullback', 'Pullback về SMA({period}), vùng ±{tol}%, KL cạn: {dry}',
         [P_PB_MA, P_PB_TOL, P_PB_DRY], _pullback('sma', False)),
    _sig('PullbackBounceSMA', 'pullback', 'Bật lên từ SMA({period}), vùng ±{tol}%, KL cạn: {dry}',
         [P_PB_MA, P_PB_TOL, P_PB_DRY], _pullback('sma', True)),
    _sig('PullbackToTrendline', 'pullback', 'Pullback về trendline tăng {period}, vùng ±{tol}%, KL cạn: {dry}',
         [P_PB_TL, P_PB_TOL, P_PB_DRY], _pullback('tl', False)),
    _sig('PullbackBounceTrendline', 'pullback', 'Bật lên từ trendline tăng {period}, vùng ±{tol}%, KL cạn: {dry}',
         [P_PB_TL, P_PB_TOL, P_PB_DRY], _pullback('tl', True)),
    _sig('BreakDownTrendline', 'pullback', 'Vượt lên trendline giảm {period} ≥ {brk}%, KL ≥ TB20: {vol}',
         [P_PB_TL, P_BRK, P_BRK_VOL], _break_down_line),
    _sig('PullbackBrokenDownTrendline', 'pullback', 'Sau vượt trendline giảm {period}: pullback về ±{tol}%',
         [P_PB_TL, P_PB_TOL], _retest_down_line(False)),
    _sig('BounceBrokenDownTrendline', 'pullback', 'Sau vượt trendline giảm {period}: bật lên ±{tol}%',
         [P_PB_TL, P_PB_TOL], _retest_down_line(True)),
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
    if 'short' in params and 'long' in params and params['short'] >= params['long']:
        params['short'], params['long'] = (p.default for p in sig.params)     # đường ngắn phải ngắn hơn đường dài
    return {'id': sig.id, 'params': params}


def _show(v):
    return str(int(v)) if isinstance(v, float) and v.is_integer() else str(v)


def param_text(value):
    """Giá trị tham số như người dùng thấy: '1w' → '1 tuần', '15m' → '15 phút', 3.5 → '3.5', 70.0 → '70'."""
    return TF_NAME.get(value) or PERIOD_NAME.get(value, _show(value))


def signal_tf(sig):
    """Khung nến tín hiệu cần: 'D' (nến ngày — mọi tín hiệu không có tham số khung) hoặc '15m'."""
    return (sig.get('params') or {}).get('tf', 'D')


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
    lv = {'last', 'high', 'low', 'volume', 'est'} (giá nghìn đồng), thêm 'intra': {'15m': thống kê nến 15 phút}
    khi có tiêu chí cần. Thiếu số → False."""
    s = SIGNALS.get(sig.get('id'))
    if s is None:
        return False
    if signal_tf(sig) != 'D':
        st = ((lv or {}).get('intra') or {}).get(signal_tf(sig))
    if not _valid(st, lv):
        return False
    params = dict(sig.get('params') or {})
    if 'pct' in params:
        params['pct'] = params['pct'] / 100        # lưu theo % (50), tính theo tỷ lệ (0.5)
    try:
        return bool(s.fn(st, lv, params))
    except (KeyError, TypeError, ZeroDivisionError, ValueError):
        return False
