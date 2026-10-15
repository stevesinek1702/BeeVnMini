"""
Chỉ báo kỹ thuật tính từ nến ngày — dữ liệu nền cho các điều kiện lọc kiểu FireAnt Screener
(RSI, MFI, MACD, Bollinger, giá cắt SMA/EMA, vượt đỉnh / thủng đáy, số phiên tăng giảm liên tục…).

Mọi con số tính trên các phiên ĐÃ ĐÓNG (bỏ nến hôm nay) — đúng cách bảng thống kê của FireAnt đưa ra;
điều kiện lọc (conditions.py) rồi ghép giá hiện tại vào để biết "hôm nay có cắt lên / cắt xuống không".
Giá tính bằng nghìn đồng như cột Giá của bảng; khối lượng bằng cổ phiếu.
Không dính giao diện, không dính mạng (lấy nến nằm ở core.py) nên test được.
"""
import calendar
import math

# Cửa sổ trung bình mà các điều kiện cần (số phiên): giá đóng cửa, khối lượng.
PRICE_AVG_N = (4, 5, 9, 10, 14, 15, 19, 20, 44, 45)
VOL_AVG_N = (4, 5, 9, 10, 14, 19, 20, 44)
EMA_N = (5, 10, 15, 20, 45)
# Các mốc "1 tuần … 1 năm": tính theo lịch (ngày hoặc tháng) lùi từ hôm nay.
PERIODS = {'1w': ('d', 7), '2w': ('d', 14), '1m': ('m', 1), '3m': ('m', 3), '6m': ('m', 6), '1y': ('m', 12)}
MIN_BARS = 20      # ít hơn chừng này phiên (mã mới niêm yết) thì chưa tính — thà thiếu còn hơn sai


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


def stats_from_bars(bars, today, date_of):
    """Toàn bộ số thống kê của 1 mã, tính trên các phiên đã đóng; None nếu quá ít nến."""
    rows = closed_bars(bars, today, date_of)
    if len(rows) < MIN_BARS:
        return None
    dates = [r[0] for r in rows]
    closes = [r[4] for r in rows]
    vols = [r[5] for r in rows]
    n = len(rows)
    out = {'n': n, 'ld': dates[-1], 'lc': closes[-1], 'lh': rows[-1][2], 'll': rows[-1][3]}

    for k in PRICE_AVG_N:
        out[f'p{k}'] = _mean(closes[-k:])
    for k in VOL_AVG_N:
        out[f'v{k}'] = _mean(vols[-k:])
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
    out['pmf'], out['nmf'], out['mfi'], _ = money_flow(rows)

    # Đỉnh / đáy và giá mốc "1 tuần … 1 năm trước"
    for key, (kind, k) in PERIODS.items():
        since = minus_period(today, kind, k)
        win = [r for r in rows if r[0] >= since]
        out[f'hi{key}'] = max(r[2] for r in win) if win else None
        out[f'lo{key}'] = min(r[3] for r in win) if win else None
        ref = [c for d, c in zip(dates, closes) if d <= since]
        out[f'px{key}'] = ref[-1] if ref else None
    out['streak'] = streak(closes)
    return {k: (round(v, 6) if isinstance(v, float) else v) for k, v in out.items()}


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
