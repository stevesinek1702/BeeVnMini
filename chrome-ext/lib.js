// Lấy dữ liệu + định dạng + bảng nhỏ. Chép tối thiểu từ core.py (fetch_quotes, transform_quote,
// hist_stats, format_*) để thử; logic lọc chưa chuyển.
const QUOTES_URL = 'https://www.fireant.vn/api/Data/Markets/Quotes?symbols=';
const HISTORY_URL = 'https://dchart-api.vndirect.com.vn/dchart/history?resolution=D';
const VN_OFFSET = 7 * 3600;

// Không đặt được User-Agent trong fetch (header cấm) — Chrome tự gửi UA của nó.
// host_permissions trong manifest cho phép gọi chéo nguồn mà không vướng CORS.
async function fetchQuotes(symbols) {
  const res = await fetch(QUOTES_URL + symbols.join(','), {
    headers: { Accept: 'application/json' }, cache: 'no-store' });
  if (!res.ok) throw new Error(`FireAnt trả HTTP ${res.status}`);
  const data = await res.json();
  if (!Array.isArray(data)) throw new Error('FireAnt trả dữ liệu lạ');
  return data;
}

function vnDate(ts) {
  return new Date((ts + VN_OFFSET) * 1000).toISOString().slice(0, 10);
}

// Nến ngày VNDirect → KL trung bình 45 phiên đã đóng (bỏ nến hôm nay), như core.hist_stats.
// Accept mặc định của fetch là */* — dchart trả 406 nếu hỏi đích danh application/json.
async function fetchHistory(symbol) {
  const to = Math.floor(Date.now() / 1000), frm = to - 100 * 86400;
  const res = await fetch(`${HISTORY_URL}&symbol=${symbol}&from=${frm}&to=${to}`, { cache: 'no-store' });
  if (!res.ok) throw new Error(`VNDirect trả HTTP ${res.status}`);
  const bars = await res.json();
  if (!bars || bars.s !== 'ok' || !Array.isArray(bars.t)) return null;
  const today = vnDate(to);
  const closes = [], vols = [];
  bars.t.forEach((t, i) => {
    if (vnDate(t) < today) { closes.push(bars.c[i]); vols.push(bars.v[i]); }
  });
  const avg = (a, n) => (a.length < n ? null : a.slice(-n).reduce((x, y) => x + y, 0) / n);
  const av = avg(vols, 45);
  return { bars: bars.t.length, lastClose: closes.at(-1), ma20: avg(closes, 20),
           avgVol: av == null ? 0 : Math.round(av) };
}

function transformQuote(q, hist) {
  const k = (v) => (v == null ? null : v / 1000);
  const cur = q.PriceCurrent, top = q.PriceCeiling, bottom = q.PriceFloor;
  const vol = q.TotalVolume || 0;
  return {
    symbol: q.Symbol,
    price: k(cur),
    change: k(q.PriceChange) || 0,
    changePercent: q.PricePercentChange ? q.PricePercentChange * 100 : 0,
    volume: q.TotalVolume,
    volRatio: hist && hist.avgVol ? Math.round(vol / hist.avgVol * 100) : null,
    limit: cur && top && cur >= top ? 'ceil' : (cur && bottom && cur <= bottom ? 'floor' : null),
  };
}

// ── Định dạng (giống core.format_*) ──────────────────────────────────────
function formatPrice(p) {
  if (p == null || Number.isNaN(p)) return '--';
  if (p === 0) return '0';
  const s = p.toFixed(1);
  return s.endsWith('.0') ? s.slice(0, -2) : s;
}

function formatVolume(v) {
  if (v == null) return '--';
  if (v >= 1e9) return (v / 1e9).toFixed(1) + 'B';
  if (v >= 1e6) return (v / 1e6).toFixed(1) + 'M';
  if (v >= 1e3) return (v / 1e3).toFixed(1) + 'K';
  return String(Math.trunc(v));
}

// (chữ, tông màu) cho từng ô — trần tím, sàn xanh lơ đè lên màu tăng / giảm
function formatCell(s, key) {
  const tone = s.limit || (s.change > 0 ? 'up' : (s.change < 0 ? 'down' : 'flat'));
  const plus = s.change > 0 ? '+' : '';
  switch (key) {
    case 'symbol': return [s.symbol, tone];
    case 'price': return [formatPrice(s.price), tone];
    case 'changePercent': return [plus + s.changePercent.toFixed(2) + '%', tone];
    case 'volume': return [formatVolume(s.volume), ''];
    case 'volRatio':
      if (s.volRatio == null) return ['--', 'muted'];
      return [s.volRatio + '%', s.volRatio > 100 ? 'up' : (s.volRatio < 100 ? 'down' : '')];
  }
  return ['', ''];
}

const COLUMNS = [['symbol', 'Mã'], ['price', 'Giá'], ['changePercent', '%'],
                 ['volume', 'KLGD'], ['volRatio', '%KL/TB']];

// Màu lấy đúng bảng màu beevn_mini.pyw (BG, HEAD, LINE, ALT, TEXT, MUTED, GOLD, TONE)
const BOARD_CSS = `
:root { color-scheme: dark; }
html, body { margin: 0; background: #141428; color: #e6e6f0;
  font: 13px "Segoe UI", system-ui, sans-serif; }
.bee-head { display: flex; align-items: center; gap: 6px; background: #1c1c38;
  padding: 3px 8px; font-size: 12px; white-space: nowrap; }
.bee-head b { color: #fbbf24; } .bee-head .dot { color: #e6e6f0; font-weight: normal; }
.bee-head .meta { color: #8a8aa8; margin-left: auto; font-variant-numeric: tabular-nums; }
.bee-head .meta.stale { color: #eab308; }
table.bee { width: 100%; border-collapse: collapse; font-variant-numeric: tabular-nums; }
table.bee th { color: #8a8aa8; font: bold 11px "Segoe UI", sans-serif; text-align: right;
  padding: 2px 8px; border-bottom: 1px solid #2a2a4a; }
table.bee td { text-align: right; padding: 2px 8px; height: 18px; }
table.bee th:first-child, table.bee td:first-child { text-align: left; font-weight: bold; }
table.bee tr:nth-child(even) td { background: #191934; }
.up { color: #22c55e; } .down { color: #ef4444; } .flat { color: #eab308; }
.ceil { color: #c084fc; } .floor { color: #22d3ee; } .muted { color: #8a8aa8; }
.bee-foot { color: #8a8aa8; font-size: 10px; padding: 2px 8px; }
`;

// Bảng dựng MỘT lần cho danh sách mã; mỗi lần cập nhật chỉ đổi textContent / className
// của ô nào thật sự khác → không dựng lại DOM, không nhấp nháy.
class MiniBoard {
  constructor(doc, symbols, opts = {}) {
    this.doc = doc;
    this.cells = new Map();
    this.builds = 0;
    this.cellWrites = 0;
    this.build(symbols, opts.foot);
  }

  build(symbols, foot) {
    const d = this.doc;
    this.builds++;
    this.root = d.createElement('div');
    this.root.innerHTML =
      '<div class="bee-head"><b>Bee</b><span class="dot">.vn</span><span class="meta">đang tải…</span></div>' +
      '<table class="bee"><thead><tr>' + COLUMNS.map(([, h]) => `<th>${h}</th>`).join('') +
      '</tr></thead><tbody></tbody></table>' + (foot ? '<div class="bee-foot"></div>' : '');
    this.meta = this.root.querySelector('.meta');
    this.foot = this.root.querySelector('.bee-foot');
    const tbody = this.root.querySelector('tbody');
    for (const sym of symbols) {
      const tr = d.createElement('tr');
      const row = {};
      for (const [key] of COLUMNS) {
        const td = d.createElement('td');
        td.textContent = key === 'symbol' ? sym : '';
        tr.appendChild(td);
        row[key] = td;
      }
      tbody.appendChild(tr);
      this.cells.set(sym, row);
    }
  }

  update(rows, metaText, stale) {
    for (const s of rows) {
      const row = this.cells.get(s.symbol);
      if (!row) continue;
      for (const [key] of COLUMNS) {
        const [text, tone] = formatCell(s, key);
        const td = row[key];
        if (td.textContent !== text) { td.textContent = text; this.cellWrites++; }
        if (td.className !== tone) td.className = tone;
      }
    }
    this.meta.textContent = metaText;
    this.meta.classList.toggle('stale', !!stale);
    if (this.foot) {
      this.foot.textContent = `dựng bảng ${this.builds} lần · đã đổi ${this.cellWrites} ô`;
    }
  }
}
