// Phần lõi — chép từ core.py: đổi quote FireAnt sang hàng bảng giá, lọc / sắp xếp / định dạng giống bảng giá
// Bee.vn, danh sách tiêu chí. Không dính giao diện / mạng (lấy dữ liệu nằm ở data.js) nên test được bằng Node.
import * as conditions from './conditions.js';
import * as tech from './tech.js';
import { fixed, jsNum, pyRound, isum, fsum } from './pyfloat.js';

// Cùng ngưỡng lọc nhiễu với cột "Lực cầu" của Bee.vn.
export const LIQUIDITY_MIN_VALUE = 100_000_000;
export const LIQUIDITY_MIN_VOLUME = 30_000;
export const LUC_CAU_MAX = 80;

export const EXCHANGE_KEY = { HOSTC: 'HSX', HASTC: 'HNX', UPCOM: 'UPCOM', UPCoM: 'UPCOM' };
export const EXCHANGES = ['HSX', 'HNX', 'UPCOM'];

export const COLUMNS = [
  ['symbol', 'Mã CP'],
  ['price', 'Giá'],
  ['change', 'Thay đổi'],
  ['changePercent', '% Thay đổi'],
  ['volume', 'KLGD'],
  ['volRatio', '% KL/TB'],
  ['value', 'GTGD'],
  ['ma10', 'MA10'],
  ['ma20', 'MA20'],
  ['ma45', 'MA45'],
  ['demandStrength', 'Lực cầu'],
];
export const LABEL = { ...Object.fromEntries(COLUMNS), ...conditions.METRIC_LABEL };
export const HEAD_LABEL = { ...LABEL, changePercent: '%', ...conditions.METRIC_HEAD };
export const FILTERABLE = COLUMNS.filter((c) => c[0] !== 'symbol');
export const OPS = { gt: '>', lt: '<', eq: '=', ge: '≥', le: '≤' };    // + 'bt' (trong khoảng value..value2)
export const LEGACY_KEYS = new Set(FILTERABLE.map((c) => c[0]));

// ── Thời gian (giờ Việt Nam) ────────────────────────────────────────────
const VN_MS = 7 * 3600000;

// ts tính bằng giây (như time.time() của Python)
export function vnDate(ts) {
  return new Date(ts * 1000 + VN_MS).toISOString().slice(0, 10);
}

export function vnClock(ms = Date.now()) {
  return new Date(ms + VN_MS).toISOString().slice(11, 19);
}

// Giờ giao dịch HOSE/HNX theo giờ Việt Nam, đệm 15 phút hai đầu.
export function isTradingTime(ts = Date.now() / 1000) {
  const d = new Date(ts * 1000 + VN_MS);
  const wd = d.getUTCDay();
  if (wd === 0 || wd === 6) return false;
  const m = d.getUTCHours() * 60 + d.getUTCMinutes();
  return 8 * 60 + 45 <= m && m <= 15 * 60 + 15;
}

// MA + KL trung bình trên các phiên đã đóng — bỏ nến hôm nay
export function histStats(bars, today) {
  if (!bars || typeof bars !== 'object' || bars.s !== 'ok' || !Array.isArray(bars.t)) return null;
  const closes = [], vols = [];
  const n = Math.min(bars.t.length, (bars.c || []).length, (bars.v || []).length);
  for (let i = 0; i < n; i++) {
    if (vnDate(bars.t[i]) >= today) continue;
    closes.push(bars.c[i]);
    vols.push(bars.v[i]);
  }
  const ma = (k) => {
    if (closes.length < k) return null;
    return Number(fixed(fsum(closes.slice(-k)) / k, 2));
  };
  const av = vols.length < 45 ? null : isum(vols.slice(-45)) / 45;
  return { ma10: ma(10), ma20: ma(20), ma45: ma(45), avgVol: av === null ? 0 : pyRound(av) };
}

// ── Đổi sang hàng bảng giá ──────────────────────────────────────────────

// Lực cầu theo giá trị — công thức computeLucCauByValue của Bee.vn
export function lucCau(q) {
  const tv = q.TotalValue || 0;
  const vol = q.TotalVolume || 0;
  if (tv < LIQUIDITY_MIN_VALUE || vol < LIQUIDITY_MIN_VOLUME) return null;
  const lc = pyRound((q.TotalActiveBuyVolume || 0) * (q.PriceAverage || 0) / tv * 1000) / 10;
  return lc > LUC_CAU_MAX ? null : lc;
}

// Ngày (giờ VN) của quote FireAnt — trường Date là giờ UTC dạng ISO; null nếu thiếu / lạ
export function quoteVnDate(q) {
  const raw = q.Date;
  if (typeof raw !== 'string' || !/^\d{4}-\d{2}-\d{2}/.test(raw)) return null;
  if (raw.length === 10) return raw;
  const iso = /[zZ]|[+-]\d{2}:?\d{2}$/.test(raw.slice(10)) ? raw : raw + 'Z';
  const ms = Date.parse(iso);
  return Number.isNaN(ms) ? null : new Date(ms + VN_MS).toISOString().slice(0, 10);
}

// Quote FireAnt → hàng bảng giá. hist = MA / KL trung bình; techStats = thống kê kỹ thuật của mã; nowMs = giờ hiện tại;
// intra = {'15m': thống kê nến 15 phút} (chỉ khi có tiêu chí dùng khung 15 phút).
// Hàng mang thêm _tech / _live để các điều kiện tín hiệu tính; hai khoá này không hiện ra bảng.
export function transformQuote(q, hist = null, techStats = null, nowMs = Date.now(), intra = null) {
  const h = hist || {};
  const vol = q.TotalVolume || 0;
  const k = (v) => (v === null || v === undefined ? null : Number(fixed(v / 1000, 2)));
  const pct = q.PricePercentChange;
  const tv = q.TotalValue;
  const exchange = EXCHANGE_KEY[q.Exchange] ?? q.Exchange;
  const price = k(q.PriceCurrent), change = k(q.PriceChange);
  const row = {
    symbol: q.Symbol,
    name: q.Name || '',
    exchange,
    price,
    change,
    changePercent: pct ? Number(fixed(pct * 100, 2)) : 0,
    volume: q.TotalVolume,
    value: tv ? pyRound(tv / 1e9 * 10) / 10 : 0,
    volRatio: h.avgVol ? pyRound(vol / h.avgVol * 100) : null,
    ma10: h.ma10 ?? null,
    ma20: h.ma20 ?? null,
    ma45: h.ma45 ?? null,
    demandStrength: lucCau(q),
  };
  const cur = q.PriceCurrent, top = q.PriceCeiling, bottom = q.PriceFloor;
  row.limit = cur && top && cur >= top ? 'ceil' : (cur && bottom && cur <= bottom ? 'floor' : null);
  const today = vnDate(nowMs / 1000);
  const qd = quoteVnDate(q);
  // Quote của phiên cũ (cuối tuần, ngoài giờ) đã đủ cả phiên → không ngoại suy theo giờ hiện tại
  const est = qd === null || qd === today ? tech.estimatedVolume(vol, exchange, nowMs) : (vol || null);
  const st = techStats && Object.keys(techStats).length ? techStats : null;
  Object.assign(row, conditions.quoteMetrics(q));
  Object.assign(row, conditions.techMetrics(st, price, change, est));
  row._tech = st;
  row._live = { last: price, high: k(q.PriceHigh), low: k(q.PriceLow), volume: vol, est };
  Object.assign(row, conditions.indicatorMetrics(st, row._live));
  if (intra) row._live.intra = intra;
  return row;
}

export function groupByExchange(rows) {
  const out = Object.fromEntries(EXCHANGES.map((e) => [e, []]));
  for (const r of rows) if (r.symbol && out[r.exchange]) out[r.exchange].push(r);
  return out;
}

// ── Lọc / sắp xếp (giống bảng giá web) ──────────────────────────────────

// float(v) của Python; null nếu không phải số
export function num(v) {
  if (v === null || v === undefined || v === '' || typeof v === 'object') return null;
  if (typeof v === 'boolean') return v ? 1 : 0;
  if (typeof v === 'string' && !v.trim()) return null;
  const f = Number(v);
  return Number.isNaN(f) ? null : f;
}

// Các cột đang bị lọc: có giá trị (và với 'trong khoảng' thì có cả giá trị thứ hai)
export function activeFilterKeys(filters) {
  const out = [];
  for (const [k, f] of Object.entries(filters || {})) {
    if (!(k in LABEL) || !f || num(f.value) === null) continue;
    if (f.operator === 'bt' && num(f.value2) === null) continue;
    out.push(k);
  }
  return out;
}

export function applyFilters(stocks, filters) {
  let out = stocks;
  for (const key of activeFilterKeys(filters)) {
    const f = filters[key];
    const val = num(f.value), val2 = num(f.value2), op = f.operator;
    const legacy = LEGACY_KEYS.has(key);
    const ok = (s) => {
      let v;
      if (legacy) {
        v = num(s[key] || 0) || 0;                // y bảng giá web: thiếu số coi như 0
      } else {
        v = num(s[key]);
        if (v === null) return false;             // cột kiểu FireAnt chưa tính được thì không khớp
      }
      switch (op) {
        case 'gt': return v > val;
        case 'lt': return v < val;
        case 'eq': return v === val;
        case 'ge': return v >= val;
        case 'le': return v <= val;
        case 'bt': return Math.min(val, val2) <= v && v <= Math.max(val, val2);
        default: return true;
      }
    };
    out = out.filter(ok);
  }
  return out;
}

// Giữ mã thoả TẤT CẢ tín hiệu. Mã chưa có thống kê kỹ thuật thì không khớp.
export function applySignals(stocks, signals) {
  let out = stocks;
  for (const sig of signals || []) out = out.filter((s) => conditions.evalSignal(sig, s._tech, s._live));
  return out;
}

export const TEXT_COLUMNS = ['symbol', 'exchange'];
const cmp = (a, b) => (a < b ? -1 : a > b ? 1 : 0);

// sorted() của Python (ổn định; reverse giữ nguyên thứ tự các phần tử bằng nhau)
function pySorted(arr, key, reverse) {
  const keyed = arr.map((x) => [key(x), x]);
  keyed.sort((a, b) => (reverse ? cmp(b[0], a[0]) : cmp(a[0], b[0])));
  return keyed.map((p) => p[1]);
}

export function sortStocks(stocks, column, direction) {
  const asc = direction === 'asc';
  const empty = asc ? Infinity : -Infinity;
  if (TEXT_COLUMNS.includes(column)) {
    const base = pySorted(stocks, (s) => s.value || 0, true);
    return pySorted(base, (s) => String(s[column] || ''), !asc);
  }
  return pySorted(stocks, (s) => (s[column] === null || s[column] === undefined ? empty : s[column]), !asc);
}

// Bấm tiêu đề cột: cùng cột thì đảo chiều; cột mới thì chữ A→Z, số lớn → nhỏ
export function nextSort(curColumn, curDirection, clicked) {
  if (clicked === curColumn) return [clicked, curDirection === 'desc' ? 'asc' : 'desc'];
  return [clicked, TEXT_COLUMNS.includes(clicked) ? 'asc' : 'desc'];
}

export function selectMatches(allStocks, cfg) {
  const ex = cfg.exchange || 'HSX';
  const pool = ex === 'ALL' ? EXCHANGES.flatMap((e) => allStocks[e] || []) : (allStocks[ex] || []);
  const matched = applySignals(applyFilters(pool, cfg.filters), cfg.signals);
  return sortStocks(matched, cfg.sortColumn || 'value', cfg.sortDirection || 'desc');
}

export const WATCH_NAME = '★ Theo dõi';

// 'vib, mbb  VIB' → ['VIB', 'MBB']: chữ hoa, bỏ trùng, giữ thứ tự gõ. Nhận cả danh sách mã.
export function parseSymbols(text) {
  if (Array.isArray(text)) text = text.map(String).join(' ');
  const out = [];
  for (const s of String(text ?? '').match(/[A-Za-z0-9]+/g) || []) {
    const u = s.toUpperCase();
    if (!out.includes(u)) out.push(u);
  }
  return out;
}

export function selectWatch(rows, symbols, column = 'symbol', direction = 'asc') {
  const bySymbol = new Map(rows.filter((r) => r.symbol).map((r) => [r.symbol, r]));
  return sortStocks(symbols.filter((s) => bySymbol.has(s)).map((s) => bySymbol.get(s)), column || 'symbol', direction || 'asc');
}

export function hasConditions(c) {
  return !!(activeFilterKeys(c.filters).length || (c.signals && c.signals.length));
}

const TECH_KEYS = new Set(conditions.TECH_METRIC_KEYS);

// Tiêu chí có dùng điều kiện cần lịch sử ~1 năm (thống kê kỹ thuật) không — không thì khỏi tải
export function needsTech(c) {
  return (c.signals || []).some((s) => conditions.signalTf(s) === 'D')
    || activeFilterKeys(c.filters).some((k) => TECH_KEYS.has(k));
}

// Tiêu chí có tín hiệu khung 15 phút không — có thì tải nến 15 phút sau mỗi lần chốt nến
export function needsIntraday(c) {
  return (c.signals || []).some((s) => conditions.signalTf(s) === '15m');
}

// Tiêu chí có lọc theo phiên vượt trendline giảm không — có thì phải quét lùi khi tải chỉ báo
export function needsBreakHistory(c) {
  return activeFilterKeys(c.filters).some((k) => k in conditions.BREAK_ALL_KEYS);
}

// Cột kiểu FireAnt đang bị lọc, theo thứ tự danh mục; lọc 1 cột của nhóm vượt trendline thì hiện cả nhóm
export function extraColumns(filters) {
  const active = new Set(activeFilterKeys(filters));
  for (const k of [...active]) {
    if (k in conditions.BREAK_ALL_KEYS) {
      const grp = conditions.BREAK_ALL_KEYS[k];
      active.add(grp);
      conditions.BREAK_COMPANIONS[grp].forEach((x) => active.add(x));
    }
  }
  return conditions.METRIC_KEYS.filter((k) => active.has(k)).map((k) => [k, conditions.METRIC_LABEL[k]]);
}

export function compactColumns(filters) {
  const active = new Set(activeFilterKeys(filters));
  return [...COLUMNS.filter((c) => c[0] === 'symbol' || active.has(c[0])), ...extraColumns(filters)];
}

export const spell = (symbol) => symbol.split('').join(' ');

export function alertText(symbols, limit = 5) {
  const syms = [...symbols];
  const head = syms.slice(0, limit).map(spell);
  const rest = syms.length - head.length;
  const vi = 'Mã mới: ' + head.join(', ') + (rest > 0 ? `, và ${rest} mã khác` : '') + '.';
  const en = 'New: ' + head.join(', ') + (rest > 0 ? `, and ${rest} more` : '') + '.';
  return [vi, en];
}

export const ALERT_MODES = ['speak', 'beep', 'off'];

// Tiêu chí mẫu (Cài đặt → 📋 Mẫu): bấm là thêm thành tiêu chí mới, sửa tiếp được. GTTB 20 phiên lọc mã đủ thanh khoản.
const liq = (bil) => ({ avgValue20: { operator: 'ge', value: bil } });
const S = (id, params = {}) => conditions.normalizeSignal({ id, params });
export const TEMPLATES = [
  { name: 'Cổ phiếu khoẻ, sát đỉnh', desc: 'Giá trên MA50, MA50 trên MA200, cách đỉnh 1 năm ≤ 10%, GTTB ≥ 10 tỷ',
    exchange: 'ALL', filters: { ...liq(10), fromHigh1y: { operator: 'le', value: 10 } },
    signals: [S('PriceAboveSMA', { period: 50 }), S('ShortSMAAboveLongSMA', { short: 50, long: 200 })] },
  { name: 'Pullback về MA20', desc: 'Xu hướng tăng, điều chỉnh về chạm SMA20 (±2%), KL cạn dần, GTTB ≥ 5 tỷ',
    exchange: 'ALL', filters: liq(5), signals: [S('PullbackToSMA', { period: 20 })] },
  { name: 'Vượt đỉnh 3 tháng + KL lớn', desc: 'Giá vượt đỉnh 3 tháng, KL dự kiến vượt TB 20 phiên ≥ 50%, GTTB ≥ 3 tỷ',
    exchange: 'ALL', filters: liq(3),
    signals: [S('AbovePreviousHigh', { period: '3m' }), S('EstimatedVolumeSurge', { period: 20, pct: 50 })] },
  { name: 'RSI tạo đáy 15 phút', desc: 'RSI 15 phút vừa thoát vùng 30, trên Signal, giá trên MA10 — GTTB ≥ 10 tỷ',
    exchange: 'ALL', filters: liq(10), signals: [S('RSIBottom', { tf: '15m' })] },
  { name: 'Bắt đáy quá bán', desc: 'RSI(14) ≤ 35, Stochastic %K cắt lên %D từ vùng dưới 20, GTTB ≥ 5 tỷ',
    exchange: 'ALL', filters: { ...liq(5), rsi14: { operator: 'le', value: 35 } },
    signals: [S('StochKCrossAboveDOverSold', { level: 20 })] },
  { name: 'Xu hướng tăng mạnh', desc: '+DI trên −DI và ADX > 25, Parabolic SAR báo tăng, giá trên mây Ichimoku, GTTB ≥ 5 tỷ',
    exchange: 'ALL', filters: liq(5),
    signals: [S('ADXStrongUptrend', { level: 25 }), S('SARUptrend'), S('IchimokuAboveCloud')] },
  { name: 'Nền chặt sát đỉnh', desc: 'Dải Bollinger hẹp (≤ 10%), cách đỉnh 3 tháng ≤ 15%, giá trên MA50, GTTB ≥ 3 tỷ',
    exchange: 'ALL', filters: { ...liq(3), bbWidth: { operator: 'le', value: 10 }, fromHigh3m: { operator: 'le', value: 15 } },
    signals: [S('PriceAboveSMA', { period: 50 })] },
  { name: 'Vượt trendline giảm', desc: 'Hôm nay vượt trendline giảm 6 tháng ≥ 1%, KL dự kiến ≥ KLTB 20, GTTB ≥ 3 tỷ',
    exchange: 'ALL', filters: liq(3), signals: [S('BreakDownTrendline', { period: '6m' })] },
  { name: 'Dòng tiền vào', desc: 'OBV cắt lên TB 20 phiên, MFI ≥ 50, giá trên MA20, GTTB ≥ 5 tỷ',
    exchange: 'ALL', filters: { ...liq(5), mfi14: { operator: 'ge', value: 50 } },
    signals: [S('OBVCrossAboveMA'), S('PriceAboveSMA', { period: 20 })] },
  { name: 'Khối ngoại mua ròng', desc: 'Nước ngoài mua ròng ≥ 10 tỷ hôm nay, giá đang tăng',
    exchange: 'ALL', filters: { foreignNetValue: { operator: 'ge', value: 10 }, changePercent: { operator: 'gt', value: 0 } } },
];

const isObj = (c) => c && typeof c === 'object' && !Array.isArray(c);

// Danh sách tiêu chí lọc. Cài đặt cũ (1 bộ lọc ở exchange/filters) tự thành "Tiêu chí 1".
export function criteriaFromConfig(cfg) {
  const defaultAlert = ALERT_MODES.includes(cfg.alert) ? cfg.alert : 'speak';
  const alertOf = (c) => (ALERT_MODES.includes(c.alert) ? c.alert : defaultAlert);
  const sortOf = (c) => {
    const col = c.sortColumn || cfg.sortColumn;
    if (!col) return {};
    return { sortColumn: col, sortDirection: c.sortDirection || cfg.sortDirection || 'desc' };
  };
  const out = [];
  (cfg.criteria || []).forEach((c, i) => {
    if (!isObj(c)) return;
    const item = {
      name: String(c.name ?? '').trim() || `Tiêu chí ${i + 1}`,
      exchange: c.exchange || 'HSX',
      filters: { ...(isObj(c.filters) ? c.filters : {}) },
      alert: alertOf(c),
    };
    const signals = (c.signals || []).map(conditions.normalizeSignal).filter(Boolean);
    if (signals.length) item.signals = signals;
    Object.assign(item, sortOf(c));
    out.push(item);
  });
  if (!out.length) {
    out.push({ name: 'Tiêu chí 1', exchange: cfg.exchange || 'HSX', filters: { ...(cfg.filters || {}) },
      alert: defaultAlert, ...sortOf({}) });
  }
  return out;
}

// JSON với khoá xếp theo thứ tự (json.dumps(sort_keys=True)) — để so nội dung
function stableJson(v) {
  if (Array.isArray(v)) return '[' + v.map(stableJson).join(',') + ']';
  if (v && typeof v === 'object') return '{' + Object.keys(v).sort().map((k) => JSON.stringify(k) + ':' + stableJson(v[k])).join(',') + '}';
  return JSON.stringify(v ?? null);
}

// Nhận diện 1 tiêu chí theo nội dung (đổi tên / kiểu xếp / kiểu báo không tính là đổi lọc)
export function criterionKey(c) {
  const key = [c.exchange, c.filters];
  if (c.signals && c.signals.length) key.push(c.signals);
  return stableJson(key);
}

export function alertTextGroups(groups, limit = 6, names = null) {
  groups = groups.filter(([, s]) => s.length).map(([n, s]) => [n, [...s]]);
  if (names === null) names = groups.length > 1;
  if (!names) return alertText(groups.flatMap(([, s]) => s), 5);
  const vi = [], en = [];
  let used = 0, rest = 0;
  for (const [name, syms] of groups) {
    const take = syms.slice(0, Math.max(0, limit - used));
    used += take.length;
    rest += syms.length - take.length;
    if (take.length) {
      vi.push(`${name}: ` + take.map(spell).join(', '));
      en.push(`${name}: ` + take.map(spell).join(', '));
    }
  }
  const tailVi = rest ? `. Và ${rest} mã khác` : '';
  const tailEn = rest ? `. And ${rest} more` : '';
  return [vi.join('. ') + tailVi + '.', en.join('. ') + tailEn + '.'];
}

export const EXCHANGE_COL = ['exchange', 'Sàn'];
export const EXCHANGE_SHORT = { HSX: 'HSX', HNX: 'HNX', UPCOM: 'UpCom' };

// Cột hiện ra (xem table_columns của core.py)
export function tableColumns(cfg, full) {
  if (cfg.watch) {
    const cols = full ? [...COLUMNS] : COLUMNS.filter((c) => ['symbol', 'price', 'changePercent'].includes(c[0]));
    if (full) cols.splice(1, 0, EXCHANGE_COL);
    return cols;
  }
  let cols = full ? [...COLUMNS, ...extraColumns(cfg.filters)] : compactColumns(cfg.filters);
  if (!full && cfg.signals && cfg.signals.length) {
    const keys = new Set(cols.map((c) => c[0]));
    cols = [...COLUMNS.filter((c) => ['symbol', 'price', 'changePercent'].includes(c[0]) || keys.has(c[0])),
      ...extraColumns(cfg.filters)];
  }
  if (full && cfg.exchange === 'ALL') cols.splice(1, 0, EXCHANGE_COL);
  return cols;
}

export function describeFilters(filters, signals = null) {
  const one = (k) => {
    const f = filters[k];
    if (f.operator === 'bt') return `${LABEL[k] ?? k} từ ${jsNum(f.value)} đến ${jsNum(f.value2)}`;
    return `${LABEL[k] ?? k} ${OPS[f.operator] ?? '?'} ${jsNum(f.value)}`;
  };
  return [...activeFilterKeys(filters).map(one), ...(signals || []).map(conditions.describeSignal)].join(' · ');
}

// ── Định dạng (giống web) ───────────────────────────────────────────────
export function formatPrice(p) {
  if (p === null || p === undefined || Number.isNaN(p)) return '--';
  if (p === 0) return '0';
  const s = fixed(p, 1);
  return s.endsWith('.0') ? s.slice(0, -2) : s;
}

export function formatVolume(v) {
  if (v === null || v === undefined) return '--';
  if (v >= 1e9) return fixed(v / 1e9, 1) + 'B';
  if (v >= 1e6) return fixed(v / 1e6, 1) + 'M';
  if (v >= 1e3) return fixed(v / 1e3, 1) + 'K';
  return String(Math.trunc(v));
}

// [chữ, tông màu] — tông: 'ceil' | 'floor' | 'up' | 'down' | 'flat' | 'muted' | ''
export function formatCell(s, key) {
  const change = s.change || 0;
  const tone = s.limit || (change > 0 ? 'up' : (change < 0 ? 'down' : 'flat'));
  const plus = change > 0 ? '+' : '';
  switch (key) {
    case 'symbol': return [s.symbol || '', tone];
    case 'exchange': return [EXCHANGE_SHORT[s.exchange] ?? (s.exchange || ''), 'muted'];
    case 'price': return [formatPrice(s.price ?? null), tone];
    case 'change': return [plus + formatPrice(change), tone];
    case 'changePercent': return [plus + fixed(s.changePercent || 0, 2) + '%', tone];
    case 'volume': return [formatVolume(s.volume ?? null), ''];
    case 'volRatio': {
      const r = s.volRatio;
      if (r === null || r === undefined) return ['--', 'muted'];
      return [`${r}%`, r > 100 ? 'up' : (r < 100 ? 'down' : '')];
    }
    case 'value': return [(s.value ? fixed(s.value, 1) : '--') + ' tỷ', ''];
    case 'ma10': case 'ma20': case 'ma45': return [s[key] ? jsNum(s[key]) : '--', ''];
    case 'demandStrength': {
      const d = s.demandStrength;
      if (d === null || d === undefined) return ['—', 'muted'];
      return [jsNum(d) + '%', d > 50 ? 'up' : (d < 50 ? 'down' : 'flat')];
    }
  }
  const fmt = conditions.METRIC_FMT[key];
  if (fmt === 'ago') {
    const v = s[key];
    if (v === null || v === undefined) return ['--', 'muted'];
    return v === 0 ? ['hôm nay', 'up'] : [s[key + 'Day'] || `${v} phiên`, ''];
  }
  if (fmt) return formatMetric(s[key] ?? null, fmt);
  return [String(s[key] ?? ''), ''];
}

export function formatMetric(v, fmt) {
  if (v === null || v === undefined) return ['--', 'muted'];
  const tone = v > 0 ? 'up' : (v < 0 ? 'down' : 'flat');
  switch (fmt) {
    case 'pct': return [(v > 0 ? '+' : '') + fixed(v, 2) + '%', tone];
    case 'price': return [jsNum(v), ''];
    case 'pct0': return [fixed(v, 0) + '%', v > 50 ? 'up' : (v < 50 ? 'down' : 'flat')];
    case 'int': return [String(Math.trunc(v)), ''];
    case 'vol': return [formatVolume(v), ''];
    case 'svol': return [(v > 0 ? '+' : v < 0 ? '-' : '') + formatVolume(Math.abs(v)), tone];
    case 'sbil': return [(v > 0 ? '+' : '') + fixed(v, 1) + ' tỷ', tone];
    case 'bil': return [fixed(v, 1) + ' tỷ', ''];
    case 'num': return [fixed(v, 1), ''];             // giá trị chỉ báo (RSI, ADX, CCI…)
    case 'upct': return [fixed(v, 1) + '%', ''];      // % không dấu (cách đỉnh / đáy, độ rộng dải…)
  }
  return [String(v), ''];
}
