// Danh mục điều kiện lọc kiểu FireAnt Screener + công thức đánh giá — chép từ conditions.py.
//   • METRICS — một con số trên mỗi mã, lọc bằng ≥ ≤ hoặc "trong khoảng".
//   • SIGNALS — tín hiệu đúng / sai kèm tham số (giá cắt lên SMA(5), RSI vào vùng quá mua trên 70…).
// Số thống kê tính ở phiên đã đóng gần nhất (tech.js) rồi ghép giá hiện tại vào. Giá tính bằng nghìn đồng:
// khoảng đệm 0.05 ở EMA / Bollinger là 50đ (một bước giá), y như FireAnt.
import * as tech from './tech.js';

export const GROUPS = [['price', 'Giá'], ['volume', 'Khối lượng'], ['ma', 'Đường trung bình'],
  ['rsi', 'RSI (14)'], ['mfi', 'MFI (14)'], ['bb', 'Bollinger Band (20)'], ['macd', 'MACD'],
  ['pullback', 'Pullback & trendline']];

// [khoá, nhãn đầy đủ, nhãn ngắn trên tiêu đề cột, nhóm, kiểu hiển thị]
export const METRICS = [
  ['change1w', 'Thay đổi giá 1 tuần (%)', '% 1 tuần', 'price', 'pct'],
  ['change1m', 'Thay đổi giá 1 tháng (%)', '% 1 tháng', 'price', 'pct'],
  ['change3m', 'Thay đổi giá 3 tháng (%)', '% 3 tháng', 'price', 'pct'],
  ['change6m', 'Thay đổi giá 6 tháng (%)', '% 6 tháng', 'price', 'pct'],
  ['change1y', 'Thay đổi giá 1 năm (%)', '% 1 năm', 'price', 'pct'],
  ['upDays', 'Số phiên tăng giá liên tục', 'Phiên tăng', 'price', 'int'],
  ['downDays', 'Số phiên giảm giá liên tục', 'Phiên giảm', 'price', 'int'],
  ['upDaysBeforeDown', 'Số phiên tăng liên tục trước khi đảo chiều giảm', 'Tăng→giảm', 'price', 'int'],
  ['downDaysBeforeUp', 'Số phiên giảm liên tục trước khi đảo chiều tăng', 'Giảm→tăng', 'price', 'int'],
  ['activeBuyPct', '% KL khớp lệnh do bên mua chủ động', '% mua CĐ', 'volume', 'pct0'],
  ['avgVol5', 'KLTB 5 phiên', 'KLTB 5', 'volume', 'vol'],
  ['avgVol10', 'KLTB 10 phiên', 'KLTB 10', 'volume', 'vol'],
  ['avgVol20', 'KLTB 20 phiên', 'KLTB 20', 'volume', 'vol'],
  ['avgVol3m', 'KLTB 3 tháng', 'KLTB 3T', 'volume', 'vol'],
  ['foreignNetVol', 'KL nước ngoài mua ròng', 'KL NN ròng', 'volume', 'svol'],
  ['foreignNetValue', 'GT nước ngoài mua ròng (tỷ)', 'GT NN ròng', 'volume', 'sbil'],
  ['distSMA20', 'Khoảng cách giá tới SMA20 (%)', '↕SMA20', 'pullback', 'pct'],
  ['distSMA50', 'Khoảng cách giá tới SMA50 (%)', '↕SMA50', 'pullback', 'pct'],
  ['brkTL3m', 'Vượt trendline giảm 3 tháng cách đây (phiên)', 'Vượt TL 3T', 'pullback', 'ago'],
  ['brkTL3mPx', 'Giá vượt trendline giảm 3 tháng (giá đóng cửa phiên vượt)', 'Giá vượt 3T', 'pullback', 'price'],
  ['brkTL3mPct', '% giá hiện tại so với giá vượt trendline giảm 3 tháng', '% từ vượt 3T', 'pullback', 'pct'],
  ['brkTL6m', 'Vượt trendline giảm 6 tháng cách đây (phiên)', 'Vượt TL 6T', 'pullback', 'ago'],
  ['brkTL6mPx', 'Giá vượt trendline giảm 6 tháng (giá đóng cửa phiên vượt)', 'Giá vượt 6T', 'pullback', 'price'],
  ['brkTL6mPct', '% giá hiện tại so với giá vượt trendline giảm 6 tháng', '% từ vượt 6T', 'pullback', 'pct'],
];
export const METRIC_KEYS = METRICS.map((m) => m[0]);
export const METRIC_LABEL = Object.fromEntries(METRICS.map((m) => [m[0], m[1]]));
export const METRIC_HEAD = Object.fromEntries(METRICS.map((m) => [m[0], m[2]]));
export const METRIC_GROUP = Object.fromEntries(METRICS.map((m) => [m[0], m[3]]));
export const METRIC_FMT = Object.fromEntries(METRICS.map((m) => [m[0], m[4]]));

const TECH_PERIOD = { change1w: '1w', change1m: '1m', change3m: '3m', change6m: '6m', change1y: '1y' };
const TECH_AVGVOL = { avgVol5: 'v5', avgVol10: 'v10', avgVol20: 'v20', avgVol3m: 'v3m' };
const TECH_DIST = { distSMA20: 20, distSMA50: 50 };
// Phiên vượt trendline giảm gần nhất (0 = hôm nay): cần quét lùi tech.lastBreak — nặng, chỉ tính khi có tiêu chí dùng.
export const BREAK_METRIC_KEYS = { brkTL3m: '3m', brkTL6m: '6m' };
export const BREAK_COMPANIONS = Object.fromEntries(Object.keys(BREAK_METRIC_KEYS).map((k) => [k, [k + 'Px', k + 'Pct']]));
export const BREAK_ALL_KEYS = {};      // cột → cột chính của nhóm
for (const [grp, ks] of Object.entries(BREAK_COMPANIONS)) for (const k of [grp, ...ks]) BREAK_ALL_KEYS[k] = grp;
export const TECH_METRIC_KEYS = [...Object.keys(TECH_PERIOD), ...Object.keys(TECH_AVGVOL), ...Object.keys(TECH_DIST),
  ...Object.keys(BREAK_ALL_KEYS), 'upDays', 'downDays', 'upDaysBeforeDown', 'downDaysBeforeUp'];

const nz = (v) => v !== null && v !== undefined;
const truthy = (v) => nz(v) && v !== 0 && v !== '' && !Number.isNaN(v);    // bool(v) của Python cho số / chuỗi

// Các con số lấy thẳng từ quote FireAnt: % mua chủ động, nước ngoài mua ròng (KL, GT tỷ đồng)
export function quoteMetrics(q) {
  const tv = q.TotalVolume || 0;
  const bq = q.BuyForeignQuantity, sq = q.SellForeignQuantity;
  const bv = q.BuyForeignValue, sv = q.SellForeignValue;
  return {
    activeBuyPct: tv > 0 ? (q.TotalActiveBuyVolume || 0) * 100 / tv : null,
    foreignNetVol: !nz(bq) && !nz(sq) ? null : (bq || 0) - (sq || 0),
    foreignNetValue: !nz(bv) && !nz(sv) ? null : ((bv || 0) - (sv || 0)) / 1e9,
  };
}

// Các con số cần lịch sử (xem tech_metrics của conditions.py)
export function techMetrics(st, last, change, est = null) {
  const out = {};
  for (const k of [...Object.keys(TECH_PERIOD), ...Object.keys(TECH_AVGVOL), ...Object.keys(TECH_DIST),
    ...Object.keys(BREAK_ALL_KEYS), 'upDays', 'downDays', 'upDaysBeforeDown', 'downDaysBeforeUp']) out[k] = null;
  if (!st || !Object.keys(st).length) return out;
  if (truthy(last) && last > 0) {
    for (const [key, per] of Object.entries(TECH_PERIOD)) {
      const px = st[`px${per}`];
      if (truthy(px) && px > 0) out[key] = (last - px) * 100 / px;
    }
    for (const [key, n] of Object.entries(TECH_DIST)) {
      const ma = smaLive(st, last, n);
      if (truthy(ma)) out[key] = (last - ma) * 100 / ma;
    }
    for (const [key, per] of Object.entries(BREAK_METRIC_KEYS)) {
      const [pxKey, pctKey] = BREAK_COMPANIONS[key];
      if (breakDownLine(st, { last, est }, { period: per, brk: tech.BREAK_UP * 100, vol: 'có' })) {
        out[key] = 0; out[key + 'Day'] = null; out[pxKey] = last;
      } else if (st['tb' + per]) {
        const tb = st['tb' + per];
        out[key] = tb.k; out[key + 'Day'] = `${tb.d.slice(8, 10)}/${tb.d.slice(5, 7)}`; out[pxKey] = tb.p;
      }
      if (truthy(out[pxKey])) out[pctKey] = (last - out[pxKey]) * 100 / out[pxKey];
    }
  }
  for (const [key, sk] of Object.entries(TECH_AVGVOL)) out[key] = nz(st[sk]) ? st[sk] : null;
  const s = st.streak;
  if (nz(s) && truthy(change)) {
    if (change > 0 && s >= 0) out.upDays = s + 1;
    if (change < 0 && s <= 0) out.downDays = -s + 1;
    if (change < 0 && s > 0) out.upDaysBeforeDown = s;
    if (change > 0 && s < 0) out.downDaysBeforeUp = -s;
  }
  return out;
}

// ── Tín hiệu có tham số ─────────────────────────────────────────────────
// choices: giá trị cho chọn; free=true: ô nhập số tự do (vẫn gợi ý choices) trong khoảng lo..hi
const P = (id, name, choices, def, free = false, lo = null, hi = null) => ({ id, name, choices, default: def, free, lo, hi });

export const PERIOD_NAME = { '1w': '1 tuần', '2w': '2 tuần', '1m': '1 tháng', '3m': '3 tháng', '6m': '6 tháng', '1y': '1 năm' };
export const MA_PERIODS = [5, 10, 15, 20, 45, 50, 100, 200];
const P_HIGHLOW = P('period', 'trong', Object.keys(PERIOD_NAME), '1y');
const P_MA = P('period', 'kỳ (phiên)', MA_PERIODS, 5);
const P_RSI_UP = P('level', 'ngưỡng quá mua', [60, 65, 70, 75, 80, 85, 90], 70, true, 0, 100);
const P_RSI_DOWN = P('level', 'ngưỡng quá bán', [10, 15, 20, 25, 30, 35, 40], 30, true, 0, 100);
const P_MFI_UP = P('level', 'ngưỡng quá mua', [70, 75, 80, 85, 90], 80, true, 0, 100);
const P_MFI_DOWN = P('level', 'ngưỡng quá bán', [10, 15, 20, 25, 30], 20, true, 0, 100);
const P_BB = P('std', 'độ lệch chuẩn', [2, 3.5], 2, true, 0.5, 6);
const P_PB_MA = P('period', 'SMA (phiên)', Object.keys(tech.PB_SMA).map(Number), 20);
const P_PB_TL = P('period', 'trendline trong', Object.keys(tech.TL_WINDOWS), '6m');
const P_PB_TOL = P('tol', 'vùng ± (%)', [1, 1.5, 2, 3], 2, true, 0.5, 5);
const P_PB_DRY = P('dry', 'KL cạn dần', ['có', 'không'], 'có');
const P_BRK = P('brk', 'vượt đường tối thiểu (%)', [0.5, 1, 2, 3], 1, true, 0, 10);
const P_BRK_VOL = P('vol', 'KL dự kiến ≥ KLTB 20', ['có', 'không'], 'có');

function valid(st, lv) {
  return !!st && Object.keys(st).length > 0 && !!lv && (lv.last || 0) > 0;
}

// Thiếu khoá mà Python sẽ báo lỗi (KeyError / so với None) → tín hiệu trả sai
class Missing extends Error {}
function need(v) {
  if (!nz(v)) throw new Missing();
  return v;
}

// --- Giá vượt đỉnh / thủng đáy ---
const aboveHigh = (st, lv, p) => { const hi = st['hi' + p.period]; return truthy(hi) && hi < lv.last; };
const belowLow = (st, lv, p) => { const lo = st['lo' + p.period]; return truthy(lo) && lo > lv.last; };

// --- KL dự kiến cả phiên vượt trung bình các phiên trước ---
function estVolumeSurge(st, lv, p) {
  const n = p.period, est = lv.est, prev = st[`v${n - 1}`];
  if (!truthy(est) || !truthy(prev)) return false;
  const avg = (prev * (n - 1) + est) / n;
  return est > (1 + p.pct) * avg;
}

// --- Giá cắt SMA / EMA; SMA ngắn cắt SMA dài ---
const smaCross = (up) => (st, lv, p) => {
  const n = p.period, a = st[`p${n}`], b = st[`p${n - 1}`];
  if (!truthy(a) || !truthy(b) || !truthy(st.lc)) return false;
  const live = (lv.last + (n - 1) * b) / n;
  return up ? (st.lc <= a && lv.last > live) : (st.lc >= a && lv.last < live);
};

const emaCross = (up) => (st, lv, p) => {
  const n = p.period, e = st[`e${n}`];
  if (!truthy(e) || !truthy(st.lc)) return false;
  const live = (2 * lv.last + (n - 1) * e) / (n + 1);
  return up ? (st.lc <= e && lv.last > live + 0.05) : (st.lc >= e && lv.last < live - 0.05);
};

const smaPair = (up) => (st, lv, p) => {
  const s = p.short, l = p.long;
  const ps = st[`p${s}`], ps1 = st[`p${s - 1}`], pl = st[`p${l}`], pl1 = st[`p${l - 1}`];
  if (!(truthy(ps) && truthy(ps1) && truthy(pl) && truthy(pl1))) return false;
  const liveS = (lv.last + (s - 1) * ps1) / s;
  const liveL = (lv.last + (l - 1) * pl1) / l;
  return up ? (ps <= pl && liveS > liveL) : (ps >= pl && liveS < liveL);
};

// --- RSI(14) ---
const rsiOf = (gain, loss) => (loss === 0 ? 100 : 100 - 100 / (1 + gain / loss));

export function rsiNow(st, last) {
  const ag = st.ag, al = st.al, lc = st.lc;
  if (!nz(ag) || !nz(al) || !nz(lc)) return [null, null];
  const d = last - lc;
  return [rsiOf(ag, al), rsiOf(ag * 13 + Math.max(d, 0), al * 13 + Math.max(-d, 0))];
}

const rsi = (kind) => (st, lv, p) => {
  const [prev, live] = rsiNow(st, lv.last);
  if (live === null) return false;
  const a = p.level;
  return { cross_up: prev <= a && a < live, cross_down: prev >= a && a > live, above: live > a, below: live < a }[kind];
};

// --- MFI(14) ---
export function mfiNow(st, lv) {
  if (['lh', 'll', 'lc', 'pmf', 'nmf', 'mfi'].some((k) => !nz(st[k]))) return [null, null];
  const last = lv.last;
  const tpPrev = (st.lh + st.ll + st.lc) / 3;
  const tpNow = ((lv.high || last) + (lv.low || last) + last) / 3;
  const flow = tpNow * (lv.volume || 0);
  const pos = st.pmf + (tpNow > tpPrev ? flow : 0);
  const neg = st.nmf + (tpNow < tpPrev ? flow : 0);
  return [st.mfi, neg === 0 ? 100 : 100 - 100 / (1 + pos / neg)];
}

const mfi = (kind) => (st, lv, p) => {
  const [prev, live] = mfiNow(st, lv);
  if (live === null) return false;
  const a = p.level;
  return { cross_up: live > a && prev < a, cross_down: live < a && prev > a, above: live > a, below: live < a }[kind];
};

// --- Bollinger Band (20, k) ---
export function bbNow(st, last, k) {
  const p19 = st.p19, p20 = st.p20, s19 = st.sd19, s20 = st.sd20;
  if (![p19, p20, s19, s20].every(nz)) return null;
  const mid = (p19 * 19 + last) / 20;
  const d = last - p19;
  const sd = Math.sqrt(19 * (d * d) + 380 * (s19 * s19)) / 20;
  return [[p20 + k * s20, p20 - k * s20], [mid + k * sd, mid - k * sd]];
}

const bb = (kind) => (st, lv, p) => {
  const r = bbNow(st, lv.last, p.std);
  const lc = st.lc;
  if (r === null || !nz(lc)) return false;
  const [[up0, lo0], [up1, lo1]] = r;
  const last = lv.last;
  return {
    cross_above: lc < up0 && last > up1 + 0.05,
    back_from_above: lc > up0 && last < up1 - 0.05,
    above: last > up1 + 0.05,
    cross_below: lc > lo0 && last < lo1 - 0.05,
    back_from_below: lc < lo0 && last > lo1 + 0.05,
    below: last < lo1 - 0.05,
  }[kind];
};

// --- MACD (12, 26, 9) ---
export function macdNow(st, last) {
  const e12 = st.e12, e26 = st.e26, sig = st.sig;
  if (![e12, e26, sig].every(nz)) return null;
  const a12 = 2 / 13, a26 = 2 / 27;
  const live = (a12 * last + (1 - a12) * e12) - (a26 * last + (1 - a26) * e26);
  return [e12 - e26, sig, live, 0.2 * live + 0.8 * sig];
}

const macd = (kind) => (st, lv) => {
  const r = macdNow(st, lv.last);
  if (r === null) return false;
  const [prev, sig, live, liveSig] = r;
  return {
    cross_above_sig: prev < sig && live > liveSig,
    above_sig: live > liveSig,
    cross_below_sig: prev > sig && live < liveSig,
    below_sig: live < liveSig,
    cross_above_zero: prev < 0 && live > 0,
    above_zero: live > 0,
    cross_below_zero: prev > 0 && live < 0,
    below_zero: live < 0,
  }[kind];
};

// --- Pullback: đang xu hướng tăng, điều chỉnh về kiểm định SMA / trendline tăng ---
export function smaLive(st, last, n) {
  const prev = st[`p${n - 1}`];
  return truthy(prev) ? (last + (n - 1) * prev) / n : null;
}

function pbLine(st, last, p, source) {
  if (source === 'sma') {
    const n = p.period;
    const line = smaLive(st, last, n), ref = st[`ps${n}`], leg = st[`pb${n}`];
    if (!truthy(line) || !truthy(ref) || !leg || !((st[`p${n}`] || 0) > ref)) return null;
    return [line, leg, tech.PB_SMA[n][1]];
  }
  const tl = st['tl' + p.period];
  return tl ? [tl.v + tl.s, tl, tech.TL_EXT] : null;
}

const pullback = (source, bounce) => (st, lv, p) => {
  const last = lv.last;
  const r = pbLine(st, last, p, source);
  if (r === null) return false;
  const [line, leg, ext] = r;
  const tol = p.tol / 100;
  if (line <= 0 || need(leg.ext) < ext || (nz(leg.mr) && leg.mr < 1 - tol)) return false;
  if (p.dry === 'có') {
    const est = lv.est, v20 = st.v20;
    const total = (truthy(leg.vpb) ? leg.vpb * leg.pk : 0) + (est || 0);
    const count = (truthy(leg.vpb) ? leg.pk : 0) + (truthy(est) ? 1 : 0);
    if (!count || !truthy(v20) || total / count >= v20) return false;
  }
  const touched = Math.min(lv.low || last, last) <= line * (1 + tol);
  if (bounce) return (touched || need(leg.lr) <= 1 + tol) && last > line && last > need(st.lc);
  return touched && last >= line * (1 - tol);
};

const firstAbove = (ratios, k) => {
  const j = ratios.findIndex((r) => r >= k);
  return j < 0 ? null : j;
};

// Vượt lên trendline giảm: các phiên trước chưa vượt ≥ brk%, hôm nay vượt ≥ brk%, (vol) KL dự kiến ≥ KLTB 20
export function breakDownLine(st, lv, p) {
  const td = st['td' + p.period];
  if (!td) return false;
  const k = 1 + p.brk / 100;
  if (firstAbove(td.cr, k) !== null || lv.last < (td.v + td.s) * k) return false;
  if (p.vol === 'có') {
    const est = lv.est, v20 = st.v20;
    return !!(truthy(est) && truthy(v20) && est >= v20);
  }
  return true;
}

export const BROKE = 1.01;

const retestDownLine = (bounce) => (st, lv, p) => {
  const td = st['td' + p.period];
  if (!td) return false;
  const j = firstAbove(td.cr, BROKE);
  if (j === null) return false;
  const tol = p.tol / 100, last = lv.last;
  const line = td.v + td.s;
  if (Math.min(...td.cr.slice(j)) < 1 - tol || last < line * (1 - tol)) return false;
  let touched = Math.min(lv.low || last, last) <= line * (1 + tol);
  if (bounce) {
    touched = touched || td.lr.slice(Math.max(j + 1, td.lr.length - 2)).some((r) => r <= 1 + tol);
    return touched && last > line && last > need(st.lc);
  }
  return touched;
};

const S = (id, group, label, params, fn) => ({ id, group, label, params, fn });

export const SIGNAL_LIST = [
  S('AbovePreviousHigh', 'price', 'Giá vượt đỉnh {period}', [P_HIGHLOW], aboveHigh),
  S('BelowPreviousLow', 'price', 'Giá thủng đáy {period}', [P_HIGHLOW], belowLow),
  S('EstimatedVolumeSurge', 'volume', 'KL dự kiến vượt TB {period} phiên tối thiểu {pct}%',
    [P('period', 'TB (phiên)', MA_PERIODS, 5), P('pct', 'vượt tối thiểu (%)', [10, 20, 30, 50, 70, 100, 150, 200, 300], 50, true, 1, 1000)],
    estVolumeSurge),
  S('PriceCrossAboveSMA', 'ma', 'Giá cắt lên SMA({period})', [P_MA], smaCross(true)),
  S('PriceCrossBelowSMA', 'ma', 'Giá cắt xuống SMA({period})', [P_MA], smaCross(false)),
  S('PriceCrossAboveEMA', 'ma', 'Giá cắt lên EMA({period})', [P_MA], emaCross(true)),
  S('PriceCrossBelowEMA', 'ma', 'Giá cắt xuống EMA({period})', [P_MA], emaCross(false)),
  S('ShortSMACrossAboveLongSMA', 'ma', 'SMA({short}) cắt lên SMA({long})',
    [P('short', 'SMA ngắn', [5, 10, 15, 20, 50], 5), P('long', 'cắt lên SMA dài', [15, 20, 45, 50, 100, 200], 15)], smaPair(true)),
  S('ShortSMACrossBelowLongSMA', 'ma', 'SMA({short}) cắt xuống SMA({long})',
    [P('short', 'SMA ngắn', [5, 10, 15, 20, 50], 5), P('long', 'cắt xuống SMA dài', [15, 20, 45, 50, 100, 200], 15)], smaPair(false)),
  S('RSICrossAboveOverBoughtLine', 'rsi', 'RSI(14) đi vào vùng quá mua (trên {level})', [P_RSI_UP], rsi('cross_up')),
  S('RSICrossBelowOverBoughtLine', 'rsi', 'RSI(14) thoát khỏi vùng quá mua (trên {level})', [P_RSI_UP], rsi('cross_down')),
  S('RSIAboveOverBoughtLine', 'rsi', 'RSI(14) đang trong vùng quá mua (trên {level})', [P_RSI_UP], rsi('above')),
  S('RSICrossBelowOverSoldLine', 'rsi', 'RSI(14) đi vào vùng quá bán (dưới {level})', [P_RSI_DOWN], rsi('cross_down')),
  S('RSICrossAboveOverSoldLine', 'rsi', 'RSI(14) thoát khỏi vùng quá bán (dưới {level})', [P_RSI_DOWN], rsi('cross_up')),
  S('RSIBelowOverSoldLine', 'rsi', 'RSI(14) đang trong vùng quá bán (dưới {level})', [P_RSI_DOWN], rsi('below')),
  S('MFICrossAboveOverBoughtLine', 'mfi', 'MFI(14) đi vào vùng quá mua (trên {level})', [P_MFI_UP], mfi('cross_up')),
  S('MFICrossBelowOverBoughtLine', 'mfi', 'MFI(14) thoát khỏi vùng quá mua (trên {level})', [P_MFI_UP], mfi('cross_down')),
  S('MFIAboveOverBoughtLine', 'mfi', 'MFI(14) đang trong vùng quá mua (trên {level})', [P_MFI_UP], mfi('above')),
  S('MFICrossBelowOverSoldLine', 'mfi', 'MFI(14) đi vào vùng quá bán (dưới {level})', [P_MFI_DOWN], mfi('cross_down')),
  S('MFICrossAboveOverSoldLine', 'mfi', 'MFI(14) thoát khỏi vùng quá bán (dưới {level})', [P_MFI_DOWN], mfi('cross_up')),
  S('MFIBelowOverSoldLine', 'mfi', 'MFI(14) đang trong vùng quá bán (dưới {level})', [P_MFI_DOWN], mfi('below')),
  S('PriceCrossAboveBollingerBands', 'bb', 'Giá thoát ra ngoài biên trên Bollinger (20, {std})', [P_BB], bb('cross_above')),
  S('PriceCrossFromAboveBollingerBands', 'bb', 'Giá cắt xuống từ ngoài biên trên Bollinger (20, {std})', [P_BB], bb('back_from_above')),
  S('PriceAboveBollingerBands', 'bb', 'Giá đang ở ngoài biên trên Bollinger (20, {std})', [P_BB], bb('above')),
  S('PriceCrossBelowBollingerBands', 'bb', 'Giá thoát ra ngoài biên dưới Bollinger (20, {std})', [P_BB], bb('cross_below')),
  S('PriceCrossFromBelowBollingerBands', 'bb', 'Giá cắt lên từ ngoài biên dưới Bollinger (20, {std})', [P_BB], bb('back_from_below')),
  S('PriceBelowBollingerBands', 'bb', 'Giá đang ở ngoài biên dưới Bollinger (20, {std})', [P_BB], bb('below')),
  S('MACDCrossAboveSignalLine', 'macd', 'MACD cắt lên đường tín hiệu', [], macd('cross_above_sig')),
  S('MACDAboveSignalLine', 'macd', 'MACD đang ở trên đường tín hiệu', [], macd('above_sig')),
  S('MACDCrossBelowSignalLine', 'macd', 'MACD cắt xuống đường tín hiệu', [], macd('cross_below_sig')),
  S('MACDBelowSignalLine', 'macd', 'MACD đang ở dưới đường tín hiệu', [], macd('below_sig')),
  S('MACDCrossAboveZeroLine', 'macd', 'MACD cắt lên đường 0', [], macd('cross_above_zero')),
  S('MACDAboveZeroLine', 'macd', 'MACD đang ở trên đường 0', [], macd('above_zero')),
  S('MACDCrossBelowZeroLine', 'macd', 'MACD cắt xuống đường 0', [], macd('cross_below_zero')),
  S('MACDBelowZeroLine', 'macd', 'MACD đang ở dưới đường 0', [], macd('below_zero')),
  S('PullbackToSMA', 'pullback', 'Pullback về SMA({period}), vùng ±{tol}%, KL cạn: {dry}',
    [P_PB_MA, P_PB_TOL, P_PB_DRY], pullback('sma', false)),
  S('PullbackBounceSMA', 'pullback', 'Bật lên từ SMA({period}), vùng ±{tol}%, KL cạn: {dry}',
    [P_PB_MA, P_PB_TOL, P_PB_DRY], pullback('sma', true)),
  S('PullbackToTrendline', 'pullback', 'Pullback về trendline tăng {period}, vùng ±{tol}%, KL cạn: {dry}',
    [P_PB_TL, P_PB_TOL, P_PB_DRY], pullback('tl', false)),
  S('PullbackBounceTrendline', 'pullback', 'Bật lên từ trendline tăng {period}, vùng ±{tol}%, KL cạn: {dry}',
    [P_PB_TL, P_PB_TOL, P_PB_DRY], pullback('tl', true)),
  S('BreakDownTrendline', 'pullback', 'Vượt lên trendline giảm {period} ≥ {brk}%, KL ≥ TB20: {vol}',
    [P_PB_TL, P_BRK, P_BRK_VOL], breakDownLine),
  S('PullbackBrokenDownTrendline', 'pullback', 'Sau vượt trendline giảm {period}: pullback về ±{tol}%',
    [P_PB_TL, P_PB_TOL], retestDownLine(false)),
  S('BounceBrokenDownTrendline', 'pullback', 'Sau vượt trendline giảm {period}: bật lên ±{tol}%',
    [P_PB_TL, P_PB_TOL], retestDownLine(true)),
];
export const SIGNALS = Object.fromEntries(SIGNAL_LIST.map((s) => [s.id, s]));

// float(v) của Python cho tham số nhập tự do; null nếu không đổi được
function pyFloat(v) {
  if (typeof v === 'number') return Number.isNaN(v) ? null : v;
  if (typeof v === 'boolean') return v ? 1 : 0;
  if (typeof v !== 'string' || !v.trim()) return null;
  const s = v.trim();
  if (!/^[+-]?(\d+\.?\d*|\.\d+)(e[+-]?\d+)?$/i.test(s) && !/^[+-]?(inf|infinity|nan)$/i.test(s)) return null;
  const f = /^[+-]?inf/i.test(s) ? (s[0] === '-' ? -Infinity : Infinity) : Number(s);
  return Number.isNaN(f) ? null : f;
}

const sameChoice = (a, b) => (typeof a === 'number' && typeof b === 'number') ? a === b : a === b;

// {id, params} từ cài đặt (có thể cũ / sai) → bản sạch; null nếu không có tín hiệu đó
export function normalizeSignal(raw) {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw) || !SIGNALS[raw.id]) return null;
  const sig = SIGNALS[raw.id];
  const given = raw.params && typeof raw.params === 'object' && !Array.isArray(raw.params) ? raw.params : {};
  const params = {};
  for (const p of sig.params) {
    let v = p.id in given ? given[p.id] : p.default;
    let ok;
    if (p.free) {
      const f = pyFloat(v);
      ok = f !== null && Number.isFinite(f) && p.lo <= f && f <= p.hi;
      v = f;
    } else {
      const i = p.choices.findIndex((c) => sameChoice(c, v));
      ok = i >= 0;
      if (ok) v = p.choices[i];
    }
    params[p.id] = ok ? v : p.default;
  }
  if ((raw.id === 'ShortSMACrossAboveLongSMA' || raw.id === 'ShortSMACrossBelowLongSMA') && params.short >= params.long) {
    params.short = 5;
    params.long = 15;
  }
  return { id: sig.id, params };
}

// Giá trị tham số như người dùng thấy: '1w' → '1 tuần', 3.5 → '3.5', 70 → '70'
export function paramText(value) {
  return PERIOD_NAME[value] ?? String(value);
}

// Tên tín hiệu cho bộ chọn: chỗ tham số thay bằng '…'
export const signalTitle = (sig) => sig.label.replace(/\{\w+\}/g, '…');

// {nhóm: [[tên, 'metric' | 'signal', khoá]]}; trong mỗi nhóm cột số trước, tín hiệu sau
export function catalog() {
  const out = Object.fromEntries(GROUPS.map(([g]) => [g, []]));
  for (const [key, label, , group] of METRICS) out[group].push([label, 'metric', key]);
  for (const s of SIGNAL_LIST) out[s.group].push([signalTitle(s), 'signal', s.id]);
  return out;
}

// Câu mô tả 1 tín hiệu, vd 'Giá cắt lên SMA(5)'
export function describeSignal(sig) {
  const s = SIGNALS[sig && sig.id];
  if (!s) return String(sig && sig.id);
  const params = (sig && sig.params) || {};
  return s.label.replace(/\{(\w+)\}/g, (m, k) => (k in params ? paramText(params[k]) : m));
}

// Tín hiệu `sig` có đang đúng với thống kê `st` và giá hiện tại `lv` không. Thiếu số → false.
export function evalSignal(sig, st, lv) {
  const s = SIGNALS[sig && sig.id];
  if (!s || !valid(st, lv)) return false;
  const params = { ...((sig && sig.params) || {}) };
  if ('pct' in params) params.pct = params.pct / 100;      // lưu theo % (50), tính theo tỷ lệ (0.5)
  try {
    return !!s.fn(st, lv, params);
  } catch (e) {
    if (e instanceof Missing || e instanceof TypeError) return false;
    throw e;
  }
}
