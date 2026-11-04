// Chỉ báo kỹ thuật tính từ nến ngày — chép từ tech.py của bản Python, giữ đúng thứ tự phép tính
// để số ra khớp từng chữ số (xem pyfloat.js). Mọi con số tính trên các phiên ĐÃ ĐÓNG (bỏ nến hôm nay).
// Riêng khung 15 phút (intradayStats): xét nến đã chốt gần nhất, không ghép giá hiện tại.
// Giá tính bằng nghìn đồng; khối lượng bằng cổ phiếu. Không dính giao diện, không dính mạng.
import { fsum, fmean, isum, imean, pyRoundTo } from './pyfloat.js';

export const PRICE_AVG_N = [4, 5, 9, 10, 14, 15, 19, 20, 44, 45, 49, 50, 99, 100, 199, 200];
export const VOL_AVG_N = [4, 5, 9, 10, 14, 19, 20, 44];
export const EMA_N = [5, 10, 15, 20, 45, 50, 100, 200];
export const VERSION = 9;        // cùng số với tech.VERSION của Python: đổi khi thêm số thống kê mới → bộ đệm cũ bị bỏ
export const PERIODS = { '1w': ['d', 7], '2w': ['d', 14], '1m': ['m', 1], '3m': ['m', 3], '6m': ['m', 6], '1y': ['m', 12] };
export const MIN_BARS = 20;

// Pullback về SMA: kỳ → [số phiên tìm đỉnh nhịp tăng, đỉnh phải cách SMA tối thiểu]; SMA dốc lên = hôm qua > 10 phiên trước.
export const PB_SMA = { 10: [15, 0.04], 20: [20, 0.05], 50: [30, 0.08] };
export const PB_SLOPE = 10;
// Trendline tự vẽ trên GIÁ ĐÓNG CỬA — luật đầy đủ ghi ở đầu tech.py
export const TL_WINDOWS = { '3m': 60, '6m': 120 };
export const TL_PIVOT = 3, TL_MIN_GAP = 10, TL_MAX_SLOPE = 0.01;
export const TL_TOL = 0.02, TL_EXT = 0.05, TL_RECENT = 10, TL_TOUCHES = 3;
export const TL_MIN_BARS = 40;
export const BREAK_DAYS = 20, BREAK_UP = 0.01;
// RSI tạo đáy (luật Long của anh bên hệ phái sinh): Signal = WMA(14) của RSI(14); giữ RSI của RSI_KEEP nến đã đóng gần nhất
export const RSI_SIGNAL_N = 14, RSI_KEEP = 30;
// Nến 15 phút (dchart ghi giờ MỞ nến): các buổi khớp lệnh theo phút trong ngày, giờ VN. Nến ATC của HOSE mang giờ 14:45
// → buổi chiều tính tới 15:00 (khung 14:45 coi như chưa chốt) cho chắc nến ATC đã lên dchart.
export const INTRA_MIN = 15;
export const INTRA_SESSIONS = [[9 * 60, 11 * 60 + 30], [13 * 60, 15 * 60]];
export const INTRA_MIN_BARS = 60;     // mã ít khớp lệnh thì nến thưa, RSI 15 phút vô nghĩa → không tính
// Khung trong phiên: khung → [nến nguồn tải về (phút), số phút mỗi nến]. Máy chủ chỉ có nến 15 / 60 phút: 30 phút gộp từ
// nến 15 phút, 2 / 4 giờ gộp từ nến 1 giờ, tính từ 9:00 như TradingView (4 giờ = 1 nến buổi sáng + 1 nến buổi chiều).
export const INTRA_TFS = { '15m': [15, 15], '30m': [15, 30], '1h': [60, 60], '2h': [60, 120], '4h': [60, 240] };
export const INTRA_FEED_DAYS = { 15: 30, 60: 90 };      // số ngày lịch tải về cho mỗi loại nến nguồn
// Chỉ báo bổ sung (xem tech.py): Parabolic SAR như ta.sar của TradingView; Stochastic chậm (14, 3, 3), Williams %R;
// CCI (20); ADX / DMI (14) như ta.dmi; OBV + TB 20 phiên; Ichimoku (9, 26, 52), mây dời tới 25 phiên.
export const SAR_STEP = 0.02, SAR_MAX = 0.2;
export const STOCH_N = 14, CCI_N = 20, DMI_N = 14, OBV_N = 20;
export const ICHI_T = 9, ICHI_K = 26, ICHI_B = 52, ICHI_SHIFT = 25;

const DAY_MS = 86400000;
const VN_MS = 7 * 3600000;

function daysInMonth(y, m) {
  return new Date(Date.UTC(y, m, 0)).getUTCDate();
}

// '2026-10-15' lùi n ngày / n tháng. Lùi tháng mà ngày không có (31/3 → 28/2) thì lấy ngày cuối tháng.
export function minusPeriod(date, kind, n) {
  let [y, m, d] = date.split('-').map(Number);
  if (kind === 'd') return new Date(Date.UTC(y, m - 1, d) - n * DAY_MS).toISOString().slice(0, 10);
  m -= n;
  while (m < 1) { m += 12; y -= 1; }
  return `${String(y).padStart(4, '0')}-${String(m).padStart(2, '0')}-${String(Math.min(d, daysInMonth(y, m))).padStart(2, '0')}`;
}

const isNum = (v) => v !== null && v !== undefined;

// Nến dchart {t,o,h,l,c,v} → [ngày, mở, cao, thấp, đóng, KL] các phiên đã đóng, cũ → mới.
export function closedBars(bars, today, dateOf) {
  if (!bars || typeof bars !== 'object' || bars.s !== 'ok') return [];
  const cols = ['t', 'o', 'h', 'l', 'c', 'v'].map((k) => bars[k]);
  if (!cols.every(Array.isArray) || new Set(cols.map((c) => c.length)).size !== 1) return [];
  const out = [];
  for (let i = 0; i < cols[0].length; i++) {
    const [t, o, h, lo, c, v] = cols.map((col) => col[i]);
    const day = dateOf(t);
    if (day >= today || ![o, h, lo, c, v].every(isNum) || c <= 0) continue;
    out.push([day, o, h, lo, c, v]);
  }
  return out;
}

// Độ lệch chuẩn tổng thể (chia n). (x − m)**2 của Python = (x − m)·(x − m).
function std(a) {
  const m = fmean(a);
  return Math.sqrt(fsum(a.map((x) => (x - m) * (x - m))) / a.length);
}

export function emaLast(values, n) {
  const a = 2 / (n + 1);
  let e = values[0];
  for (let i = 1; i < values.length; i++) e = a * values[i] + (1 - a) * e;
  return e;
}

// [avgGain, avgLoss] kiểu Wilder tại phiên cuối
export function wilderRsiParts(closes, n = 14) {
  if (closes.length < n + 1) return [null, null];
  const diffs = [];
  for (let i = 1; i < closes.length; i++) diffs.push(closes[i] - closes[i - 1]);
  let ag = fsum(diffs.slice(0, n).map((d) => Math.max(d, 0))) / n;
  let al = fsum(diffs.slice(0, n).map((d) => Math.max(-d, 0))) / n;
  for (const d of diffs.slice(n)) {
    ag = (ag * (n - 1) + Math.max(d, 0)) / n;
    al = (al * (n - 1) + Math.max(-d, 0)) / n;
  }
  return [ag, al];
}

export const rsiOf = (gain, loss) => (loss === 0 ? 100 : 100 - 100 / (1 + gain / loss));

// RSI Wilder(n) tại `keep` nến cuối (cũ → mới), cùng cách tính wilderRsiParts; [] nếu chưa đủ n+1 nến
export function rsiTail(closes, keep = RSI_KEEP, n = 14) {
  if (closes.length < n + 1) return [];
  const diffs = [];
  for (let i = 1; i < closes.length; i++) diffs.push(closes[i] - closes[i - 1]);
  let ag = fsum(diffs.slice(0, n).map((d) => Math.max(d, 0))) / n;
  let al = fsum(diffs.slice(0, n).map((d) => Math.max(-d, 0))) / n;
  const out = [rsiOf(ag, al)];
  for (const d of diffs.slice(n)) {
    ag = (ag * (n - 1) + Math.max(d, 0)) / n;
    al = (al * (n - 1) + Math.max(-d, 0)) / n;
    out.push(rsiOf(ag, al));
  }
  return out.slice(-keep);
}

// MFI: [dòng tiền dương n−1 phiên cuối, dòng tiền âm n−1 phiên cuối, MFI n phiên, giá điển hình phiên cuối]
export function moneyFlow(bars, n = 14) {
  if (bars.length < n + 1) return [null, null, null, null];
  const tp = bars.map((r) => (r[2] + r[3] + r[4]) / 3);
  const pos = [], neg = [];
  for (let i = 1; i < bars.length; i++) {
    const mf = tp[i] * bars[i][5];
    pos.push(tp[i] > tp[i - 1] ? mf : 0);
    neg.push(tp[i] < tp[i - 1] ? mf : 0);
  }
  const p13 = fsum(pos.slice(-(n - 1))), n13 = fsum(neg.slice(-(n - 1)));
  const p14 = fsum(pos.slice(-n)), n14 = fsum(neg.slice(-n));
  const mfi = n14 === 0 ? 100 : 100 - 100 / (1 + p14 / n14);
  return [p13, n13, mfi, tp[tp.length - 1]];
}

// Một phiên Parabolic SAR như ta.sar của TradingView → [SAR chưa kẹp, EP, af, chiều tăng?, vừa đảo chiều?]
export function sarStep(sar, ep, af, up, h, lo) {
  sar = sar + af * (ep - sar);
  if (up && sar > lo) return [Math.max(h, ep), lo, SAR_STEP, false, true];
  if (!up && sar < h) return [Math.min(lo, ep), h, SAR_STEP, true, true];
  if (up && h > ep) {
    ep = h;
    af = Math.min(af + SAR_STEP, SAR_MAX);
  } else if (!up && lo < ep) {
    ep = lo;
    af = Math.min(af + SAR_STEP, SAR_MAX);
  }
  return [sar, ep, af, up, false];
}

// Parabolic SAR (0.02, 0.2) tại phiên cuối → [chiều: 1 tăng / −1 giảm, SAR đã kẹp, EP, af] (xem parabolic_sar)
export function parabolicSar(rows) {
  if (rows.length < 3) return [null, null, null, null];
  let up = rows[1][4] > rows[0][4];
  let ep = up ? rows[1][2] : rows[1][3];
  let sar = up ? rows[0][3] : rows[0][2];
  let af = SAR_STEP;
  for (let i = 1; i < rows.length; i++) {
    const h = rows[i][2], lo = rows[i][3];
    if (i === 1) {                      // phiên đầu xu hướng: chỉ xét đảo chiều, chưa dời EP
      sar = sar + af * (ep - sar);
      if (up && sar > lo) { sar = Math.max(h, ep); ep = lo; up = false; }
      else if (!up && sar < h) { sar = Math.min(lo, ep); ep = h; up = true; }
    } else {
      [sar, ep, af, up] = sarStep(sar, ep, af, up, h, lo);
    }
    const prev = rows.slice(Math.max(i - 2, 0), i);
    sar = up ? Math.min(sar, ...prev.map((r) => r[3])) : Math.max(sar, ...prev.map((r) => r[2]));
  }
  return [up ? 1 : -1, sar, ep, af];
}

// %K thô (n) tại phiên i; null nếu chưa đủ phiên hoặc cao nhất = thấp nhất
export function rawK(rows, i, n = STOCH_N) {
  if (i < n - 1) return null;
  const win = rows.slice(i - n + 1, i + 1);
  const hh = Math.max(...win.map((r) => r[2])), ll = Math.min(...win.map((r) => r[3]));
  return hh > ll ? (rows[i][4] - ll) / (hh - ll) * 100 : null;
}

// CCI của dãy giá điển hình (phần tử cuối là phiên đang xét); null nếu dao động trung bình = 0
export function cci(tps) {
  const m = fmean(tps);
  const md = fsum(tps.map((x) => Math.abs(x - m))) / tps.length;
  return md ? (tps[tps.length - 1] - m) / (0.015 * md) : null;
}

// Trung bình Wilder (rma của TradingView) tại từng phần tử; các phần tử trước khi đủ n → null
function rma(values, n) {
  const out = new Array(values.length).fill(null);
  if (values.length < n) return out;
  let a = fmean(values.slice(0, n));
  out[n - 1] = a;
  for (let i = n; i < values.length; i++) {
    a = (a * (n - 1) + values[i]) / n;
    out[i] = a;
  }
  return out;
}

// [+DM, −DM, TR] của phiên cur so với phiên prev — mỗi phiên dạng [… , cao, thấp, đóng, …]
export function dmTr(prev, cur) {
  const up = cur[2] - prev[2], down = prev[3] - cur[3];
  return [up > down && up > 0 ? up : 0, down > up && down > 0 ? down : 0,
    Math.max(cur[2] - cur[3], Math.abs(cur[2] - prev[4]), Math.abs(cur[3] - prev[4]))];
}

export const di = (dm, atr) => (atr ? 100 * dm / atr : 0);

// |+DI − −DI| / (+DI + −DI) — ADX là trung bình Wilder của số này × 100
export function dxFrac(pdi, mdi) {
  const s = pdi + mdi;
  return Math.abs(pdi - mdi) / (s || 1);
}

// ADX / DMI tại phiên cuối: [RMA TR, RMA +DM, RMA −DM, RMA của dxFrac]; null nếu thiếu phiên
export function dmiParts(rows, n = DMI_N) {
  const parts = rows.slice(1).map((r, i) => dmTr(rows[i], r));
  const atr = rma(parts.map((x) => x[2]), n);
  const pdm = rma(parts.map((x) => x[0]), n);
  const mdm = rma(parts.map((x) => x[1]), n);
  const dx = [];
  atr.forEach((a, i) => { if (a !== null) dx.push(dxFrac(di(pdm[i], a), di(mdm[i], a))); });
  const adx = rma(dx, n);
  if (!adx.length || adx[adx.length - 1] === null) return null;
  return [atr[atr.length - 1], pdm[pdm.length - 1], mdm[mdm.length - 1], adx[adx.length - 1]];
}

// (cao nhất + thấp nhất) / 2 của n phiên tính tới phiên i — Tenkan / Kijun / Span B; null nếu chưa đủ phiên
export function midRange(rows, i, n) {
  if (i < n - 1) return null;
  const win = rows.slice(i - n + 1, i + 1);
  return (Math.max(...win.map((r) => r[2])) + Math.min(...win.map((r) => r[3]))) / 2;
}

// [Span A, Span B] tính ở phiên i — tức mây của phiên i + 25; null nếu chưa đủ phiên
export function ichimokuLead(rows, i) {
  const t = midRange(rows, i, ICHI_T), k = midRange(rows, i, ICHI_K), b = midRange(rows, i, ICHI_B);
  return t === null || k === null || b === null ? null : [(t + k) / 2, b];
}

// Số phiên tăng (dương) hoặc giảm (âm) liên tục tính đến phiên cuối; đứng giá = 0.
export function streak(closes) {
  let s = 0;
  for (let i = closes.length - 1; i > 0; i--) {
    const d = closes[i] - closes[i - 1];
    const sign = d > 0 ? 1 : (d < 0 ? -1 : 0);
    if (sign === 0 || (s !== 0 && sign !== (s > 0 ? 1 : -1))) break;
    s += sign;
  }
  return s;
}

export function smaSeries(closes, n) {
  const out = new Array(closes.length).fill(null);
  let s = 0;
  for (let i = 0; i < closes.length; i++) {
    s += closes[i];
    if (i >= n) s -= closes[i - n];
    if (i >= n - 1) out[i] = s / n;
  }
  return out;
}

// Nhịp tăng rồi điều chỉnh gần nhất so với 1 đường hỗ trợ (xem pullback_leg của tech.py)
export function pullbackLeg(rows, line, lookback) {
  const n = rows.length;
  const start = Math.max(n - lookback, 0);
  if (n < 2) return null;
  for (let i = Math.min(start, n - 2); i < n; i++) if (line[i] === null || line[i] <= 0) return null;
  let peak = start;
  for (let i = start + 1; i < n; i++) if (rows[i][2] >= rows[peak][2]) peak = i;     // bằng nhau thì lấy phiên sau
  const after = [];
  for (let i = peak + 1; i < n; i++) after.push(i);
  return {
    ext: rows[peak][2] / line[peak] - 1,
    pk: after.length,
    vpb: after.length ? imean(after.map((i) => rows[i][5])) : null,
    mr: after.length ? Math.min(...after.map((i) => rows[i][4] / line[i])) : null,
    lr: Math.min(rows[n - 2][3] / line[n - 2], rows[n - 1][3] / line[n - 1]),
  };
}

// Chỉ số các đáy (nhỏ nhất trong k phiên mỗi bên) hoặc đỉnh (high=true)
export function pivots(values, high = false, k = TL_PIVOT) {
  const out = [];
  for (let i = k; i < values.length - k; i++) {
    let ext = values[i - k];
    for (let j = i - k + 1; j <= i + k; j++) ext = high ? Math.max(ext, values[j]) : Math.min(ext, values[j]);
    if (values[i] === ext) out.push(i);
  }
  return out;
}

// Trendline tự vẽ trên giá đóng cửa trong `window` phiên đã đóng gần nhất (luật TL_*).
export function trendLine(allRows, window, up = true) {
  const rows = allRows.slice(-window);
  if (rows.length < TL_MIN_BARS) return null;
  const closes = rows.map((r) => r[4]);
  const highs = rows.map((r) => r[2]);
  const sg = up ? 1 : -1;
  const last = rows.length - 1;
  const until = up ? last : last - TL_RECENT;
  const piv = pivots(closes, !up).filter((p) => p <= until);
  const edge = closes.map((c) => c / (1 - sg * TL_TOL));
  const after = new Map();
  const afterLim = (b) => {
    if (!after.has(b)) {
      let m = Infinity;
      for (let i = b + 1; i <= until; i++) {
        const v = sg * (edge[i] - closes[b]) / (i - b);
        if (v < m) m = v;
      }
      after.set(b, m);
    }
    return after.get(b);
  };
  const maxOf = (a, from, to) => {      // max(a[from:to])
    let m = -Infinity;
    for (let i = from; i < to; i++) if (a[i] > m) m = a[i];
    return m;
  };

  for (let ai = 0; ai < piv.length; ai++) {
    const a = piv[ai];
    const y0 = closes[a];
    let before = null;
    for (let bi = piv.length - 1; bi > ai; bi--) {
      const b = piv[bi];
      if (b - a < TL_MIN_GAP || sg * (closes[b] - y0) <= 0) continue;
      const s = (closes[b] - y0) / (b - a);
      if (Math.abs(s) > TL_MAX_SLOPE * y0 || sg * s > afterLim(b)) continue;
      if (before === null) {
        before = new Array(b + 1).fill(Infinity);
        for (let i = a + 1; i < b; i++) before[i + 1] = Math.min(before[i], sg * (edge[i] - y0) / (i - a));
      }
      if (sg * s > before[b]) continue;
      if (up && maxOf(highs, b + 1, highs.length) < maxOf(highs, a, b + 1)) continue;
      const line = rows.map((_, i) => y0 + s * (i - a));
      const touch = piv.filter((p) => a <= p && p <= until && Math.abs(closes[p] / line[p] - 1) <= TL_TOL);
      if (touch.length < TL_TOUCHES) continue;
      const e = touch[touch.length - 1];
      let extra;
      if (up) {
        extra = pullbackLeg(rows, line, last - b);
        if (extra === null || extra.ext < TL_EXT) continue;
      } else {
        let mn = Infinity;
        for (let i = a; i <= e; i++) mn = Math.min(mn, closes[i] / line[i]);
        if (mn > 1 - TL_EXT) continue;
        const cr = [], lr = [];
        for (let i = Math.max(e + 1, last - TL_RECENT + 1); i <= last; i++) {
          cr.push(closes[i] / line[i]);
          lr.push(rows[i][3] / line[i]);
        }
        extra = { cr, lr };
      }
      return { v: line[last], s, a: rows[a][0], b: rows[b][0], e: rows[e][0], t: touch.length, ...extra };
    }
  }
  return null;
}

// Phiên vượt trendline giảm gần nhất trong `back` phiên đã đóng (kẻ lại đường như đúng hôm đó)
export function lastBreak(rows, window, back = BREAK_DAYS) {
  const top = Math.min(back, rows.length - 1);
  for (let k = 1; k <= top; k++) {
    const past = rows.slice(0, -k), bar = rows[rows.length - k];
    const td = trendLine(past, window, false);
    if (!td || td.cr.some((r) => r >= 1 + BREAK_UP)) continue;
    const v20 = imean(past.slice(-20).map((r) => r[5]));
    const r = bar[4] / (td.v + td.s);
    if (r >= 1 + BREAK_UP && bar[5] >= v20) {
      return { k, d: bar[0], p: bar[4], r, vr: v20 ? bar[5] / v20 : null };
    }
  }
  return null;
}

// round(v, 6) của Python cho mọi số thực (lồng trong dict / list); số nguyên giữ nguyên
function round6(v) {
  if (typeof v === 'number') return Number.isInteger(v) ? v : pyRoundTo(v, 6);
  if (Array.isArray(v)) return v.map(round6);
  if (v && typeof v === 'object') {
    const o = {};
    for (const [k, x] of Object.entries(v)) o[k] = round6(x);
    return o;
  }
  return v;
}

// Số thống kê chỉ đếm theo số nến (MA, RSI, MACD, Bollinger, MFI, Stochastic, CCI, ADX, SAR, OBV, Ichimoku…) — dùng chung
// cho nến ngày (statsFromBars) và nến trong phiên (intradayStats). Chưa làm tròn. Xem indicator_stats của tech.py.
export function indicatorStats(rows) {
  const closes = rows.map((r) => r[4]);
  const vols = rows.map((r) => r[5]);
  const n = rows.length;
  const last = rows[n - 1];
  const out = { n, lc: closes[n - 1], lh: last[2], ll: last[3] };

  for (const k of PRICE_AVG_N) out[`p${k}`] = n >= k ? fmean(closes.slice(-k)) : null;
  for (const k of VOL_AVG_N) out[`v${k}`] = imean(vols.slice(-k));
  for (const k of [50, 100]) out[`v${k}`] = n >= k ? imean(vols.slice(-k)) : null;
  out.sd19 = std(closes.slice(-19));
  out.sd20 = std(closes.slice(-20));

  for (const k of EMA_N) out[`e${k}`] = n >= k ? emaLast(closes, k) : null;
  if (n >= 35) {
    const e12 = [], e26 = [];
    const a12 = 2 / 13, a26 = 2 / 27;
    let x12 = closes[0], x26 = closes[0];
    for (const c of closes.slice(1)) {
      x12 = a12 * c + (1 - a12) * x12;
      x26 = a26 * c + (1 - a26) * x26;
      e12.push(x12);
      e26.push(x26);
    }
    out.e12 = e12[e12.length - 1];
    out.e26 = e26[e26.length - 1];
    out.sig = emaLast(e12.map((a, i) => a - e26[i]), 9);
  } else {
    out.e12 = out.e26 = out.sig = null;
  }
  [out.ag, out.al] = wilderRsiParts(closes);
  out.rs = rsiTail(closes).map((x) => pyRoundTo(x, 4));
  [out.pmf, out.nmf, out.mfi] = moneyFlow(rows);

  // Parabolic SAR; Stochastic (%K thô / %K chậm 2 phiên cuối, %D phiên cuối, cao / thấp 13 phiên cuối)
  [out.sart, out.sar, out.sep, out.saf] = parabolicSar(rows);
  const kr = [];
  for (let i = n - 5; i < n; i++) kr.push(rawK(rows, i));
  const ks = [0, 1, 2].map((j) => (kr.slice(j, j + 3).some((x) => x === null) ? null : (kr[j] + kr[j + 1] + kr[j + 2]) / 3));
  out.skr = kr.slice(-2);
  out.sks = ks.slice(-2);
  out.skd = ks.some((x) => x === null) ? null : (ks[0] + ks[1] + ks[2]) / 3;
  const last13 = rows.slice(-(STOCH_N - 1));
  out.hh13 = Math.max(...last13.map((r) => r[2]));
  out.ll13 = Math.min(...last13.map((r) => r[3]));
  // CCI: giá điển hình 19 phiên cuối + CCI phiên cuối
  const tps = rows.map((r) => (r[2] + r[3] + r[4]) / 3);
  out.tp19 = tps.slice(-(CCI_N - 1));
  out.cci = cci(tps.slice(-CCI_N));
  // ADX / DMI
  [out.atr, out.pdm, out.mdm, out.dxa] = dmiParts(rows) || [null, null, null, null];
  // OBV (cộng dồn từ phiên thứ 2) + tổng 19 / TB 20 phiên cuối
  const obv = [];
  let s = 0;
  for (let i = 1; i < n; i++) {
    const c = rows[i][4], p = rows[i - 1][4];
    s += c > p ? rows[i][5] : (c < p ? -rows[i][5] : 0);
    obv.push(s);
  }
  if (obv.length >= OBV_N) {
    out.obv = obv[obv.length - 1];
    out.ob19 = isum(obv.slice(-(OBV_N - 1)));
    out.obm = isum(obv.slice(-OBV_N)) / OBV_N;
  } else {
    out.obv = out.ob19 = out.obm = null;
  }
  // Ichimoku: Tenkan / Kijun phiên cuối, cao / thấp 8 và 25 phiên cuối, mây hôm nay (ca) và hôm qua (cb)
  out.tk = midRange(rows, n - 1, ICHI_T);
  out.kj = midRange(rows, n - 1, ICHI_K);
  for (const k of [ICHI_T - 1, ICHI_K - 1]) {
    const w = rows.slice(-k);
    out[`ih${k}`] = Math.max(...w.map((r) => r[2]));
    out[`il${k}`] = Math.min(...w.map((r) => r[3]));
  }
  out.ca = ichimokuLead(rows, n - ICHI_SHIFT);
  out.cb = ichimokuLead(rows, n - 1 - ICHI_SHIFT);
  return out;
}

// Thứ Hai của tuần chứa ngày 'YYYY-MM-DD'
export function weekStart(day) {
  const ms = Date.parse(day + 'T00:00:00Z');
  return new Date(ms - ((new Date(ms).getUTCDay() + 6) % 7) * DAY_MS).toISOString().slice(0, 10);
}

// Nến tuần gộp từ nến ngày → [indicatorStats các tuần đã đóng hoặc null, [cao, thấp, KL] các phiên đã đóng của tuần này
// hoặc null] (xem weekly_parts của tech.py)
export function weeklyParts(rows, today) {
  const cur = weekStart(today);
  const weeks = [];
  let part = null;
  for (const [d, o, h, lo, c, v] of rows) {
    if (d >= cur) {
      part = part === null ? [h, lo, v] : [Math.max(part[0], h), Math.min(part[1], lo), part[2] + v];
      continue;
    }
    const ws = weekStart(d), w = weeks[weeks.length - 1];
    if (w && w[0] === ws) weeks[weeks.length - 1] = [ws, w[1], Math.max(w[2], h), Math.min(w[3], lo), c, w[5] + v];
    else weeks.push([ws, o, h, lo, c, v]);
  }
  return [weeks.length >= MIN_BARS ? indicatorStats(weeks) : null, part];
}

// Toàn bộ số thống kê của 1 mã (null nếu quá ít nến). history=true: thêm quét lùi phiên vượt trendline giảm.
export function statsFromBars(bars, today, dateOf, history = false) {
  const rows = closedBars(bars, today, dateOf);
  if (rows.length < MIN_BARS) return null;
  const out = indicatorStats(rows);
  const dates = rows.map((r) => r[0]);
  const closes = rows.map((r) => r[4]);
  const vols = rows.map((r) => r[5]);
  const n = rows.length;
  out.ld = dates[n - 1];
  [out.w, out.wk] = weeklyParts(rows, today);
  out.gv20 = fmean(rows.slice(-20).map((r) => r[4] * r[5])) / 1e6;      // GTTB 20 phiên, tỷ đồng (giá nghìn đồng)
  const since3m = minusPeriod(today, 'm', 3);
  const v3m = vols.filter((_, i) => dates[i] >= since3m);
  out.v3m = v3m.length ? imean(v3m) : null;

  for (const [key, [kind, k]] of Object.entries(PERIODS)) {
    const since = minusPeriod(today, kind, k);
    const win = rows.filter((r) => r[0] >= since);
    out[`hi${key}`] = win.length ? Math.max(...win.map((r) => r[2])) : null;
    out[`lo${key}`] = win.length ? Math.min(...win.map((r) => r[3])) : null;
    const ref = closes.filter((_, i) => dates[i] <= since);
    out[`px${key}`] = ref.length ? ref[ref.length - 1] : null;
  }
  out.streak = streak(closes);

  for (const [k, [look]] of Object.entries(PB_SMA).map(([k, v]) => [Number(k), v])) {
    const line = smaSeries(closes, k);
    out[`ps${k}`] = n >= k + PB_SLOPE ? line[n - 1 - PB_SLOPE] : null;
    out[`pb${k}`] = n >= k + look ? pullbackLeg(rows, line, look) : null;
  }
  for (const [key, w] of Object.entries(TL_WINDOWS)) {
    out[`tl${key}`] = trendLine(rows, w);
    out[`td${key}`] = trendLine(rows, w, false);
    if (history) out[`tb${key}`] = lastBreak(rows, w);
  }
  return round6(out);
}

// ── Nến trong phiên ─────────────────────────────────────────────────────

// [ngày 'YYYY-MM-DD' giờ VN, mốc (phút trong ngày), đang trong buổi khớp lệnh?]. Trong buổi: giờ mở nến `minutes` phút
// đang chạy (nến tính từ 9:00); ngoài giờ: giờ hết buổi vừa xong (11:30 / 15:00; trước giờ mở cửa, cuối tuần: 0).
function intradaySlot(nowMs, minutes) {
  const d = new Date(nowMs + VN_MS);
  const date = d.toISOString().slice(0, 10);
  const wd = d.getUTCDay();
  const weekday = wd !== 0 && wd !== 6;
  const m = d.getUTCHours() * 60 + d.getUTCMinutes();
  if (weekday) {
    for (const [a, b] of INTRA_SESSIONS) if (a <= m && m < b) return [date, m - (m - INTRA_SESSIONS[0][0]) % minutes, true];
  }
  const ends = weekday ? INTRA_SESSIONS.map(([, b]) => b).filter((b) => b <= m) : [];
  return [date, ends.length ? ends[ends.length - 1] : 0, false];
}

// Giờ mở nến `minutes` phút đang chạy lúc nowMs (giây Unix): nến từ giờ này trở đi chưa chốt.
// null = ngoài giờ khớp lệnh (nghỉ trưa, sau giờ, trước giờ mở cửa, cuối tuần) — mọi nến đã chốt.
export function intradayCutoff(nowMs, minutes = INTRA_MIN) {
  const [date, m, open] = intradaySlot(nowMs, minutes);
  return open ? (Date.parse(date + 'T00:00:00Z') - VN_MS) / 1000 + m * 60 : null;
}

// Mốc của bộ nến `minutes` phút dùng được lúc nowMs, vd '2026-10-29 09:00'. Sang mốc mới = vừa có nến chốt → tải lại.
export function intradayKey(nowMs, minutes = INTRA_MIN) {
  const [date, m] = intradaySlot(nowMs, minutes);
  return `${date} ${String(Math.floor(m / 60)).padStart(2, '0')}:${String(m % 60).padStart(2, '0')}`;
}

// Gộp nến [giờ mở giây Unix, mở, cao, thấp, đóng, KL] liền nhau thành nến `minutes` phút tính từ 9:00 giờ VN
export function mergeBars(rows, minutes) {
  const out = [];
  for (const [t, o, h, lo, c, v] of rows) {
    const m = Math.floor(((t + VN_MS / 1000) % 86400) / 60);
    const start = t - ((((m - INTRA_SESSIONS[0][0]) % minutes) + minutes) % minutes) * 60;
    const b = out[out.length - 1];
    if (b && b[0] === start) out[out.length - 1] = [start, b[1], Math.max(b[2], h), Math.min(b[3], lo), c, b[5] + v];
    else out.push([start, o, h, lo, c, v]);
  }
  return out;
}

// Số thống kê khung trong phiên của 1 mã, xét tại nến đã chốt gần nhất — nến có giờ mở < cutoff (giây Unix; null = mọi
// nến); minutes: gộp nến nguồn thành nến dài hơn. indicatorStats tính tới nến TRƯỚC đó; nến đã chốt gần nhất nằm ở
// bar = [giờ mở, cao, thấp, đóng, KL] (đóng vai "phiên hôm nay"). null nếu quá ít nến. Xem intraday_stats của tech.py.
export function intradayStats(bars, cutoff = null, minutes = null) {
  let rows = closedBars(bars, cutoff === null ? Infinity : cutoff, (t) => t);     // 'ngày' ở đây là giây Unix
  if (minutes) rows = mergeBars(rows, minutes);
  if (rows.length < INTRA_MIN_BARS) return null;
  const out = indicatorStats(rows.slice(0, -1));
  const [t, , h, lo, c, v] = rows[rows.length - 1];
  out.bar = [t, h, lo, c, v];
  return round6(out);
}

// ── Khối lượng dự kiến cả phiên (cách FireAnt đổi giờ hiện tại → số phút đã giao dịch) ──
export function sessionMinutes(exchange) {
  return exchange === 'HNX' || exchange === 'UPCOM' ? 270 : 255;
}

// nowMs: mốc thời gian (ms). Số phút giao dịch đã trôi qua tính theo giờ Việt Nam.
export function elapsedMinutes(nowMs, exchange) {
  const vn = nowMs + 7 * 3600000;
  const start = Math.floor(vn / DAY_MS) * DAY_MS + 9 * 3600000;
  const r = Math.ceil((vn - start) / 1000 / 60);
  if (r > 360) return sessionMinutes(exchange);
  if (r > 345) return exchange === 'HNX' || exchange === 'UPCOM' ? r - 90 : 255;
  if (r > 330) return exchange === 'UPCOM' ? r - 90 : 240;
  if (r > 240) return r - 90;
  if (r > 150) return 150;
  return Math.max(r, 0);
}

export function estimatedVolume(totalVolume, exchange, nowMs) {
  const m = elapsedMinutes(nowMs, exchange);
  if (!totalVolume || m <= 0) return null;
  return totalVolume * sessionMinutes(exchange) / m;
}
