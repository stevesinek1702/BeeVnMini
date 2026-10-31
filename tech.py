"""
Chỉ báo kỹ thuật tính từ nến ngày — dữ liệu nền cho các điều kiện lọc kiểu FireAnt Screener
(RSI, MFI, MACD, Bollinger, giá cắt SMA/EMA, vượt đỉnh / thủng đáy, số phiên tăng giảm liên tục…).

Mọi con số tính trên các phiên ĐÃ ĐÓNG (bỏ nến hôm nay) — đúng cách bảng thống kê của FireAnt đưa ra;
điều kiện lọc (conditions.py) rồi ghép giá hiện tại vào để biết "hôm nay có cắt lên / cắt xuống không".
Riêng khung 15 phút (intraday_stats): xét nến đã chốt gần nhất, không ghép giá hiện tại.
Giá tính bằng nghìn đồng như cột Giá của bảng; khối lượng bằng cổ phiếu.
Không dính giao diện, không dính mạng (lấy nến nằm ở core.py) nên test được.
"""
import calendar
import math

# Cửa sổ trung bình mà các điều kiện cần (số phiên): giá đóng cửa, khối lượng.
PRICE_AVG_N = (4, 5, 9, 10, 14, 15, 19, 20, 44, 45, 49, 50, 99, 100, 199, 200)
VOL_AVG_N = (4, 5, 9, 10, 14, 19, 20, 44)
EMA_N = (5, 10, 15, 20, 45, 50, 100, 200)
VERSION = 8        # đổi khi thêm số thống kê mới → bộ nhớ đệm tech.json cũ của hôm nay bị bỏ, tải lại
# Các mốc "1 tuần … 1 năm": tính theo lịch (ngày hoặc tháng) lùi từ hôm nay.
PERIODS = {'1w': ('d', 7), '2w': ('d', 14), '1m': ('m', 1), '3m': ('m', 3), '6m': ('m', 6), '1y': ('m', 12)}
MIN_BARS = 20      # ít hơn chừng này phiên (mã mới niêm yết) thì chưa tính — thà thiếu còn hơn sai

# Pullback về SMA: kỳ → (số phiên tìm đỉnh nhịp tăng, đỉnh phải cách SMA tối thiểu); SMA dốc lên = hôm qua > 10 phiên trước.
PB_SMA = {10: (15, .04), 20: (20, .05), 50: (30, .08)}
PB_SLOPE = 10
# Trendline tự vẽ trên GIÁ ĐÓNG CỬA (như biểu đồ đường): đáy / đỉnh = giá đóng cửa thấp / cao nhất trong 3 phiên mỗi bên;
# nối 2 điểm cách nhau ≥ 10 phiên, dốc ≤ 1%/phiên; các điểm khác cách đường ≤ 2% vẫn tính là "chạm" và giá đóng cửa
# được xuyên qua đường tối đa 2% (lệch 1–2% như mắt người kẻ); đường phải đi qua ít nhất 3 điểm (2 điểm nối + 1 lần chạm).
# • Trendline tăng (nối đáy): tới hôm qua chưa thủng; sau đáy 2 giá đã lên cách đường ≥ 5% và có đỉnh cao hơn
#   đỉnh giữa 2 đáy (đáy cao dần mà đỉnh thấp dần là tích luỹ, không phải xu hướng tăng).
# • Trendline giảm (nối đỉnh): giữa các lần chạm giá đã xuống cách đường ≥ 5%; được phép đã vượt lên đường trong
#   TL_RECENT phiên gần nhất (để bắt nhịp vượt rồi quay lại kiểm định) — vượt từ trước đó thì đường đã cũ, bỏ.
TL_WINDOWS = {'3m': 60, '6m': 120}
TL_PIVOT, TL_MIN_GAP, TL_MAX_SLOPE = 3, 10, .01
TL_TOL, TL_EXT, TL_RECENT, TL_TOUCHES = .02, .05, 10, 3
TL_MIN_BARS = 40
# Quét lùi tìm phiên vượt trendline giảm gần nhất: tối đa chừng này phiên; vượt = đóng cửa trên đường ≥ 1%
# (các phiên trước đó chưa vượt) và KL phiên đó ≥ KLTB 20 phiên liền trước.
BREAK_DAYS, BREAK_UP = 20, .01
# RSI tạo đáy (luật Long của anh bên hệ phái sinh): Signal = WMA(14) của RSI(14); giữ RSI của RSI_KEEP nến đã đóng
# gần nhất — đủ cho WMA14 và tìm đáy trong tối đa RSI_KEEP nến.
RSI_SIGNAL_N, RSI_KEEP = 14, 30
# Nến 15 phút (dchart ghi giờ MỞ nến): các buổi khớp lệnh theo phút trong ngày, giờ VN. Nến ATC của HOSE mang giờ 14:45
# → buổi chiều tính tới 15:00 (khung 14:45 coi như chưa chốt) cho chắc nến ATC đã lên dchart.
INTRA_MIN = 15
INTRA_SESSIONS = ((9 * 60, 11 * 60 + 30), (13 * 60, 15 * 60))
INTRA_MIN_BARS = 60     # ~4 phiên mã thanh khoản tốt; mã ít khớp lệnh thì nến thưa, RSI 15 phút vô nghĩa → không tính
# Chỉ báo bổ sung: Parabolic SAR (0.02, 0.2) kiểu Wilder; Stochastic chậm (14, 3, 3) — Williams %R (14) = %K thô − 100;
# CCI (20); ADX / DMI (14) như ta.dmi của TradingView (trung bình Wilder); OBV + TB 20 phiên; Ichimoku (9, 26, 52),
# mây dời tới 25 phiên như TradingView. Như mọi chỉ báo ở đây: tính tới phiên đã đóng, conditions.py ghép phiên hôm nay.
SAR_STEP, SAR_MAX = .02, .2
STOCH_N, CCI_N, DMI_N, OBV_N = 14, 20, 14, 20
ICHI_T, ICHI_K, ICHI_B, ICHI_SHIFT = 9, 26, 52, 25


def minus_period(date, kind, n):
    """'2026-10-15' lùi n ngày / n tháng. Lùi tháng mà ngày không có (31/3 → 28/2) thì lấy ngày cuối tháng."""
    y, m, d = (int(x) for x in date.split('-'))
    if kind == 'd':
        from datetime import date as _d, timedelta
        return (_d(y, m, d) - timedelta(days=n)).isoformat()
    m -= n
    while m < 1:
        m += 12
        y -= 1
    return f'{y:04d}-{m:02d}-{min(d, calendar.monthrange(y, m)[1]):02d}'


def closed_bars(bars, today, date_of):
    """Nến dchart {t,o,h,l,c,v} → (ngày, mở, cao, thấp, đóng, KL) các phiên đã đóng, cũ → mới.
    Bỏ nến của hôm nay (phiên đang chạy, chưa chốt) và nến hỏng."""
    if not isinstance(bars, dict) or bars.get('s') != 'ok':
        return []
    try:
        cols = [bars[k] for k in ('t', 'o', 'h', 'l', 'c', 'v')]
    except KeyError:
        return []
    if not all(isinstance(c, list) for c in cols) or len({len(c) for c in cols}) != 1:
        return []
    out = []
    for t, o, h, lo, c, v in zip(*cols):
        day = date_of(t)
        if day >= today or None in (o, h, lo, c, v) or c <= 0:
            continue
        out.append((day, o, h, lo, c, v))
    return out


def _mean(a):
    return sum(a) / len(a)


def _std(a):
    """Độ lệch chuẩn tổng thể (chia n) — cách Bollinger Band tính; công thức "giá mới vào cửa sổ"
    của FireAnt (stdEv19d → stdEv20d) cũng dựa trên đúng loại này."""
    m = _mean(a)
    return math.sqrt(sum((x - m) ** 2 for x in a) / len(a))


def ema_last(values, n):
    """EMA(n) tại giá trị cuối, hệ số 2/(n+1), khởi từ giá trị đầu. Đủ dài thì mồi đầu chuỗi không còn ảnh hưởng."""
    a = 2 / (n + 1)
    e = values[0]
    for v in values[1:]:
        e = a * v + (1 - a) * e
    return e


def wilder_rsi_parts(closes, n=14):
    """(avgGain, avgLoss) kiểu Wilder tại phiên cuối: trung bình đơn n biến động đầu, sau đó (cũ×(n−1)+mới)/n."""
    if len(closes) < n + 1:
        return None, None
    diffs = [b - a for a, b in zip(closes, closes[1:])]
    ag = sum(max(d, 0) for d in diffs[:n]) / n
    al = sum(max(-d, 0) for d in diffs[:n]) / n
    for d in diffs[n:]:
        ag = (ag * (n - 1) + max(d, 0)) / n
        al = (al * (n - 1) + max(-d, 0)) / n
    return ag, al


def rsi_of(gain, loss):
    return 100.0 if loss == 0 else 100 - 100 / (1 + gain / loss)


def rsi_tail(closes, keep=RSI_KEEP, n=14):
    """RSI Wilder(n) tại `keep` nến cuối (cũ → mới), cùng cách tính wilder_rsi_parts; [] nếu chưa đủ n+1 nến."""
    if len(closes) < n + 1:
        return []
    diffs = [b - a for a, b in zip(closes, closes[1:])]
    ag = sum(max(d, 0) for d in diffs[:n]) / n
    al = sum(max(-d, 0) for d in diffs[:n]) / n
    out = [rsi_of(ag, al)]
    for d in diffs[n:]:
        ag = (ag * (n - 1) + max(d, 0)) / n
        al = (al * (n - 1) + max(-d, 0)) / n
        out.append(rsi_of(ag, al))
    return out[-keep:]


def money_flow(bars, n=14):
    """MFI: (dòng tiền dương n−1 phiên cuối, dòng tiền âm n−1 phiên cuối, MFI n phiên tại phiên cuối, điển hình phiên cuối).
    Dòng tiền = giá điển hình × KL; dương nếu giá điển hình tăng so với phiên trước, âm nếu giảm."""
    if len(bars) < n + 1:
        return None, None, None, None
    tp = [(h + lo + c) / 3 for _, _, h, lo, c, _ in bars]
    pos, neg = [], []
    for i in range(1, len(bars)):
        mf = tp[i] * bars[i][5]
        pos.append(mf if tp[i] > tp[i - 1] else 0.0)
        neg.append(mf if tp[i] < tp[i - 1] else 0.0)
    p13, n13 = sum(pos[-(n - 1):]), sum(neg[-(n - 1):])
    p14, n14 = sum(pos[-n:]), sum(neg[-n:])
    mfi = 100.0 if n14 == 0 else 100 - 100 / (1 + p14 / n14)
    return p13, n13, mfi, tp[-1]


def sar_step(sar, ep, af, up, h, lo):
    """Một phiên Parabolic SAR như ta.sar của TradingView: SAR phiên này = SAR trước + af·(EP − SAR trước) (chưa kẹp);
    giá thấp (đang tăng) / giá cao (đang giảm) chạm qua là đảo chiều — SAR nhảy về đỉnh / đáy của nhịp cũ.
    → (SAR chưa kẹp, EP, af, chiều tăng?, vừa đảo chiều?)."""
    sar = sar + af * (ep - sar)
    if up and sar > lo:
        return max(h, ep), lo, SAR_STEP, False, True
    if not up and sar < h:
        return min(lo, ep), h, SAR_STEP, True, True
    if up and h > ep:
        ep, af = h, min(af + SAR_STEP, SAR_MAX)
    elif not up and lo < ep:
        ep, af = lo, min(af + SAR_STEP, SAR_MAX)
    return sar, ep, af, up, False


def parabolic_sar(rows):
    """Parabolic SAR (0.02, 0.2) như ta.sar của TradingView tại phiên cuối → (chiều: 1 tăng / −1 giảm, SAR, EP, af);
    SAR đã kẹp không lấn vào giá thấp / cao của 2 phiên trước. Khởi đầu theo chiều 2 phiên đầu."""
    if len(rows) < 3:
        return None, None, None, None
    up = rows[1][4] > rows[0][4]
    ep, sar, af = (rows[1][2], rows[0][3], SAR_STEP) if up else (rows[1][3], rows[0][2], SAR_STEP)
    for i in range(1, len(rows)):
        h, lo = rows[i][2], rows[i][3]
        if i == 1:                              # phiên đầu xu hướng: chỉ xét đảo chiều, chưa dời EP
            sar = sar + af * (ep - sar)
            if up and sar > lo:
                sar, ep, up = max(h, ep), lo, False
            elif not up and sar < h:
                sar, ep, up = min(lo, ep), h, True
        else:
            sar, ep, af, up, _ = sar_step(sar, ep, af, up, h, lo)
        prev = rows[max(i - 2, 0):i]           # 2 phiên trước (phiên thứ 2 chỉ có 1)
        sar = min([sar] + [r[3] for r in prev]) if up else max([sar] + [r[2] for r in prev])
    return (1 if up else -1), sar, ep, af


def raw_k(rows, i, n=STOCH_N):
    """%K thô (n) tại phiên i; None nếu chưa đủ phiên hoặc cao nhất = thấp nhất."""
    if i < n - 1:
        return None
    win = rows[i - n + 1:i + 1]
    hh, ll = max(r[2] for r in win), min(r[3] for r in win)
    return (rows[i][4] - ll) / (hh - ll) * 100 if hh > ll else None


def cci(tps):
    """CCI của dãy giá điển hình (phần tử cuối là phiên đang xét); None nếu dao động trung bình = 0."""
    m = _mean(tps)
    md = sum(abs(x - m) for x in tps) / len(tps)
    return (tps[-1] - m) / (.015 * md) if md else None


def _rma(values, n):
    """Trung bình Wilder (rma của TradingView) tại từng phần tử: mồi bằng trung bình đơn n phần tử đầu, sau đó
    (cũ×(n−1)+mới)/n; các phần tử trước đó None."""
    out = [None] * len(values)
    if len(values) < n:
        return out
    a = _mean(values[:n])
    out[n - 1] = a
    for i in range(n, len(values)):
        a = (a * (n - 1) + values[i]) / n
        out[i] = a
    return out


def dm_tr(prev, cur):
    """(+DM, −DM, TR) của phiên `cur` so với phiên `prev` — mỗi phiên dạng (…, cao, thấp, đóng, …)."""
    up, down = cur[2] - prev[2], prev[3] - cur[3]
    return (up if up > down and up > 0 else 0.0, down if down > up and down > 0 else 0.0,
            max(cur[2] - cur[3], abs(cur[2] - prev[4]), abs(cur[3] - prev[4])))


def di(dm, atr):
    return 100 * dm / atr if atr else 0.0


def dx_frac(pdi, mdi):
    """|+DI − −DI| / (+DI + −DI) — ADX là trung bình Wilder của số này × 100."""
    s = pdi + mdi
    return abs(pdi - mdi) / (s if s else 1)


def dmi_parts(rows, n=DMI_N):
    """ADX / DMI tại phiên cuối: (trung bình Wilder của TR, +DM, −DM, |+DI − −DI| / (+DI + −DI)); None nếu thiếu phiên."""
    parts = [dm_tr(p, r) for p, r in zip(rows, rows[1:])]
    atr = _rma([x[2] for x in parts], n)
    pdm = _rma([x[0] for x in parts], n)
    mdm = _rma([x[1] for x in parts], n)
    dx = [dx_frac(di(p, a), di(m, a)) for a, p, m in zip(atr, pdm, mdm) if a is not None]
    adx = _rma(dx, n)
    if not adx or adx[-1] is None:
        return None
    return atr[-1], pdm[-1], mdm[-1], adx[-1]


def mid_range(rows, i, n):
    """(cao nhất + thấp nhất) / 2 của n phiên tính tới phiên i — đường Tenkan / Kijun / Span B; None nếu chưa đủ phiên."""
    if i < n - 1:
        return None
    win = rows[i - n + 1:i + 1]
    return (max(r[2] for r in win) + min(r[3] for r in win)) / 2


def ichimoku_lead(rows, i):
    """[Span A, Span B] tính ở phiên i — tức mây của phiên i + 25; None nếu chưa đủ phiên."""
    t, k, b = mid_range(rows, i, ICHI_T), mid_range(rows, i, ICHI_K), mid_range(rows, i, ICHI_B)
    return None if None in (t, k, b) else [(t + k) / 2, b]


def streak(closes):
    """Số phiên tăng (dương) hoặc giảm (âm) liên tục tính đến phiên cuối; đứng giá = 0."""
    s = 0
    for i in range(len(closes) - 1, 0, -1):
        d = closes[i] - closes[i - 1]
        sign = 1 if d > 0 else (-1 if d < 0 else 0)
        if sign == 0 or (s != 0 and sign != (1 if s > 0 else -1)):
            break
        s += sign
    return s


def sma_series(closes, n):
    """SMA(n) tại từng phiên (None khi chưa đủ n phiên)."""
    out = [None] * len(closes)
    s = 0.0
    for i, c in enumerate(closes):
        s += c
        if i >= n:
            s -= closes[i - n]
        if i >= n - 1:
            out[i] = s / n
    return out


def pullback_leg(rows, line, lookback):
    """Nhịp tăng rồi điều chỉnh gần nhất so với 1 đường hỗ trợ (line[i] = giá trị đường ở phiên i).
    Đỉnh nhịp = phiên có giá cao nhất trong `lookback` phiên đã đóng gần nhất (bằng nhau thì lấy phiên sau).
    ext: đỉnh / đường tại đỉnh − 1; pk: số phiên sau đỉnh; vpb: KLTB các phiên sau đỉnh; mr: thấp nhất của
    đóng cửa / đường từ sau đỉnh (vpb, mr = None nếu đỉnh là phiên cuối); lr: thấp nhất của giá thấp / đường 2 phiên cuối."""
    n = len(rows)
    start = max(n - lookback, 0)
    if n < 2 or any(line[i] is None or line[i] <= 0 for i in range(min(start, n - 2), n)):
        return None
    peak = max(range(start, n), key=lambda i: (rows[i][2], i))
    after = range(peak + 1, n)
    return {'ext': rows[peak][2] / line[peak] - 1, 'pk': len(after),
            'vpb': _mean([rows[i][5] for i in after]) if after else None,
            'mr': min(rows[i][4] / line[i] for i in after) if after else None,
            'lr': min(rows[i][3] / line[i] for i in (n - 2, n - 1))}


def pivots(values, high=False, k=TL_PIVOT):
    """Chỉ số các đáy (giá thấp nhỏ nhất trong k phiên mỗi bên) hoặc đỉnh (high=True: giá cao lớn nhất).
    Điểm sát cuối chuỗi chưa đủ k phiên sau thì chưa tính."""
    pick = max if high else min
    return [i for i in range(k, len(values) - k) if values[i] == pick(values[i - k:i + k + 1])]


def trend_line(rows, window, up=True):
    """Trendline tự vẽ trên giá đóng cửa trong `window` phiên đã đóng gần nhất (luật ở đầu file: TL_*).
    up=True: trendline tăng nối đáy; up=False: trendline giảm nối đỉnh (mọi phép so lật chiều bằng sg).
    Chọn như mắt người kẻ: từ đáy / đỉnh lớn sớm nhất còn giữ được đường → tới điểm gần nhất mà giữa chừng không giá
    đóng cửa nào xuyên quá TL_TOL (ôm sát giá nhất).
    Trả {'v': giá trị đường phiên cuối, 's': dốc mỗi phiên, 'a'/'b': ngày 2 điểm nối, 'e': ngày lần chạm cuối,
    't': số lần chạm} hoặc None. Trendline tăng thêm các số của nhịp pullback_leg; trendline giảm thêm 'cr' / 'lr' =
    giá đóng cửa / giá thấp chia giá trị đường của các phiên sau lần chạm cuối (tối đa TL_RECENT phiên gần nhất)."""
    rows = rows[-window:]
    if len(rows) < TL_MIN_BARS:
        return None
    closes = [r[4] for r in rows]
    highs = [r[2] for r in rows]
    sg = 1 if up else -1
    last = len(rows) - 1
    # Giá đóng cửa phải nằm đúng phía của đường (cho lệch TL_TOL) tới hết `until`; trendline giảm được vượt gần đây
    until = last if up else last - TL_RECENT
    # Đỉnh mới sau khi đã vượt (trong TL_RECENT phiên cuối) không được làm điểm nối — kẻo đường "nuốt" luôn nhịp vượt
    piv = [p for p in pivots(closes, high=not up) if p <= until]
    # Giá đóng cửa đã chia sẵn cho (1 ∓ TL_TOL): phiên i không xuyên đường quá TL_TOL ⇔ sg·đường(i) ≤ sg·edge[i]
    edge = [c / (1 - sg * TL_TOL) for c in closes]
    after = {}          # b → giới hạn dốc để từ sau b tới `until` không phiên nào xuyên đường (tính khi cần, nhớ lại)

    def after_lim(b):
        if b not in after:
            after[b] = min((sg * (edge[i] - closes[b]) / (i - b) for i in range(b + 1, until + 1)), default=math.inf)
        return after[b]

    # Duyệt đúng thứ tự ưu tiên (a sớm nhất, rồi b muộn nhất): đường hợp lệ đầu tiên gặp là đường cần tìm
    for ai, a in enumerate(piv):
        y0 = closes[a]
        before = None   # before[b] = giới hạn dốc để giữa a và b không phiên nào xuyên đường — dựng 1 lượt khi cần
        for b in reversed(piv[ai + 1:]):
            if b - a < TL_MIN_GAP or sg * (closes[b] - y0) <= 0:
                continue
            s = (closes[b] - y0) / (b - a)
            if abs(s) > TL_MAX_SLOPE * y0 or sg * s > after_lim(b):
                continue
            if before is None:
                before = [math.inf] * (b + 1)
                for i in range(a + 1, b):
                    before[i + 1] = min(before[i], sg * (edge[i] - y0) / (i - a))
            if sg * s > before[b]:
                continue
            # Tăng: đỉnh sau đáy 2 phải cao hơn đỉnh giữa 2 đáy
            if up and max(highs[b + 1:]) < max(highs[a:b + 1]):
                continue
            line = [y0 + s * (i - a) for i in range(len(rows))]
            touch = [p for p in piv if a <= p <= until and abs(closes[p] / line[p] - 1) <= TL_TOL]
            if len(touch) < TL_TOUCHES:
                continue
            e = touch[-1]
            if up:
                extra = pullback_leg(rows, line, last - b)
                if extra is None or extra['ext'] < TL_EXT:
                    continue
            else:
                if min(closes[i] / line[i] for i in range(a, e + 1)) > 1 - TL_EXT:
                    continue
                recent = range(max(e + 1, last - TL_RECENT + 1), last + 1)
                extra = {'cr': [closes[i] / line[i] for i in recent], 'lr': [rows[i][3] / line[i] for i in recent]}
            return {'v': line[last], 's': s, 'a': rows[a][0], 'b': rows[b][0], 'e': rows[e][0], 't': len(touch), **extra}
    return None


def last_break(rows, window, back=BREAK_DAYS):
    """Phiên vượt trendline giảm gần nhất trong `back` phiên đã đóng: kẻ lại đường đúng như hôm đó app kẻ (chỉ dùng
    nến tới hết phiên liền trước) rồi xem phiên đó có vượt không. Trả {'k': số phiên trước (1 = phiên đóng gần nhất),
    'd': ngày, 'p': giá đóng cửa phiên vượt, 'r': đóng cửa / đường, 'vr': KL / KLTB 20} hoặc None."""
    for k in range(1, min(back, len(rows) - 1) + 1):
        past, bar = rows[:-k], rows[-k]
        td = trend_line(past, window, up=False)
        if not td or any(r >= 1 + BREAK_UP for r in td['cr']):
            continue
        v20 = _mean([r[5] for r in past[-20:]])
        r = bar[4] / (td['v'] + td['s'])
        if r >= 1 + BREAK_UP and bar[5] >= v20:
            return {'k': k, 'd': bar[0], 'p': bar[4], 'r': r, 'vr': bar[5] / v20 if v20 else None}
    return None


def _round(v):
    if isinstance(v, float):
        return round(v, 6)
    if isinstance(v, dict):
        return {k: _round(x) for k, x in v.items()}
    if isinstance(v, list):
        return [_round(x) for x in v]
    return v


def stats_from_bars(bars, today, date_of, history=False):
    """Toàn bộ số thống kê của 1 mã, tính trên các phiên đã đóng; None nếu quá ít nến.
    history=True: thêm quét lùi phiên vượt trendline giảm (nặng hơn — chỉ bật khi có tiêu chí dùng)."""
    rows = closed_bars(bars, today, date_of)
    if len(rows) < MIN_BARS:
        return None
    dates = [r[0] for r in rows]
    closes = [r[4] for r in rows]
    vols = [r[5] for r in rows]
    n = len(rows)
    out = {'n': n, 'ld': dates[-1], 'lc': closes[-1], 'lh': rows[-1][2], 'll': rows[-1][3]}

    for k in PRICE_AVG_N:
        out[f'p{k}'] = _mean(closes[-k:]) if n >= k else None    # chưa đủ phiên (vd SMA200 mã mới) → không tính
    for k in VOL_AVG_N:
        out[f'v{k}'] = _mean(vols[-k:])
    for k in (50, 100):
        out[f'v{k}'] = _mean(vols[-k:]) if n >= k else None
    out['gv20'] = _mean([r[4] * r[5] for r in rows[-20:]]) / 1e6       # GTTB 20 phiên, tỷ đồng (giá nghìn đồng)
    since3m = minus_period(today, 'm', 3)
    v3m = [v for d, v in zip(dates, vols) if d >= since3m]
    out['v3m'] = _mean(v3m) if v3m else None
    out['sd19'] = _std(closes[-19:])
    out['sd20'] = _std(closes[-20:])

    for k in EMA_N:
        out[f'e{k}'] = ema_last(closes, k) if n >= k else None
    # MACD: đường = EMA12 − EMA26, tín hiệu = EMA9 của đường MACD
    if n >= 35:
        e12, e26 = [], []
        a12, a26 = 2 / 13, 2 / 27
        x12 = x26 = closes[0]
        for c in closes[1:]:
            x12, x26 = a12 * c + (1 - a12) * x12, a26 * c + (1 - a26) * x26
            e12.append(x12)
            e26.append(x26)
        out['e12'], out['e26'] = e12[-1], e26[-1]
        out['sig'] = ema_last([a - b for a, b in zip(e12, e26)], 9)
    else:
        out['e12'] = out['e26'] = out['sig'] = None
    out['ag'], out['al'] = wilder_rsi_parts(closes)
    out['rs'] = [round(x, 4) for x in rsi_tail(closes)]
    out['pmf'], out['nmf'], out['mfi'], _ = money_flow(rows)

    # Parabolic SAR; Stochastic (%K thô / %K chậm 2 phiên cuối, %D phiên cuối, cao / thấp 13 phiên cuối)
    out['sart'], out['sar'], out['sep'], out['saf'] = parabolic_sar(rows)
    kr = [raw_k(rows, i) for i in range(n - 5, n)]
    ks = [None if None in kr[j:j + 3] else (kr[j] + kr[j + 1] + kr[j + 2]) / 3 for j in range(3)]
    out['skr'], out['sks'] = kr[-2:], ks[-2:]
    out['skd'] = None if None in ks else (ks[0] + ks[1] + ks[2]) / 3
    out['hh13'] = max(r[2] for r in rows[-(STOCH_N - 1):])
    out['ll13'] = min(r[3] for r in rows[-(STOCH_N - 1):])
    # CCI: giá điển hình 19 phiên cuối + CCI phiên cuối
    tps = [(h + lo + c) / 3 for _, _, h, lo, c, _ in rows]
    out['tp19'] = tps[-(CCI_N - 1):]
    out['cci'] = cci(tps[-CCI_N:])
    # ADX / DMI
    out['atr'], out['pdm'], out['mdm'], out['dxa'] = dmi_parts(rows) or (None, None, None, None)
    # OBV (cộng dồn từ phiên thứ 2) + tổng 19 / TB 20 phiên cuối
    obv, s = [], 0
    for p, r in zip(rows, rows[1:]):
        s += r[5] if r[4] > p[4] else (-r[5] if r[4] < p[4] else 0)
        obv.append(s)
    ok = len(obv) >= OBV_N
    out['obv'], out['ob19'], out['obm'] = (obv[-1], sum(obv[-(OBV_N - 1):]), sum(obv[-OBV_N:]) / OBV_N) if ok else (None,) * 3
    # Ichimoku: Tenkan / Kijun phiên cuối, cao / thấp 8 và 25 phiên cuối, mây hôm nay (ca) và hôm qua (cb)
    out['tk'], out['kj'] = mid_range(rows, n - 1, ICHI_T), mid_range(rows, n - 1, ICHI_K)
    for k in (ICHI_T - 1, ICHI_K - 1):
        out[f'ih{k}'], out[f'il{k}'] = max(r[2] for r in rows[-k:]), min(r[3] for r in rows[-k:])
    out['ca'], out['cb'] = ichimoku_lead(rows, n - ICHI_SHIFT), ichimoku_lead(rows, n - 1 - ICHI_SHIFT)

    # Đỉnh / đáy và giá mốc "1 tuần … 1 năm trước"
    for key, (kind, k) in PERIODS.items():
        since = minus_period(today, kind, k)
        win = [r for r in rows if r[0] >= since]
        out[f'hi{key}'] = max(r[2] for r in win) if win else None
        out[f'lo{key}'] = min(r[3] for r in win) if win else None
        ref = [c for d, c in zip(dates, closes) if d <= since]
        out[f'px{key}'] = ref[-1] if ref else None
    out['streak'] = streak(closes)

    # Pullback: SMA 10 phiên trước (độ dốc), nhịp tăng rồi điều chỉnh so với SMA; trendline tăng
    for k, (look, _) in PB_SMA.items():
        line = sma_series(closes, k)
        out[f'ps{k}'] = line[-1 - PB_SLOPE] if n >= k + PB_SLOPE else None
        out[f'pb{k}'] = pullback_leg(rows, line, look) if n >= k + look else None
    for key, w in TL_WINDOWS.items():
        out[f'tl{key}'] = trend_line(rows, w)
        out[f'td{key}'] = trend_line(rows, w, up=False)
        if history:
            out[f'tb{key}'] = last_break(rows, w)
    return _round(out)


# ── Nến 15 phút ─────────────────────────────────────────────────────────

def intraday_cutoff(now):
    """Giờ mở nến 15 phút đang chạy lúc `now` (datetime giờ VN): nến từ giờ này trở đi chưa chốt.
    None = ngoài giờ khớp lệnh (nghỉ trưa, sau giờ, trước giờ mở cửa, cuối tuần) — mọi nến đã chốt."""
    if now.weekday() >= 5:
        return None
    m = now.hour * 60 + now.minute
    for a, b in INTRA_SESSIONS:
        if a <= m < b:
            m -= m % INTRA_MIN
            return now.replace(hour=m // 60, minute=m % 60, second=0, microsecond=0)
    return None


def intraday_key(now):
    """Mốc của bộ nến 15 phút dùng được lúc `now`: giờ mở nến đang chạy; ngoài giờ là giờ hết buổi vừa xong
    (11:30 / 15:00; trước giờ mở cửa, cuối tuần: 00:00). Sang mốc mới = vừa có nến chốt → tải lại."""
    cut = intraday_cutoff(now)
    if cut is None:
        m = now.hour * 60 + now.minute
        ends = [b for _, b in INTRA_SESSIONS if b <= m] if now.weekday() < 5 else []
        m = ends[-1] if ends else 0
        cut = now.replace(hour=m // 60, minute=m % 60, second=0, microsecond=0)
    return cut.strftime('%Y-%m-%d %H:%M')


def intraday_stats(bars, cutoff=None):
    """Số thống kê khung 15 phút của 1 mã tại nến đã chốt gần nhất — nến có giờ mở < cutoff (giây Unix; None = mọi nến).
    None nếu quá ít nến."""
    rows = closed_bars(bars, math.inf if cutoff is None else cutoff, lambda t: t)     # 'ngày' ở đây là giây Unix
    if len(rows) < INTRA_MIN_BARS:
        return None
    closes = [r[4] for r in rows]
    return _round({'n': len(rows), 'lt': rows[-1][0], 'lc': closes[-1], 'p10': _mean(closes[-10:]),
                   'rs': [round(x, 4) for x in rsi_tail(closes)]})


# ── Khối lượng dự kiến cả phiên ─────────────────────────────────────────
# Chép cách FireAnt đổi giờ hiện tại → số phút ĐÃ giao dịch (trừ nghỉ trưa), rồi ngoại suy tuyến tính.

def session_minutes(exchange):
    """Tổng số phút giao dịch của cả phiên."""
    return 270 if exchange in ('HNX', 'UPCOM') else 255


def elapsed_minutes(now, exchange):
    """Số phút giao dịch đã trôi qua tại `now` (datetime giờ VN) — 0 khi chưa mở cửa."""
    start = now.replace(hour=9, minute=0, second=0, microsecond=0)
    r = math.ceil((now - start).total_seconds() / 60)
    if r > 360:                      # sau giờ đóng cửa
        return session_minutes(exchange)
    if r > 345:
        return r - 90 if exchange in ('HNX', 'UPCOM') else 255
    if r > 330:
        return r - 90 if exchange == 'UPCOM' else 240
    if r > 240:                      # buổi chiều
        return r - 90
    if r > 150:                      # nghỉ trưa 11:30–13:00
        return 150
    return max(r, 0)


def estimated_volume(total_volume, exchange, now):
    """KL cả phiên ước tính theo tốc độ khớp từ đầu phiên; None nếu chưa có phút nào."""
    m = elapsed_minutes(now, exchange)
    if not total_volume or m <= 0:
        return None
    return total_volume * session_minutes(exchange) / m
