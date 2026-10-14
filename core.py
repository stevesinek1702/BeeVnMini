"""
Phần lõi của Bee.vn mini — không dính giao diện, để test được.

Nguồn dữ liệu:
  - Giá trong phiên: FireAnt /api/Data/Markets/Quotes — công khai, không cần đăng nhập.
  - MA10/20/45 + KL trung bình 45 phiên, ưu tiên:
      1. FireAnt /Markets/TradingStatistic bằng cookie đọc từ ô D2 sheet Dashboard của anh Si
         (cùng cách web Bee.vn làm → số khớp y hệt web);
      2. cookie hết hạn → tự tính từ nến ngày VNDirect dchart, trên phiên ĐÃ ĐÓNG.

Lọc / sắp xếp / định dạng giữ y như bảng giá Bee.vn để số hiện ra giống hệt web.
"""
import json
import math
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP

QUOTES_URL = 'https://www.fireant.vn/api/Data/Markets/Quotes?symbols='
TRADING_STAT_URL = 'https://www.fireant.vn/api/Data/Markets/TradingStatistic'
# Ô D2 sheet "Dashboard" — nơi cookie FireAnt được làm mới tự động. Đọc dạng CSV (sheet chia sẻ bằng link).
COOKIE_SHEET_ID = '1IaSyUm5opJttxGgJa_4ucDSWEzEJQYaTFVTwYtBiH9c'
COOKIE_SHEET_URL = ('https://docs.google.com/spreadsheets/d/{id}/gviz/tq?tqx=out:csv&sheet=Dashboard&range=D2')
# TradingStatistic chỉ chịu đúng bộ header này (lấy từ Excel M code / server Bee.vn)
STAT_UA = ('Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 '
           '(KHTML, like Gecko) Chrome/107.0.0.0 Mobile Safari/537.36')
HISTORY_URL = 'https://dchart-api.vndirect.com.vn/dchart/history?resolution=D'
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36'

# FireAnt cắt bớt kết quả khi hỏi quá nhiều mã một lần (400 mã chỉ về ~60%) → 100 mã/lượt.
QUOTE_BATCH = 100
QUOTE_WORKERS = 4
HIST_WORKERS = 8

# Cùng ngưỡng lọc nhiễu với cột "Lực cầu" của Bee.vn.
LIQUIDITY_MIN_VALUE = 100_000_000
LIQUIDITY_MIN_VOLUME = 30_000
LUC_CAU_MAX = 80

VN_TZ = timezone(timedelta(hours=7))
EXCHANGE_KEY = {'HOSTC': 'HSX', 'HASTC': 'HNX', 'UPCOM': 'UPCOM', 'UPCoM': 'UPCOM'}
EXCHANGES = ['HSX', 'HNX', 'UPCOM']

# Cùng thứ tự cột với bảng giá trên web.
COLUMNS = [
    ('symbol', 'Mã CP'),
    ('price', 'Giá'),
    ('change', 'Thay đổi'),
    ('changePercent', '% Thay đổi'),
    ('volume', 'KLGD'),
    ('volRatio', '% KL/TB'),
    ('value', 'GTGD'),
    ('ma10', 'MA10'),
    ('ma20', 'MA20'),
    ('ma45', 'MA45'),
    ('demandStrength', 'Lực cầu'),
]
LABEL = dict(COLUMNS)
FILTERABLE = [c for c in COLUMNS if c[0] != 'symbol']
OPS = {'gt': '>', 'lt': '<', 'eq': '='}


# ── Thời gian ───────────────────────────────────────────────────────────

def vn_now(ts=None):
    return datetime.fromtimestamp(time.time() if ts is None else ts, VN_TZ)


def vn_date(ts):
    return vn_now(ts).strftime('%Y-%m-%d')


def is_trading_time(ts=None):
    """Giờ giao dịch HOSE/HNX theo giờ Việt Nam, đệm 15 phút hai đầu."""
    d = vn_now(ts)
    if d.weekday() >= 5:
        return False
    m = d.hour * 60 + d.minute
    return 8 * 60 + 45 <= m <= 15 * 60 + 15


# ── Lấy dữ liệu ─────────────────────────────────────────────────────────

def _get_json(url, timeout=20, accept='application/json'):
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': accept})
    with urllib.request.urlopen(req, timeout=timeout) as res:
        body = res.read()
    try:
        return json.loads(body.decode('utf-8'))
    except ValueError:
        return None


def fetch_quotes(symbols):
    batches = [symbols[i:i + QUOTE_BATCH] for i in range(0, len(symbols), QUOTE_BATCH)]

    def one(batch):
        try:
            data = _get_json(QUOTES_URL + ','.join(batch))
            return data if isinstance(data, list) else []
        except Exception:
            return None

    with ThreadPoolExecutor(QUOTE_WORKERS) as ex:
        parts = list(ex.map(one, batches))
    if all(p is None for p in parts):
        raise RuntimeError('Không lấy được giá từ FireAnt')
    return [q for p in parts if p for q in p]


class CookieExpired(Exception):
    """Cookie FireAnt hết hạn / sai → FireAnt đẩy về trang đăng nhập."""


def fetch_fireant_cookie(sheet_id=COOKIE_SHEET_ID):
    """Đọc cookie từ ô D2. Trả None nếu ô trống / không phải cookie FireAnt."""
    import csv
    import io
    req = urllib.request.Request(COOKIE_SHEET_URL.format(id=sheet_id), headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=20) as res:
        text = res.read().decode('utf-8', errors='replace')
    rows = list(csv.reader(io.StringIO(text)))
    val = rows[0][0].strip() if rows and rows[0] else ''
    return val if 'FireAnt.Authentication' in val else None


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


def parse_trading_stats(data):
    """Đổi phản hồi TradingStatistic sang {mã: {ma10, ma20, ma45, avgVol}} — y cách server Bee.vn đọc."""
    if not isinstance(data, list) or not data:
        raise CookieExpired('TradingStatistic không trả danh sách')
    out = {}
    for it in data:
        sym = it.get('Symbol')
        if not sym:
            continue

        def ma(k):
            v = it.get(k)
            return float(_fixed(v / 1000, 2)) if v else None
        out[sym] = {
            'ma10': ma('AvgPrice10d'), 'ma20': ma('AvgPrice20d'), 'ma45': ma('AvgPrice45d'),
            'avgVol': it.get('AvgVolume45d') or it.get('AvgVol45') or it.get('AvgVolume') or 0,
        }
    return out


def fetch_trading_stats(cookie):
    req = urllib.request.Request(TRADING_STAT_URL, headers={
        'Cookie': cookie, 'User-Agent': STAT_UA, 'Accept-Language': 'en-US,en;q=0.9,vi;q=0.8'})
    opener = urllib.request.build_opener(_NoRedirect)
    try:
        with opener.open(req, timeout=60) as res:
            body = res.read()
    except urllib.error.HTTPError as e:
        if e.code in (301, 302, 401, 403):
            raise CookieExpired(f'FireAnt trả {e.code}')
        raise
    try:
        data = json.loads(body.decode('utf-8'))
    except ValueError:
        raise CookieExpired('FireAnt trả trang HTML (chưa đăng nhập)')
    return parse_trading_stats(data)


def hist_stats(bars, today):
    """MA + KL trung bình trên các phiên đã đóng — bỏ nến hôm nay (phiên đang chạy, chưa chốt)."""
    if not isinstance(bars, dict) or bars.get('s') != 'ok' or not isinstance(bars.get('t'), list):
        return None
    closes, vols = [], []
    for t, c, v in zip(bars['t'], bars['c'], bars['v']):
        if vn_date(t) >= today:
            continue
        closes.append(c)
        vols.append(v)

    def avg(arr, n):
        return None if len(arr) < n else sum(arr[-n:]) / n

    def ma(n):
        v = avg(closes, n)
        return None if v is None else float(_fixed(v, 2))

    av = avg(vols, 45)
    return {'ma10': ma(10), 'ma20': ma(20), 'ma45': ma(45), 'avgVol': 0 if av is None else round(av)}


def fetch_history(symbol, today):
    to = int(time.time())
    frm = to - 100 * 86400   # ~70 phiên, dư cho 45 phiên kể cả nghỉ lễ
    # dchart trả 406 nếu hỏi đích danh application/json
    return hist_stats(_get_json(f'{HISTORY_URL}&symbol={symbol}&from={frm}&to={to}', accept='*/*'), today)


def fetch_all_history(symbols, today, done=None, on_progress=None):
    """Lấy lịch sử cho các mã còn thiếu. Mã không có dữ liệu → {} để khỏi thử lại mãi;
    lỗi mạng → bỏ trống, lần sau thử lại."""
    done = dict(done or {})
    todo = [s for s in symbols if s not in done]

    def one(sym):
        try:
            return sym, (fetch_history(sym, today) or {})
        except Exception:
            return sym, None

    with ThreadPoolExecutor(HIST_WORKERS) as ex:
        for i, (sym, stats) in enumerate(ex.map(one, todo), 1):
            if stats is not None:
                done[sym] = stats
            if on_progress and i % 50 == 0:
                on_progress(len(done) / len(symbols))
    return done


# ── Đổi sang hàng bảng giá ──────────────────────────────────────────────

def luc_cau(q):
    """Lực cầu theo giá trị — chép công thức computeLucCauByValue của Bee.vn."""
    tv = q.get('TotalValue') or 0
    vol = q.get('TotalVolume') or 0
    if tv < LIQUIDITY_MIN_VALUE or vol < LIQUIDITY_MIN_VOLUME:
        return None
    lc = round((q.get('TotalActiveBuyVolume') or 0) * (q.get('PriceAverage') or 0) / tv * 1000) / 10
    return None if lc > LUC_CAU_MAX else lc


def transform_quote(q, hist=None):
    h = hist or {}
    vol = q.get('TotalVolume') or 0

    def k(v):
        return None if v is None else float(_fixed(v / 1000, 2))

    pct = q.get('PricePercentChange')
    tv = q.get('TotalValue')
    return {
        'symbol': q.get('Symbol'),
        'name': q.get('Name') or '',
        'exchange': EXCHANGE_KEY.get(q.get('Exchange'), q.get('Exchange')),
        'price': k(q.get('PriceCurrent')),
        'change': k(q.get('PriceChange')),
        'changePercent': float(_fixed(pct * 100, 2)) if pct else 0,
        'volume': q.get('TotalVolume'),
        'value': round(tv / 1e9 * 10) / 10 if tv else 0,
        # Chưa có KL trung bình (lịch sử đang tải / mã mới) → None, hiện "--" thay vì "0%" đỏ gây hiểu lầm
        'volRatio': round(vol / h['avgVol'] * 100) if h.get('avgVol') else None,
        'ma10': h.get('ma10'),
        'ma20': h.get('ma20'),
        'ma45': h.get('ma45'),
        'demandStrength': luc_cau(q),
    }


def group_by_exchange(rows):
    out = {ex: [] for ex in EXCHANGES}
    for r in rows:
        if r.get('symbol') and r.get('exchange') in out:
            out[r['exchange']].append(r)
    return out


# ── Lọc / sắp xếp (giống bảng giá web) ──────────────────────────────────

def _num(v):
    try:
        f = float(v)
        return None if math.isnan(f) else f
    except (TypeError, ValueError):
        return None


def active_filter_keys(filters):
    return [k for k, f in (filters or {}).items() if f and _num(f.get('value')) is not None]


def apply_filters(stocks, filters):
    out = stocks
    for key in active_filter_keys(filters):
        f = filters[key]
        val = _num(f['value'])
        op = f.get('operator')

        def ok(s):
            v = _num(s.get(key) or 0) or 0.0
            if op == 'gt':
                return v > val
            if op == 'lt':
                return v < val
            if op == 'eq':
                return v == val
            return True
        out = [s for s in out if ok(s)]
    return out


def sort_stocks(stocks, column, direction):
    asc = direction == 'asc'
    empty = math.inf if asc else -math.inf
    if column == 'symbol':
        return sorted(stocks, key=lambda s: str(s.get('symbol') or ''), reverse=not asc)
    return sorted(stocks, key=lambda s: empty if s.get(column) is None else s.get(column), reverse=not asc)


def select_matches(all_stocks, cfg):
    ex = cfg.get('exchange', 'HSX')
    pool = [s for e in EXCHANGES for s in all_stocks.get(e, [])] if ex == 'ALL' else all_stocks.get(ex, [])
    return sort_stocks(apply_filters(pool, cfg.get('filters')),
                       cfg.get('sortColumn') or 'value', cfg.get('sortDirection') or 'desc')


def compact_columns(filters):
    """Chế độ thu gọn: Mã CP + các cột đang bị lọc, theo thứ tự bảng giá."""
    active = set(active_filter_keys(filters))
    return [c for c in COLUMNS if c[0] == 'symbol' or c[0] in active]


EXCHANGE_COL = ('exchange', 'Sàn')
EXCHANGE_SHORT = {'HSX': 'HSX', 'HNX': 'HNX', 'UPCOM': 'UpCom'}


def table_columns(cfg, full):
    """Cột hiện ra. Lọc cả 3 sàn thì thêm cột Sàn ngay sau Mã CP để biết mã nào sàn nào."""
    cols = list(COLUMNS) if full else compact_columns(cfg.get('filters'))
    if cfg.get('exchange') == 'ALL':
        cols.insert(1, EXCHANGE_COL)
    return cols


def describe_filters(filters):
    return ' · '.join(f"{LABEL.get(k, k)} {OPS.get(filters[k].get('operator'), '?')} {js_num(filters[k]['value'])}"
                      for k in active_filter_keys(filters))


# ── Định dạng (giống web) ───────────────────────────────────────────────

def _fixed(x, digits):
    """Giống Number.toFixed của JavaScript (làm tròn nửa lên trên giá trị nhị phân thật)."""
    q = Decimal(1).scaleb(-digits)
    return str(Decimal(x).quantize(q, rounding=ROUND_HALF_UP))


def js_num(v):
    """In số như String(v) của JavaScript: 11.0 → '11', 13.5 → '13.5'."""
    f = float(v)
    return str(int(f)) if f.is_integer() else repr(f)


def format_price(p):
    if p is None or (isinstance(p, float) and math.isnan(p)):
        return '--'
    if p == 0:
        return '0'
    s = _fixed(p, 1)
    return s[:-2] if s.endswith('.0') else s


def format_volume(v):
    if v is None:
        return '--'
    if v >= 1e9:
        return _fixed(v / 1e9, 1) + 'B'
    if v >= 1e6:
        return _fixed(v / 1e6, 1) + 'M'
    if v >= 1e3:
        return _fixed(v / 1e3, 1) + 'K'
    return str(int(v))


def format_cell(s, key):
    """Trả (chữ, tông màu) — tông: 'up' | 'down' | 'flat' | 'muted' | ''."""
    change = s.get('change') or 0
    tone = 'up' if change > 0 else ('down' if change < 0 else 'flat')
    plus = '+' if change > 0 else ''
    if key == 'symbol':
        return s.get('symbol') or '', 'sym'
    if key == 'exchange':
        return EXCHANGE_SHORT.get(s.get('exchange'), s.get('exchange') or ''), 'muted'
    if key == 'price':
        return format_price(s.get('price')), tone
    if key == 'change':
        return plus + format_price(change), tone
    if key == 'changePercent':
        return plus + _fixed(s.get('changePercent') or 0, 2) + '%', tone
    if key == 'volume':
        return format_volume(s.get('volume')), ''
    if key == 'volRatio':
        r = s.get('volRatio')
        if r is None:
            return '--', 'muted'
        return f'{r}%', ('up' if r > 100 else ('down' if r < 100 else ''))
    if key == 'value':
        v = s.get('value')
        return (_fixed(v, 1) if v else '--') + ' tỷ', ''
    if key in ('ma10', 'ma20', 'ma45'):
        v = s.get(key)
        return (js_num(v) if v else '--'), ''
    if key == 'demandStrength':
        d = s.get('demandStrength')
        if d is None:
            return '—', 'muted'
        txt = js_num(d) + '%'
        return txt, ('up' if d > 50 else ('down' if d < 50 else 'flat'))
    return str(s.get(key, '')), ''
