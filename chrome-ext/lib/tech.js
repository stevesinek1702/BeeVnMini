// Chỉ báo kỹ thuật tính từ nến ngày — chép từ tech.py của bản Python, giữ đúng thứ tự phép tính
// để số ra khớp từng chữ số (xem pyfloat.js). Mọi con số tính trên các phiên ĐÃ ĐÓNG (bỏ nến hôm nay).
// Giá tính bằng nghìn đồng; khối lượng bằng cổ phiếu. Không dính giao diện, không dính mạng.
import { fsum, fmean, imean, pyRoundTo } from './pyfloat.js';

export const PRICE_AVG_N = [4, 5, 9, 10, 14, 15, 19, 20, 44, 45, 49, 50, 99, 100, 199, 200];
export const VOL_AVG_N = [4, 5, 9, 10, 14, 19, 20, 44];
export const EMA_N = [5, 10, 15, 20, 45, 50, 100, 200];
export const VERSION = 6;        // cùng số với tech.VERSION của Python: đổi khi thêm số thống kê mới → bộ đệm cũ bị bỏ
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

const DAY_MS = 86400000;

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

// Toàn bộ số thống kê của 1 mã (null nếu quá ít nến). history=true: thêm quét lùi phiên vượt trendline giảm.
export function statsFromBars(bars, today, dateOf, history = false) {
  const rows = closedBars(bars, today, dateOf);
  if (rows.length < MIN_BARS) return null;
  const dates = rows.map((r) => r[0]);
  const closes = rows.map((r) => r[4]);
  const vols = rows.map((r) => r[5]);
  const n = rows.length;
  const last = rows[n - 1];
  const out = { n, ld: dates[n - 1], lc: closes[n - 1], lh: last[2], ll: last[3] };

  for (const k of PRICE_AVG_N) out[`p${k}`] = n >= k ? fmean(closes.slice(-k)) : null;
  for (const k of VOL_AVG_N) out[`v${k}`] = imean(vols.slice(-k));
  const since3m = minusPeriod(today, 'm', 3);
  const v3m = vols.filter((_, i) => dates[i] >= since3m);
  out.v3m = v3m.length ? imean(v3m) : null;
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
  [out.pmf, out.nmf, out.mfi] = moneyFlow(rows);

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
