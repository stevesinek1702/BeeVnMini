// Danh mục điều kiện lọc kiểu FireAnt Screener + công thức đánh giá — chép từ conditions.py.
//   • METRICS — một con số trên mỗi mã, lọc bằng ≥ ≤ hoặc "trong khoảng".
//   • SIGNALS — tín hiệu đúng / sai kèm tham số (giá cắt lên SMA(5), RSI vào vùng quá mua trên 70…).
// Số thống kê tính ở phiên đã đóng gần nhất (tech.js) rồi ghép giá hiện tại vào. Giá tính bằng nghìn đồng:
// khoảng đệm 0.05 ở EMA / Bollinger là 50đ (một bước giá), y như FireAnt.
// Tín hiệu có tham số tf (khung) = '15m' thì tính trên nến 15 phút đã chốt (lv.intra['15m']) thay cho nến ngày.
import * as tech from './tech.js';
import { fsum } from './pyfloat.js';

export const GROUPS = [['price', 'Giá'], ['volume', 'Khối lượng & dòng tiền'], ['ma', 'Đường trung bình'],
  ['rsi', 'RSI (14)'], ['mfi', 'MFI (14)'], ['stoch', 'Stochastic (14, 3, 3)'], ['osc', 'Williams %R & CCI'],
  ['bb', 'Bollinger Band (20)'], ['macd', 'MACD'], ['adx', 'ADX / DMI (14)'], ['sar', 'Parabolic SAR'],
  ['ichimoku', 'Ichimoku (9, 26, 52)'], ['pullback', 'Pullback & trendline']];

// [khoá, nhãn đầy đủ, nhãn ngắn trên tiêu đề cột, nhóm, kiểu hiển thị]
export const METRICS = [
  ['change1w', 'Thay đổi giá 1 tuần (%)', '% 1 tuần', 'price', 'pct'],
  ['change1m', 'Thay đổi giá 1 tháng (%)', '% 1 tháng', 'price', 'pct'],
  ['change3m', 'Thay đổi giá 3 tháng (%)', '% 3 tháng', 'price', 'pct'],
  ['change6m', 'Thay đổi giá 6 tháng (%)', '% 6 tháng', 'price', 'pct'],
  ['change1y', 'Thay đổi giá 1 năm (%)', '% 1 năm', 'price', 'pct'],
  ['fromHigh1m', 'Giá cách đỉnh 1 tháng (%)', '↓ đỉnh 1T', 'price', 'upct'],
  ['fromHigh3m', 'Giá cách đỉnh 3 tháng (%)', '↓ đỉnh 3T', 'price', 'upct'],
  ['fromHigh6m', 'Giá cách đỉnh 6 tháng (%)', '↓ đỉnh 6T', 'price', 'upct'],
  ['fromHigh1y', 'Giá cách đỉnh 1 năm (%)', '↓ đỉnh 1N', 'price', 'upct'],
  ['fromLow1m', 'Giá cách đáy 1 tháng (%)', '↑ đáy 1T', 'price', 'upct'],
  ['fromLow3m', 'Giá cách đáy 3 tháng (%)', '↑ đáy 3T', 'price', 'upct'],
  ['fromLow6m', 'Giá cách đáy 6 tháng (%)', '↑ đáy 6T', 'price', 'upct'],
  ['fromLow1y', 'Giá cách đáy 1 năm (%)', '↑ đáy 1N', 'price', 'upct'],
  ['upDays', 'Số phiên tăng giá liên tục', 'Phiên tăng', 'price', 'int'],
  ['downDays', 'Số phiên giảm giá liên tục', 'Phiên giảm', 'price', 'int'],
  ['upDaysBeforeDown', 'Số phiên tăng liên tục trước khi đảo chiều giảm', 'Tăng→giảm', 'price', 'int'],
  ['downDaysBeforeUp', 'Số phiên giảm liên tục trước khi đảo chiều tăng', 'Giảm→tăng', 'price', 'int'],
  ['activeBuyPct', '% KL khớp lệnh do bên mua chủ động', '% mua CĐ', 'volume', 'pct0'],
  ['avgVol5', 'KLTB 5 phiên', 'KLTB 5', 'volume', 'vol'],
  ['avgVol10', 'KLTB 10 phiên', 'KLTB 10', 'volume', 'vol'],
  ['avgVol20', 'KLTB 20 phiên', 'KLTB 20', 'volume', 'vol'],
  ['avgVol50', 'KLTB 50 phiên', 'KLTB 50', 'volume', 'vol'],
  ['avgVol100', 'KLTB 100 phiên', 'KLTB 100', 'volume', 'vol'],
  ['avgVol3m', 'KLTB 3 tháng', 'KLTB 3T', 'volume', 'vol'],
  ['avgValue20', 'GTTB 20 phiên (tỷ đồng)', 'GTTB 20', 'volume', 'bil'],
  ['foreignNetVol', 'KL nước ngoài mua ròng', 'KL NN ròng', 'volume', 'svol'],
  ['foreignNetValue', 'GT nước ngoài mua ròng (tỷ)', 'GT NN ròng', 'volume', 'sbil'],
  ['rsi14', 'RSI(14) hiện tại', 'RSI', 'rsi', 'num'],
  ['mfi14', 'MFI(14) hiện tại', 'MFI', 'mfi', 'num'],
  ['stochK', 'Stochastic %K (14, 3, 3)', '%K', 'stoch', 'num'],
  ['willR', 'Williams %R (14)', '%R', 'osc', 'num'],
  ['cci20', 'CCI (20)', 'CCI', 'osc', 'num'],
  ['bbWidth', 'Độ rộng dải Bollinger (20, 2) (% so với đường giữa)', 'BB rộng', 'bb', 'upct'],
  ['adx14', 'ADX (14)', 'ADX', 'adx', 'num'],
  ['atrPct', 'Biên độ ATR (14) so với giá (%)', 'ATR %', 'adx', 'upct'],
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
const TECH_AVGVOL = { avgVol5: 'v5', avgVol10: 'v10', avgVol20: 'v20', avgVol50: 'v50', avgVol100: 'v100',
  avgVol3m: 'v3m', avgValue20: 'gv20' };
const TECH_DIST = { distSMA20: 20, distSMA50: 50 };
// Phiên vượt trendline giảm gần nhất (0 = hôm nay): cần quét lùi tech.lastBreak — nặng, chỉ tính khi có tiêu chí dùng.
export const BREAK_METRIC_KEYS = { brkTL3m: '3m', brkTL6m: '6m' };
export const BREAK_COMPANIONS = Object.fromEntries(Object.keys(BREAK_METRIC_KEYS).map((k) => [k, [k + 'Px', k + 'Pct']]));
export const BREAK_ALL_KEYS = {};      // cột → cột chính của nhóm
for (const [grp, ks] of Object.entries(BREAK_COMPANIONS)) for (const k of [grp, ...ks]) BREAK_ALL_KEYS[k] = grp;
// Cột tính từ chỉ báo + phiên hôm nay (giá / cao / thấp / KL hiện tại): indicatorMetrics
export const INDICATOR_KEYS = ['rsi14', 'mfi14', 'stochK', 'willR', 'cci20', 'bbWidth', 'adx14', 'atrPct',
  ...['High', 'Low'].flatMap((s) => ['1m', '3m', '6m', '1y'].map((p) => `from${s}${p}`))];
export const TECH_METRIC_KEYS = [...Object.keys(TECH_PERIOD), ...Object.keys(TECH_AVGVOL), ...Object.keys(TECH_DIST),
  ...Object.keys(BREAK_ALL_KEYS), ...INDICATOR_KEYS, 'upDays', 'downDays', 'upDaysBeforeDown', 'downDaysBeforeUp'];

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
export const TF_NAME = { '15m': '15 phút', D: 'ngày' };
const P_TF = P('tf', 'khung', Object.keys(TF_NAME), '15m');
const P_RSI_LOOK = P('look', 'đáy trong (nến)', [8, 12, 16, 20, 24, tech.RSI_KEEP], 16);
const P_MA_STATE = P('period', 'kỳ (phiên)', MA_PERIODS, 20);
const P_STO_UP = P('level', 'ngưỡng quá mua', [70, 75, 80, 85, 90], 80, true, 0, 100);
const P_STO_DOWN = P('level', 'ngưỡng quá bán', [10, 15, 20, 25, 30], 20, true, 0, 100);
const P_WR_DOWN = P('level', 'ngưỡng quá bán (−)', [70, 80, 90], 80, true, 0, 100);
const P_WR_UP = P('level', 'ngưỡng quá mua (−)', [10, 20, 30], 20, true, 0, 100);
const P_CCI = P('level', 'ngưỡng (±)', [100, 150, 200], 100, true, 0, 500);
const P_ADX = P('level', 'ADX tối thiểu', [20, 25, 30, 40], 25, true, 0, 100);
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
export function rsiNow(st, last) {
  const ag = st.ag, al = st.al, lc = st.lc;
  if (!nz(ag) || !nz(al) || !nz(lc)) return [null, null];
  const d = last - lc;
  return [tech.rsiOf(ag, al), tech.rsiOf(ag * 13 + Math.max(d, 0), al * 13 + Math.max(-d, 0))];
}

const rsi = (kind) => (st, lv, p) => {
  const [prev, live] = rsiNow(st, lv.last);
  if (live === null) return false;
  const a = p.level;
  return { cross_up: prev <= a && a < live, cross_down: prev >= a && a > live, above: live > a, below: live < a }[kind];
};

// RSI tạo đáy (luật Long của anh bên hệ phái sinh): trong `look` nến gần nhất RSI(14) từng ≤ ngưỡng quá bán, nay đã
// thoát lên trên ngưỡng + RSI trên Signal (WMA14 của RSI) + giá đóng cửa trên MA10 (SMA10).
// Khung ngày ghép giá hiện tại như các tín hiệu khác; khung 15 phút xét nến đã chốt gần nhất (xem _rsi_bottom).
function rsiBottom(st, lv, p) {
  const rs = [...(st.rs || [])];
  let price, ma;
  if (p.tf === 'D') {
    rs.push(rsiNow(st, lv.last)[1]);
    price = lv.last;
    ma = smaLive(st, lv.last, 10);
  } else {
    price = st.lc;
    ma = st.p10;
  }
  const n = tech.RSI_SIGNAL_N, k = p.look;
  if (rs.some((r) => !nz(r)) || rs.length < Math.max(n, k) || !truthy(price) || !truthy(ma)) return false;
  const signal = fsum(rs.slice(-n).map((r, i) => (i + 1) * r)) / (n * (n + 1) / 2);    // WMA: nến mới nhất nặng nhất
  const last = rs[rs.length - 1];
  return Math.min(...rs.slice(-k)) <= p.level && p.level < last && last > signal && price > ma;
}

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

// --- Chỉ báo bổ sung (tech.js): mọi số ghép phiên hôm nay = giá / cao / thấp hiện tại ---
// [cao nhất, thấp nhất] của phiên hôm nay tính cả giá hiện tại; quote thiếu cao / thấp thì lấy giá hiện tại
function hl(lv) {
  const last = lv.last;
  return [Math.max(lv.high || last, last), Math.min(lv.low || last, last)];
}

export function emaLive(st, last, n) {
  const e = st[`e${n}`];
  return truthy(e) ? (2 * last + (n - 1) * e) / (n + 1) : null;
}

const priceVsMa = (kind, above) => (st, lv, p) => {
  const line = (kind === 'sma' ? smaLive : emaLive)(st, lv.last, p.period);
  return truthy(line) && (above ? lv.last > line : lv.last < line);
};

function smaAbove(st, lv, p) {
  const s = smaLive(st, lv.last, p.short), l = smaLive(st, lv.last, p.long);
  return truthy(s) && truthy(l) && s > l;
}

const emaPair = (up) => (st, lv, p) => {
  const es = st[`e${p.short}`], el = st[`e${p.long}`];
  const s = emaLive(st, lv.last, p.short), l = emaLive(st, lv.last, p.long);
  if (!(truthy(es) && truthy(el) && truthy(s) && truthy(l))) return false;
  return up ? (es <= el && s > l) : (es >= el && s < l);
};

// Parabolic SAR: phiên hôm nay (giá cao / thấp hiện tại) đi qua SAR là đảo chiều (tech.sarStep)
const sar = (kind) => (st, lv) => {
  if (['sart', 'sar', 'sep', 'saf'].some((k) => !nz(st[k]))) return false;
  const [hi, lo] = hl(lv);
  const [, , , up, flip] = tech.sarStep(st.sar, st.sep, st.saf, st.sart === 1, hi, lo);
  if (kind === 'flip_up') return flip && up;
  if (kind === 'flip_down') return flip && !up;
  return kind === 'up' ? up : !up;
};

// %K thô (14) tính cả phiên hôm nay; null nếu thiếu số / cao nhất = thấp nhất
export function rawKNow(st, lv) {
  let hh = st.hh13, ll = st.ll13;
  if (!nz(hh) || !nz(ll)) return null;
  const [hi, lo] = hl(lv);
  hh = Math.max(hh, hi);
  ll = Math.min(ll, lo);
  return hh > ll ? (lv.last - ll) / (hh - ll) * 100 : null;
}

// [%K, %D phiên đóng gần nhất, %K, %D tính cả phiên hôm nay] — Stochastic chậm 14, 3, 3; null nếu thiếu số
export function stochNow(st, lv) {
  const kr = st.skr, ks = st.sks, d = st.skd;
  const raw = rawKNow(st, lv);
  if (raw === null || !nz(d) || !kr || !ks || kr.some((x) => !nz(x)) || ks.some((x) => !nz(x))) return null;
  const k = (kr[0] + kr[1] + raw) / 3;
  return [ks[1], d, k, (ks[0] + ks[1] + k) / 3];
}

const stoch = (kind) => (st, lv, p) => {
  const r = stochNow(st, lv);
  if (r === null) return false;
  const [k0, d0, k1, d1] = r;
  if (kind === 'cross_up') return k0 <= d0 && k1 > d1;
  if (kind === 'cross_down') return k0 >= d0 && k1 < d1;
  const a = p.level;
  if (kind === 'cross_up_os') return k0 <= d0 && k1 > d1 && k0 <= a;
  if (kind === 'exit_os') return k0 <= a && a < k1;
  if (kind === 'exit_ob') return k0 >= a && a > k1;
  return kind === 'below' ? k1 < a : k1 > a;
};

// Williams %R (14) = %K thô − 100. Thoát quá bán: cắt lên −level; thoát quá mua: cắt xuống −level
const willr = (kind) => (st, lv, p) => {
  const kr = st.skr, raw = rawKNow(st, lv);
  if (raw === null || !kr || !nz(kr[kr.length - 1])) return false;
  const w0 = kr[kr.length - 1] - 100, w1 = raw - 100, a = -p.level;
  return kind === 'exit_os' ? (w0 <= a && a < w1) : (w0 >= a && a > w1);
};

// [CCI(20) phiên đóng gần nhất, CCI tính cả phiên hôm nay]; null nếu thiếu số
export function cciNow(st, lv) {
  const tps = st.tp19, prev = st.cci;
  if (!tps || tps.length < tech.CCI_N - 1 || !nz(prev)) return null;
  const [hi, lo] = hl(lv);
  const cur = tech.cci([...tps, (hi + lo + lv.last) / 3]);
  return cur === null ? null : [prev, cur];
}

const cciSig = (kind) => (st, lv, p) => {
  const r = cciNow(st, lv);
  if (r === null) return false;
  const [c0, c1] = r, a = p.level;
  if (kind === 'exit_os') return c0 <= -a && -a < c1;
  if (kind === 'exit_ob') return c0 >= a && a > c1;
  return kind === 'above' ? c1 > a : c1 < -a;
};

// [+DI, −DI phiên đóng gần nhất, +DI, −DI, ADX, ATR tính cả phiên hôm nay]; null nếu thiếu số
export function dmiNow(st, lv) {
  if (['atr', 'pdm', 'mdm', 'dxa', 'lh', 'll', 'lc'].some((k) => !nz(st[k]))) return null;
  const [hi, lo] = hl(lv);
  const n = tech.DMI_N;
  const [p, m, tr] = tech.dmTr([null, null, st.lh, st.ll, st.lc], [null, null, hi, lo, lv.last]);
  const atr = (st.atr * (n - 1) + tr) / n;
  const pdm = (st.pdm * (n - 1) + p) / n;
  const mdm = (st.mdm * (n - 1) + m) / n;
  const pd1 = tech.di(pdm, atr), md1 = tech.di(mdm, atr);
  const adx = 100 * (st.dxa * (n - 1) + tech.dxFrac(pd1, md1)) / n;
  return [tech.di(st.pdm, st.atr), tech.di(st.mdm, st.atr), pd1, md1, adx, atr];
}

const dmi = (kind) => (st, lv, p) => {
  const r = dmiNow(st, lv);
  if (r === null) return false;
  const [pd0, md0, pd1, md1, adx] = r;
  if (kind === 'cross_up') return pd0 <= md0 && pd1 > md1;
  if (kind === 'cross_down') return pd0 >= md0 && pd1 < md1;
  if (kind === 'adx') return adx > p.level;
  return pd1 > md1 && adx > p.level;            // xu hướng tăng mạnh
};

// [OBV, TB 20 của OBV ở phiên đóng gần nhất, OBV, TB 20 tính cả hôm nay]; KL hôm nay = KL dự kiến cả phiên
export function obvNow(st, lv) {
  const obv = st.obv, s19 = st.ob19, m = st.obm, lc = st.lc;
  if (![obv, s19, m, lc].every(nz)) return null;
  const vol = lv.est || lv.volume || 0, last = lv.last;
  const cur = obv + (last > lc ? vol : (last < lc ? -vol : 0));
  return [obv, m, cur, (s19 + cur) / tech.OBV_N];
}

const obvSig = (kind) => (st, lv) => {
  const r = obvNow(st, lv);
  if (r === null) return false;
  const [o0, m0, o1, m1] = r;
  if (kind === 'cross_up') return o0 <= m0 && o1 > m1;
  if (kind === 'cross_down') return o0 >= m0 && o1 < m1;
  return o1 > m1;
};

// Mây hôm nay = Span A / B tính 25 phiên trước (st.ca), mây hôm qua st.cb; Tenkan / Kijun ghép phiên hôm nay
const ichimoku = (kind) => (st, lv) => {
  if (['tk', 'kj', 'ih8', 'il8', 'ih25', 'il25', 'ca', 'cb', 'lc'].some((k) => !nz(st[k]))) return false;
  const last = lv.last, ca = st.ca, cb = st.cb;
  if (kind === 'above') return last > Math.max(...ca);
  if (kind === 'below') return last < Math.min(...ca);
  if (kind === 'break_up') return st.lc <= Math.max(...cb) && last > Math.max(...ca);
  const [hi, lo] = hl(lv);
  const tk = (Math.max(st.ih8, hi) + Math.min(st.il8, lo)) / 2;
  const kj = (Math.max(st.ih25, hi) + Math.min(st.il25, lo)) / 2;
  return kind === 'tk_up' ? (st.tk <= st.kj && tk > kj) : (st.tk >= st.kj && tk < kj);
};

// Các cột số tính từ chỉ báo + phiên hôm nay (INDICATOR_KEYS) — xem indicator_metrics của conditions.py
export function indicatorMetrics(st, lv) {
  const out = Object.fromEntries(INDICATOR_KEYS.map((k) => [k, null]));
  if (!valid(st, lv)) return out;
  const last = lv.last;
  out.rsi14 = rsiNow(st, last)[1];
  out.mfi14 = mfiNow(st, lv)[1];
  const s = stochNow(st, lv);
  out.stochK = s ? s[2] : null;
  const raw = rawKNow(st, lv);
  out.willR = raw === null ? null : raw - 100;
  const c = cciNow(st, lv);
  out.cci20 = c ? c[1] : null;
  const b = bbNow(st, last, 2);
  if (b) {
    const mid = (st.p19 * 19 + last) / 20;
    out.bbWidth = mid ? (b[1][0] - b[1][1]) / mid * 100 : null;
  }
  const d = dmiNow(st, lv);
  if (d) {
    out.adx14 = d[4];
    out.atrPct = d[5] / last * 100;
  }
  const [hi, lo] = hl(lv);
  for (const per of ['1m', '3m', '6m', '1y']) {
    let h = st['hi' + per], l = st['lo' + per];
    if (truthy(h)) {
      h = Math.max(h, hi);
      out['fromHigh' + per] = (h - last) / h * 100;
    }
    if (truthy(l)) {
      l = Math.min(l, lo);
      out['fromLow' + per] = l > 0 ? (last - l) / l * 100 : null;
    }
  }
  return out;
}

const S = (id, group, label, params, fn) => ({ id, group, label, params, fn });

export const SIGNAL_LIST = [
  S('AbovePreviousHigh', 'price', 'Giá vượt đỉnh {period}', [P_HIGHLOW], aboveHigh),
  S('BelowPreviousLow', 'price', 'Giá thủng đáy {period}', [P_HIGHLOW], belowLow),
  S('EstimatedVolumeSurge', 'volume', 'KL dự kiến vượt TB {period} phiên tối thiểu {pct}%',
    [P('period', 'TB (phiên)', MA_PERIODS, 5), P('pct', 'vượt tối thiểu (%)', [10, 20, 30, 50, 70, 100, 150, 200, 300], 50, true, 1, 1000)],
    estVolumeSurge),
  S('OBVCrossAboveMA', 'volume', 'OBV cắt lên đường TB 20 phiên của OBV', [], obvSig('cross_up')),
  S('OBVCrossBelowMA', 'volume', 'OBV cắt xuống đường TB 20 phiên của OBV', [], obvSig('cross_down')),
  S('OBVAboveMA', 'volume', 'OBV đang trên đường TB 20 phiên (dòng tiền vào)', [], obvSig('above')),
  S('PriceCrossAboveSMA', 'ma', 'Giá cắt lên SMA({period})', [P_MA], smaCross(true)),
  S('PriceCrossBelowSMA', 'ma', 'Giá cắt xuống SMA({period})', [P_MA], smaCross(false)),
  S('PriceCrossAboveEMA', 'ma', 'Giá cắt lên EMA({period})', [P_MA], emaCross(true)),
  S('PriceCrossBelowEMA', 'ma', 'Giá cắt xuống EMA({period})', [P_MA], emaCross(false)),
  S('ShortSMACrossAboveLongSMA', 'ma', 'SMA({short}) cắt lên SMA({long})',
    [P('short', 'SMA ngắn', [5, 10, 15, 20, 50], 5), P('long', 'cắt lên SMA dài', [15, 20, 45, 50, 100, 200], 15)], smaPair(true)),
  S('ShortSMACrossBelowLongSMA', 'ma', 'SMA({short}) cắt xuống SMA({long})',
    [P('short', 'SMA ngắn', [5, 10, 15, 20, 50], 5), P('long', 'cắt xuống SMA dài', [15, 20, 45, 50, 100, 200], 15)], smaPair(false)),
  S('PriceAboveSMA', 'ma', 'Giá đang trên SMA({period})', [P_MA_STATE], priceVsMa('sma', true)),
  S('PriceBelowSMA', 'ma', 'Giá đang dưới SMA({period})', [P_MA_STATE], priceVsMa('sma', false)),
  S('PriceAboveEMA', 'ma', 'Giá đang trên EMA({period})', [P_MA_STATE], priceVsMa('ema', true)),
  S('PriceBelowEMA', 'ma', 'Giá đang dưới EMA({period})', [P_MA_STATE], priceVsMa('ema', false)),
  S('ShortSMAAboveLongSMA', 'ma', 'SMA({short}) đang trên SMA({long})',
    [P('short', 'SMA ngắn', [5, 10, 15, 20, 50], 50), P('long', 'trên SMA dài', [15, 20, 45, 50, 100, 200], 200)], smaAbove),
  S('ShortEMACrossAboveLongEMA', 'ma', 'EMA({short}) cắt lên EMA({long})',
    [P('short', 'EMA ngắn', [5, 10, 15, 20, 50], 10), P('long', 'cắt lên EMA dài', [15, 20, 45, 50, 100, 200], 20)], emaPair(true)),
  S('ShortEMACrossBelowLongEMA', 'ma', 'EMA({short}) cắt xuống EMA({long})',
    [P('short', 'EMA ngắn', [5, 10, 15, 20, 50], 10), P('long', 'cắt xuống EMA dài', [15, 20, 45, 50, 100, 200], 20)], emaPair(false)),
  S('RSICrossAboveOverBoughtLine', 'rsi', 'RSI(14) đi vào vùng quá mua (trên {level})', [P_RSI_UP], rsi('cross_up')),
  S('RSICrossBelowOverBoughtLine', 'rsi', 'RSI(14) thoát khỏi vùng quá mua (trên {level})', [P_RSI_UP], rsi('cross_down')),
  S('RSIAboveOverBoughtLine', 'rsi', 'RSI(14) đang trong vùng quá mua (trên {level})', [P_RSI_UP], rsi('above')),
  S('RSICrossBelowOverSoldLine', 'rsi', 'RSI(14) đi vào vùng quá bán (dưới {level})', [P_RSI_DOWN], rsi('cross_down')),
  S('RSICrossAboveOverSoldLine', 'rsi', 'RSI(14) thoát khỏi vùng quá bán (dưới {level})', [P_RSI_DOWN], rsi('cross_up')),
  S('RSIBelowOverSoldLine', 'rsi', 'RSI(14) đang trong vùng quá bán (dưới {level})', [P_RSI_DOWN], rsi('below')),
  S('RSIBottom', 'rsi', 'RSI tạo đáy khung {tf}: thoát quá bán {level} (đáy trong {look} nến), RSI trên Signal, '
    + 'giá trên MA10', [P_TF, P_RSI_DOWN, P_RSI_LOOK], rsiBottom),
  S('MFICrossAboveOverBoughtLine', 'mfi', 'MFI(14) đi vào vùng quá mua (trên {level})', [P_MFI_UP], mfi('cross_up')),
  S('MFICrossBelowOverBoughtLine', 'mfi', 'MFI(14) thoát khỏi vùng quá mua (trên {level})', [P_MFI_UP], mfi('cross_down')),
  S('MFIAboveOverBoughtLine', 'mfi', 'MFI(14) đang trong vùng quá mua (trên {level})', [P_MFI_UP], mfi('above')),
  S('MFICrossBelowOverSoldLine', 'mfi', 'MFI(14) đi vào vùng quá bán (dưới {level})', [P_MFI_DOWN], mfi('cross_down')),
  S('MFICrossAboveOverSoldLine', 'mfi', 'MFI(14) thoát khỏi vùng quá bán (dưới {level})', [P_MFI_DOWN], mfi('cross_up')),
  S('MFIBelowOverSoldLine', 'mfi', 'MFI(14) đang trong vùng quá bán (dưới {level})', [P_MFI_DOWN], mfi('below')),
  S('StochKCrossAboveD', 'stoch', 'Stochastic: %K cắt lên %D', [], stoch('cross_up')),
  S('StochKCrossBelowD', 'stoch', 'Stochastic: %K cắt xuống %D', [], stoch('cross_down')),
  S('StochKCrossAboveDOverSold', 'stoch', 'Stochastic: %K cắt lên %D từ vùng quá bán (dưới {level})', [P_STO_DOWN],
    stoch('cross_up_os')),
  S('StochCrossAboveOverSoldLine', 'stoch', 'Stochastic thoát khỏi vùng quá bán (dưới {level})', [P_STO_DOWN], stoch('exit_os')),
  S('StochCrossBelowOverBoughtLine', 'stoch', 'Stochastic thoát khỏi vùng quá mua (trên {level})', [P_STO_UP], stoch('exit_ob')),
  S('StochBelowOverSoldLine', 'stoch', 'Stochastic đang trong vùng quá bán (dưới {level})', [P_STO_DOWN], stoch('below')),
  S('StochAboveOverBoughtLine', 'stoch', 'Stochastic đang trong vùng quá mua (trên {level})', [P_STO_UP], stoch('above')),
  S('WillRCrossAboveOverSoldLine', 'osc', 'Williams %R thoát vùng quá bán (cắt lên −{level})', [P_WR_DOWN], willr('exit_os')),
  S('WillRCrossBelowOverBoughtLine', 'osc', 'Williams %R thoát vùng quá mua (cắt xuống −{level})', [P_WR_UP], willr('exit_ob')),
  S('CCICrossAboveOverSoldLine', 'osc', 'CCI(20) thoát vùng quá bán (cắt lên −{level})', [P_CCI], cciSig('exit_os')),
  S('CCICrossBelowOverBoughtLine', 'osc', 'CCI(20) thoát vùng quá mua (cắt xuống +{level})', [P_CCI], cciSig('exit_ob')),
  S('CCIAboveOverBoughtLine', 'osc', 'CCI(20) đang trên +{level}', [P_CCI], cciSig('above')),
  S('CCIBelowOverSoldLine', 'osc', 'CCI(20) đang dưới −{level}', [P_CCI], cciSig('below')),
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
  S('ADXAboveLevel', 'adx', 'ADX(14) trên {level} (có xu hướng mạnh)', [P_ADX], dmi('adx')),
  S('DIPlusCrossAboveDIMinus', 'adx', '+DI cắt lên −DI', [], dmi('cross_up')),
  S('DIPlusCrossBelowDIMinus', 'adx', '+DI cắt xuống −DI', [], dmi('cross_down')),
  S('ADXStrongUptrend', 'adx', 'Xu hướng tăng mạnh: +DI trên −DI, ADX trên {level}', [P_ADX], dmi('strong_up')),
  S('SARFlipUp', 'sar', 'Parabolic SAR đảo chiều tăng (giá vượt lên SAR)', [], sar('flip_up')),
  S('SARFlipDown', 'sar', 'Parabolic SAR đảo chiều giảm (giá thủng SAR)', [], sar('flip_down')),
  S('SARUptrend', 'sar', 'Parabolic SAR đang báo xu hướng tăng (SAR dưới giá)', [], sar('up')),
  S('SARDowntrend', 'sar', 'Parabolic SAR đang báo xu hướng giảm (SAR trên giá)', [], sar('down')),
  S('IchimokuAboveCloud', 'ichimoku', 'Giá đang trên mây Ichimoku', [], ichimoku('above')),
  S('IchimokuBelowCloud', 'ichimoku', 'Giá đang dưới mây Ichimoku', [], ichimoku('below')),
  S('IchimokuBreakAboveCloud', 'ichimoku', 'Giá vượt lên trên mây Ichimoku', [], ichimoku('break_up')),
  S('IchimokuTenkanCrossAboveKijun', 'ichimoku', 'Tenkan cắt lên Kijun', [], ichimoku('tk_up')),
  S('IchimokuTenkanCrossBelowKijun', 'ichimoku', 'Tenkan cắt xuống Kijun', [], ichimoku('tk_down')),
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
  if ('short' in params && 'long' in params && params.short >= params.long) {
    [params.short, params.long] = sig.params.map((p) => p.default);     // đường ngắn phải ngắn hơn đường dài
  }
  return { id: sig.id, params };
}

// Giá trị tham số như người dùng thấy: '1w' → '1 tuần', '15m' → '15 phút', 3.5 → '3.5', 70 → '70'
export function paramText(value) {
  return TF_NAME[value] ?? PERIOD_NAME[value] ?? String(value);
}

// Khung nến tín hiệu cần: 'D' (nến ngày — mọi tín hiệu không có tham số khung) hoặc '15m'
export const signalTf = (sig) => ((sig && sig.params) || {}).tf ?? 'D';

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

// Tín hiệu `sig` có đang đúng với thống kê `st` và giá hiện tại `lv` không. lv.intra = {'15m': thống kê nến 15 phút}
// khi có tiêu chí cần. Thiếu số → false.
export function evalSignal(sig, st, lv) {
  const s = SIGNALS[sig && sig.id];
  if (!s) return false;
  if (signalTf(sig) !== 'D') st = ((lv && lv.intra) || {})[signalTf(sig)];
  if (!valid(st, lv)) return false;
  const params = { ...((sig && sig.params) || {}) };
  if ('pct' in params) params.pct = params.pct / 100;      // lưu theo % (50), tính theo tỷ lệ (0.5)
  try {
    return !!s.fn(st, lv, params);
  } catch (e) {
    if (e instanceof Missing || e instanceof TypeError) return false;
    throw e;
  }
}
