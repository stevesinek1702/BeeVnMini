// Chép tests/test_conditions.py: điều kiện lọc kiểu FireAnt (tech.js + conditions.js + phần nối ở core.js).
// Chạy: node --test tests/   (đứng ở thư mục chrome-ext)
import { test } from 'node:test';
import assert from 'node:assert/strict';
import * as tech from '../lib/tech.js';
import * as cond from '../lib/conditions.js';
import * as core from '../lib/core.js';

const near = (a, b, places = 7) => assert.ok(Math.abs(a - b) < 0.5 * 10 ** -places, `${a} ≉ ${b}`);
const keep = (t) => t;
const addDays = (iso, n) => new Date(Date.parse(iso + 'T00:00:00Z') + n * 86400000).toISOString().slice(0, 10);

// n nến ngày liên tiếp; 't' là chuỗi ngày (dateOf giữ nguyên)
function makeBars(n, { close = (i) => i + 1, vol = 1000, start = '2026-08-01' } = {}) {
  const days = Array.from({ length: n }, (_, i) => addDays(start, i));
  const c = days.map((_, i) => close(i));
  return [{ s: 'ok', t: days, o: c, h: c.map((x) => x + 0.5), l: c.map((x) => x - 0.5), c, v: Array(n).fill(vol) }, days];
}

function statsOf(n = 60, kw = {}) {
  const [bars, days] = makeBars(n, kw);
  const today = addDays(days[days.length - 1], 1);
  return [tech.statsFromBars(bars, today, keep), today];
}

const lv = (last, kw = {}) => ({ last, high: kw.high ?? null, low: kw.low ?? null, volume: kw.volume ?? 0, est: kw.est ?? null });
const sig = (id, params = {}) => cond.normalizeSignal({ id, params });
// giờ VN → mốc ms
const vnAt = (h, m, s = 0) => Date.UTC(2026, 9, 14, h - 7, m, s);

test('lùi ngày, lùi tháng', () => {
  assert.equal(tech.minusPeriod('2026-10-15', 'd', 7), '2026-10-08');
  assert.equal(tech.minusPeriod('2026-03-31', 'm', 1), '2026-02-28');
  assert.equal(tech.minusPeriod('2026-01-15', 'm', 3), '2025-10-15');
  assert.equal(tech.minusPeriod('2026-10-15', 'm', 12), '2025-10-15');
});

test('chuỗi phiên tăng giảm', () => {
  assert.equal(tech.streak([1, 2, 3, 4]), 3);
  assert.equal(tech.streak([4, 3, 2, 3]), 1);
  assert.equal(tech.streak([5, 4, 3]), -2);
  assert.equal(tech.streak([1, 2, 3, 3]), 0);
});

test('EMA và RSI Wilder', () => {
  assert.equal(tech.emaLast([1, 2, 3], 3), 2.25);
  assert.equal(tech.emaLast(Array(30).fill(7), 12), 7);
  assert.deepEqual(tech.wilderRsiParts(Array.from({ length: 16 }, (_, i) => i + 1)), [1, 0]);
  assert.deepEqual(tech.wilderRsiParts([1, 2, 3]), [null, null]);
});

test('dòng tiền MFI', () => {
  const rows = (b) => tech.closedBars(b, '2099-01-01', keep);
  let [p, n, mfi] = tech.moneyFlow(rows(makeBars(20, { close: (i) => 10 + i })[0]));
  assert.deepEqual([n, mfi], [0, 100]);
  assert.ok(p > 0);
  [p, n, mfi] = tech.moneyFlow(rows(makeBars(20, { close: (i) => 50 - i })[0]));
  assert.deepEqual([p, mfi], [0, 0]);
});

test('bỏ nến hôm nay và nến hỏng', () => {
  const [bars, days] = makeBars(40);
  const today = days[days.length - 1];
  const st = tech.statsFromBars(bars, today, keep);
  assert.deepEqual([st.n, st.lc, st.ld], [39, 39, days[days.length - 2]]);
  bars.c[5] = null;
  assert.equal(tech.statsFromBars(bars, today, keep).n, 38);
  assert.equal(tech.statsFromBars(makeBars(10)[0], '2099-01-01', keep), null);
  assert.equal(tech.statsFromBars({ s: 'no_data' }, '2099-01-01', keep), null);
  assert.equal(tech.statsFromBars(null, '2099-01-01', keep), null);
});

test('số thống kê tính tay', () => {
  const [st] = statsOf(60);
  assert.deepEqual([st.lc, st.lh, st.ll], [60, 60.5, 59.5]);
  assert.deepEqual([st.p5, st.p20, st.p4], [58, 50.5, 58.5]);
  assert.deepEqual([st.v20, st.v44], [1000, 1000]);
  assert.equal(st.streak, 59);
  assert.equal(st.mfi, 100);
  near(st.sd20, 5.766281, 5);
  assert.deepEqual([st.hi1w, st.lo1w, st.px1w], [60.5, 53.5, 54]);
});

test('ngày của nến dchart là giờ VN', () => {
  const t = Date.UTC(2026, 9, 14) / 1000;
  const bars = { s: 'ok', t: [t], o: [1], h: [1], l: [1], c: [1], v: [1] };
  assert.equal(tech.closedBars(bars, '2026-10-15', core.vnDate).length, 1);
  assert.equal(tech.closedBars(bars, '2026-10-14', core.vnDate).length, 0);
});

test('phút giao dịch và KL dự kiến', () => {
  assert.equal(tech.elapsedMinutes(vnAt(8, 59), 'HSX'), 0);
  assert.equal(tech.elapsedMinutes(vnAt(10, 0), 'HSX'), 60);
  assert.equal(tech.elapsedMinutes(vnAt(12, 0), 'HSX'), 150);
  assert.equal(tech.elapsedMinutes(vnAt(14, 0), 'HSX'), 210);
  assert.equal(tech.elapsedMinutes(vnAt(16, 0), 'HSX'), 255);
  assert.equal(tech.elapsedMinutes(vnAt(16, 0), 'HNX'), 270);
  assert.equal(tech.estimatedVolume(1000, 'HSX', vnAt(10, 0)), 1000 * 255 / 60);
  assert.equal(tech.estimatedVolume(1000, 'HSX', vnAt(8, 30)), null);
  assert.equal(tech.estimatedVolume(0, 'HSX', vnAt(10, 0)), null);
});

test('MA dài: giá cắt lên SMA / EMA 50, 100, 200', () => {
  const st = statsOf(250, { close: () => 10 })[0];
  for (const n of [50, 100, 200]) {
    near(st[`p${n}`], 10);
    near(st[`e${n}`], 10);
    for (const sid of ['PriceCrossAboveSMA', 'PriceCrossAboveEMA']) {
      const s = { id: sid, params: { period: n } };
      assert.ok(cond.evalSignal(s, st, { last: 11 }), `${sid} ${n}`);
      assert.ok(!cond.evalSignal(s, st, { last: 9 }), `${sid} ${n}`);
    }
  }
  assert.deepEqual(cond.normalizeSignal({ id: 'ShortSMACrossAboveLongSMA', params: { short: 50, long: 200 } }).params,
    { short: 50, long: 200 });
});

test('chưa đủ phiên thì không tính', () => {
  const st = statsOf(120, { close: () => 10 })[0];
  assert.notEqual(st.p100, null);
  assert.equal(st.p200, null);
  assert.ok(!cond.evalSignal({ id: 'PriceCrossAboveSMA', params: { period: 200 } }, st, { last: 11 }));
});

// ── Pullback & trendline ────────────────────────────────────────────────
function ohlcStats(closes, lows = null, highs = null, vols = null, history = false) {
  const n = closes.length;
  const days = Array.from({ length: n }, (_, i) => addDays('2026-01-01', i));
  const bars = { s: 'ok', t: days, o: closes, h: highs || closes.map((c) => c + 0.1), l: lows || closes.map((c) => c - 0.1),
    c: closes, v: vols || Array(n).fill(1000) };
  const today = addDays(days[n - 1], 1);
  return [tech.statsFromBars(bars, today, keep, history), days];
}
const RISE = Array.from({ length: 60 }, (_, i) => 10 + 0.2 * i);
const DIP = [21.2, 20.8, 20.5, 20.4, 20.5];
const ev = (id, st, live, params = {}) => cond.evalSignal(sig(id, params), st, live);
const vols = (a, n1, b, n2) => [...Array(n1).fill(a), ...Array(n2).fill(b)];

test('pullback SMA đang kiểm định', () => {
  const [st] = ohlcStats([...RISE, ...DIP], null, null, vols(1000, 60, 500, 5));
  assert.equal(st.pb20.pk, 5);
  assert.equal(st.pb20.vpb, 500);
  const ma = cond.smaLive(st, 20.6, 20);
  assert.ok(ev('PullbackToSMA', st, lv(20.6, { low: 20.45, est: 500 }), { period: 20 }));
  assert.ok(ev('PullbackToSMA', st, lv(20.6, { low: 20.45, est: 500 }), { period: 20, tol: 1, dry: 'không' }));
  assert.ok(!ev('PullbackToSMA', st, lv(ma * 0.97, { low: ma * 0.96, est: 500 }), { period: 20 }));
  assert.ok(!ev('PullbackToSMA', st, lv(21.5, { low: 21.3, est: 500 }), { period: 20 }));
  assert.ok(!ev('PullbackToSMA', st, lv(20.6, { low: 20.45, est: 5000 }), { period: 20 }));
  assert.ok(ev('PullbackToSMA', st, lv(20.6, { low: 20.45, est: 5000 }), { period: 20, dry: 'không' }));
  assert.ok(ev('PullbackToSMA', st, lv(20.6, { low: 20.45, est: null }), { period: 20 }));
  near(cond.techMetrics(st, 20.6, 0.1).distSMA20, (20.6 / ma - 1) * 100);
});

test('pullback SMA: không phải xu hướng tăng', () => {
  const [down] = ohlcStats([...Array.from({ length: 60 }, (_, i) => 30 - 0.2 * i), 17.9, 18.0, 18.1, 18.0, 18.1]);
  assert.ok(!ev('PullbackToSMA', down, lv(18.0, { low: 17.8, est: 1000 }), { period: 20, dry: 'không' }));
  const [flat] = ohlcStats(Array.from({ length: 65 }, (_, i) => 10 + 0.01 * i));
  const last = cond.smaLive(flat, 10.64, 20);
  assert.ok(!ev('PullbackToSMA', flat, lv(last, { low: last, est: 1000 }), { period: 20, dry: 'không' }));
});

test('pullback SMA: đã đóng cửa thủng sau đỉnh', () => {
  const [st] = ohlcStats([...RISE, 21.2, 19.0, 20.5, 20.4, 20.5]);
  assert.ok(st.pb20.mr < 0.95);
  assert.ok(!ev('PullbackToSMA', st, lv(20.6, { low: 20.45, est: 500 }), { period: 20, tol: 5, dry: 'không' }));
});

test('bật lên từ SMA', () => {
  const [st] = ohlcStats([...RISE, ...DIP], null, null, vols(1000, 60, 500, 5));
  assert.ok(st.pb20.lr < 1);
  const live = lv(20.9, { low: 20.7, est: 500 });
  assert.ok(ev('PullbackBounceSMA', st, live, { period: 20 }));
  assert.ok(!ev('PullbackToSMA', st, live, { period: 20, tol: 0.5 }));
  assert.ok(!ev('PullbackBounceSMA', st, lv(20.45, { low: 20.4, est: 500 }), { period: 20 }));
  const [far] = ohlcStats([...RISE, 21.2, 20.6, 20.45, 21.4, 21.6], null, null, vols(1000, 60, 500, 5));
  assert.ok(far.pb20.lr > 1.02);
  assert.ok(!ev('PullbackBounceSMA', far, lv(21.8, { low: 21.6, est: 500 }), { period: 20 }));
});

// Khoảng cách giá đóng cửa tới đường: 0 ở ngày 10, 25, 40; cao `mid` ở giữa; sau đó xa dần tới 3 ở ngày 70 rồi về sát đường
function dist(i, mid = 1.5) {
  if (i < 10) return 0.1 * (10 - i);
  if (i <= 40) {
    const h = Array.isArray(mid) ? mid[Math.min(Math.floor((i - 10) / 15), 1)] : mid;
    return h * (1 - Math.abs((i - 10) % 15 - 7.5) / 7.5);
  }
  if (i <= 70) return 0.1 * (i - 40);
  return 3 - 0.1 * (i - 70);
}
function zigzag(n = 100, mid = 1.5) {
  const closes = Array.from({ length: n }, (_, i) => 10 + 0.05 * i + dist(i, mid));
  return [closes, closes.map((x) => x - 0.05), closes.map((x) => x + 0.05)];
}
function zigzagDown(n = 100, mid = 2) {
  const closes = Array.from({ length: n }, (_, i) => 30 - 0.05 * i - dist(i, mid));
  return [closes, closes.map((x) => x - 0.05), closes.map((x) => x + 0.05)];
}

test('trendline tự vẽ', () => {
  const [st, days] = ohlcStats(...zigzag());
  const tl = st.tl6m;
  assert.deepEqual([tl.a, tl.b, tl.e], [days[10], days[40], days[40]]);
  near(tl.v, 14.95);
  near(tl.s, 0.05);
  assert.equal(tl.t, 3);
  assert.equal(tl.pk, 29);
  assert.equal(st.tl3m, null);
  assert.ok(ev('PullbackToTrendline', st, lv(15.1, { low: 15.02 }), { period: '6m', dry: 'không' }));
  assert.ok(!ev('PullbackToTrendline', st, lv(15.1, { low: 15.02 }), { period: '6m' }));
  assert.ok(!ev('PullbackToTrendline', st, lv(14.5, { low: 14.4 }), { period: '6m', dry: 'không' }));
  assert.ok(ev('PullbackBounceTrendline', st, lv(15.2, { low: 15.1 }), { period: '6m', dry: 'không' }));
  assert.ok(!ev('PullbackBounceTrendline', st, lv(15.0, { low: 14.98 }), { period: '6m', dry: 'không' }));
});

test('trendline bị thủng hoặc thiếu phiên', () => {
  let [closes, lows, highs] = zigzag();
  const y = 10 + 0.05 * 97;
  closes[97] = y * 0.97; lows[97] = y * 0.96;
  assert.equal(ohlcStats(closes, lows, highs)[0].tl6m, null);
  assert.equal(ohlcStats(...zigzag(35))[0].tl6m, null);
  [closes, lows, highs] = zigzag();
  for (let i = 20; i < 31; i++) closes[i] += 1;
  assert.equal(ohlcStats(closes, lows, highs)[0].tl6m, null);
});

test('trendline lệch 2% vẫn tính', () => {
  const [closes, lows, highs] = zigzag();
  closes[25] = (10 + 0.05 * 25) * 0.985;
  const [st, days] = ohlcStats(closes, lows, highs);
  assert.deepEqual([st.tl6m.a, st.tl6m.b, st.tl6m.t], [days[10], days[40], 3]);
});

test('trendline tăng cần đỉnh cao dần', () => {
  assert.equal(ohlcStats(...zigzag(100, [7, 6]))[0].tl6m, null);
});

test('vượt lên trendline giảm', () => {
  let [st, days] = ohlcStats(...zigzagDown());
  const td = st.td6m;
  assert.deepEqual([td.a, td.b, td.t], [days[10], days[40], 3]);
  near(td.v, 25.05);
  near(td.s, -0.05);
  assert.equal(td.cr.length, tech.TL_RECENT);
  assert.equal(st.tl6m, null);
  const brk = (last, est, p = {}) => ev('BreakDownTrendline', st, lv(last, { est }), { period: '6m', ...p });
  assert.ok(brk(25.3, 2000));
  assert.ok(!brk(25.1, 2000));
  assert.ok(!brk(25.3, 500));
  assert.ok(brk(25.3, 500, { vol: 'không' }));
  assert.ok(brk(25.1, 2000, { brk: 0 }));
  assert.ok(!ev('PullbackBrokenDownTrendline', st, lv(25.1, { low: 25.0 }), { period: '6m' }));
  [st] = ohlcStats(...zigzagDown(100, 0.8));
  assert.equal(st.td6m, null);
});

// Trendline giảm như trên; ngày 95 đóng cửa vượt đường 3%, lùi về, ngày 98 giá thấp chạm lại đường
function retest(fail = false, history = false) {
  const [closes, lows, highs] = zigzagDown();
  const y = (i) => 30 - 0.05 * i;
  const rs = [0.99, 0.995, 1.03, 1.04, fail ? 0.97 : 1.025, 1.01, 1.012];
  for (let k = 0; k < 7; k++) {
    const i = 93 + k, r = rs[k];
    closes[i] = y(i) * r; lows[i] = y(i) * r - 0.05; highs[i] = y(i) * r + 0.05;
  }
  lows[98] = y(98) * 1.003;
  return ohlcStats(closes, lows, highs, null, history);
}

test('pullback sau khi vượt trendline giảm', () => {
  let [st, days] = retest();
  assert.deepEqual([st.td6m.a, st.td6m.b], [days[10], days[40]]);
  const e = (id, last, low) => ev(id, st, lv(last, { low }), { period: '6m' });
  assert.ok(e('BounceBrokenDownTrendline', 25.6, 25.3));
  assert.ok(!e('BounceBrokenDownTrendline', 25.2, 25.1));
  assert.ok(e('PullbackBrokenDownTrendline', 25.2, 25.1));
  assert.ok(!e('PullbackBrokenDownTrendline', 26.0, 25.8));
  assert.ok(!e('PullbackBrokenDownTrendline', 24.0, 23.9));
  assert.ok(!ev('BreakDownTrendline', st, lv(26, { est: 5000 }), { period: '6m' }));
  [st] = retest(true);
  assert.ok(!ev('BounceBrokenDownTrendline', st, lv(25.6, { low: 25.3 }), { period: '6m' }));
  assert.ok(!ev('PullbackBrokenDownTrendline', st, lv(25.2, { low: 25.1 }), { period: '6m' }));
});

test('quét lùi phiên vượt trendline giảm', () => {
  let [st, days] = retest(false, true);
  assert.deepEqual([st.tb6m.k, st.tb6m.d], [5, days[95]]);
  let m = cond.techMetrics(st, 25.6, 0.2, 1000);
  const dm = days[95].slice(8) + '/' + days[95].slice(5, 7);
  assert.deepEqual([m.brkTL6m, m.brkTL6mDay], [5, dm]);
  assert.deepEqual(core.formatCell(m, 'brkTL6m'), [dm, '']);
  assert.equal(m.brkTL3m, null);
  near(m.brkTL6mPx, 25.25 * 1.03);
  near(m.brkTL6mPct, (25.6 / (25.25 * 1.03) - 1) * 100);
  assert.deepEqual(core.formatCell(m, 'brkTL6mPct'), ['-1.57%', 'down']);
  assert.equal(m.brkTL3mPx, null);
  assert.deepEqual(core.extraColumns({ brkTL6mPct: { operator: 'le', value: 5 } }).map((c) => c[0]),
    ['brkTL6m', 'brkTL6mPx', 'brkTL6mPct']);
  assert.ok(core.needsBreakHistory({ filters: { brkTL6mPx: { operator: 'ge', value: 1 } } }));
  // Phiên vượt KL thấp hơn KLTB 20 thì không tính
  const [closes, lows, highs] = zigzagDown();
  closes[95] = (30 - 0.05 * 95) * 1.03;
  [st] = ohlcStats(closes, lows, highs, [...Array(95).fill(1000), 500, ...Array(4).fill(1000)], true);
  assert.equal(st.tb6m, null);
  // Chưa vượt phiên nào: hôm nay vượt (KL dự kiến đủ) → 0, hiện "hôm nay"
  [st] = ohlcStats(...zigzagDown(), null, true);
  assert.equal(st.tb6m, null);
  m = cond.techMetrics(st, 25.3, 0.3, 2000);
  assert.equal(m.brkTL6m, 0);
  assert.deepEqual(core.formatCell(m, 'brkTL6m'), ['hôm nay', 'up']);
  assert.deepEqual([m.brkTL6mPx, m.brkTL6mPct], [25.3, 0]);
  assert.equal(cond.techMetrics(st, 25.3, 0.3, 500).brkTL6m, null);
  assert.ok(!('tb6m' in ohlcStats(...zigzagDown())[0]));
});

test('tham số và mô tả pullback', () => {
  const s = cond.normalizeSignal({ id: 'PullbackToSMA', params: { period: 50, tol: 1.5, dry: 'không' } });
  assert.deepEqual(s.params, { period: 50, tol: 1.5, dry: 'không' });
  assert.deepEqual(sig('PullbackToSMA', { period: 7, dry: '?' }).params, { period: 20, tol: 2, dry: 'có' });
  assert.equal(cond.describeSignal(s), 'Pullback về SMA(50), vùng ±1.5%, KL cạn: không');
  assert.equal(cond.describeSignal(sig('PullbackBounceTrendline', { period: '3m' })), 'Bật lên từ trendline tăng 3 tháng, vùng ±2%, KL cạn: có');
  assert.ok(cond.catalog().pullback.some((x) => JSON.stringify(x) === JSON.stringify(['Pullback về SMA(…), vùng ±…%, KL cạn: …', 'signal', 'PullbackToSMA'])));
});

// ── Tín hiệu ────────────────────────────────────────────────────────────
test('giá cắt SMA', () => {
  const st = { lc: 10, p5: 10.2, p4: 10 };
  const up = sig('PriceCrossAboveSMA', { period: 5 });
  assert.ok(cond.evalSignal(up, st, lv(11)));
  assert.ok(!cond.evalSignal(up, st, lv(10)));
  const down = sig('PriceCrossBelowSMA', { period: 5 });
  assert.ok(!cond.evalSignal(down, st, lv(11)));
  assert.ok(cond.evalSignal(down, { lc: 10.5, p5: 10.2, p4: 10.2 }, lv(9)));
});

test('giá cắt EMA có khoảng đệm 50 đồng', () => {
  const st = { lc: 10, e5: 10 };
  const s = sig('PriceCrossAboveEMA', { period: 5 });
  assert.ok(!cond.evalSignal(s, st, lv(10.04)));
  assert.ok(cond.evalSignal(s, st, lv(10.2)));
});

test('SMA ngắn cắt SMA dài', () => {
  const st = { p5: 9, p4: 9, p15: 10, p14: 10 };
  const s = sig('ShortSMACrossAboveLongSMA', { short: 5, long: 15 });
  assert.ok(cond.evalSignal(s, st, lv(20)));
  assert.ok(!cond.evalSignal(s, st, lv(9)));
  assert.ok(!cond.evalSignal(sig('ShortSMACrossBelowLongSMA', { short: 5, long: 15 }), st, lv(20)));
});

test('RSI vào vùng quá mua', () => {
  const st = { lc: 10, ag: 1, al: 1 };
  const s = sig('RSICrossAboveOverBoughtLine', { level: 70 });
  assert.ok(cond.evalSignal(s, st, lv(40)));
  assert.ok(!cond.evalSignal(s, st, lv(12)));
  assert.ok(cond.evalSignal(sig('RSIAboveOverBoughtLine', { level: 70 }), st, lv(40)));
  const crash = { lc: 100, ag: 1, al: 1 };
  assert.ok(cond.evalSignal(sig('RSICrossBelowOverSoldLine', { level: 30 }), crash, lv(70)));
  assert.ok(cond.evalSignal(sig('RSIBelowOverSoldLine', { level: 30 }), crash, lv(70)));
  assert.ok(!cond.evalSignal(sig('RSICrossAboveOverSoldLine', { level: 30 }), crash, lv(70)));
  assert.equal(cond.rsiNow({ lc: 10, ag: 1, al: 0 }, 10)[0], 100);
});

test('MFI: giá bằng giá điển hình không có dòng tiền', () => {
  const st = { lh: 1.4, ll: 1.4, lc: 1.4, pmf: 0, nmf: 0, mfi: 0 };
  assert.deepEqual(cond.mfiNow(st, lv(1.4, { high: 1.4, low: 1.4, volume: 1000 })), [0, 100]);
  const st2 = { lh: 1.3, ll: 1.2, lc: 1.3, pmf: 10, nmf: 5, mfi: 66 };
  near(cond.mfiNow(st2, lv(1.25, { high: 1.32, low: 1.23, volume: 100 }))[1], 100 - 100 / (1 + 10 / 5));
  near(cond.mfiNow(st2, lv(1.2, { high: 1.25, low: 1.15, volume: 100 }))[1], 100 - 100 / (1 + 10 / (5 + 1.2 * 100)));
  near(cond.mfiNow(st2, lv(1.4, { high: 1.45, low: 1.35, volume: 100 }))[1], 100 - 100 / (1 + (10 + 1.4 * 100) / 5));
});

test('MFI thiếu cao / thấp trong ngày thì lấy giá hiện tại', () => {
  const st = { lh: 11, ll: 9, lc: 10, pmf: 5, nmf: 5, mfi: 50 };
  assert.deepEqual(cond.mfiNow(st, lv(12, { volume: 10 })), cond.mfiNow(st, lv(12, { high: 12, low: 12, volume: 10 })));
});

test('Bollinger', () => {
  const st = { lc: 10, p19: 10, p20: 10, sd19: 1, sd20: 1 };
  const s = sig('PriceCrossAboveBollingerBands', { std: 2 });
  assert.ok(cond.evalSignal(s, st, lv(16)));
  assert.ok(!cond.evalSignal(s, st, lv(11)));
  assert.ok(cond.evalSignal(sig('PriceAboveBollingerBands', { std: 2 }), st, lv(16)));
  assert.ok(cond.evalSignal(sig('PriceBelowBollingerBands', { std: 2 }), st, lv(5)));
  const mid = (10 * 19 + 16) / 20, sd = Math.sqrt(19 * 36 + 380) / 20;
  const [up, lo] = cond.bbNow(st, 16, 2)[1];
  near(up, mid + 2 * sd);
  near(lo, mid - 2 * sd);
});

test('MACD', () => {
  const st = { e12: 9.9, e26: 10.0, sig: 0.0 };
  assert.ok(cond.evalSignal(sig('MACDCrossAboveZeroLine'), st, lv(12)));
  assert.ok(cond.evalSignal(sig('MACDAboveZeroLine'), st, lv(12)));
  assert.ok(!cond.evalSignal(sig('MACDCrossAboveZeroLine'), st, lv(9)));
  assert.ok(cond.evalSignal(sig('MACDBelowZeroLine'), st, lv(9)));
  assert.ok(cond.evalSignal(sig('MACDCrossAboveSignalLine'), { ...st, sig: 0.0 }, lv(12)));
  assert.equal(cond.macdNow({ e12: null, e26: 1, sig: 1 }, 5), null);
});

test('vượt đỉnh / thủng đáy', () => {
  const st = { hi1m: 20, lo1m: 8, hi1y: 30, lo1y: 5 };
  assert.ok(cond.evalSignal(sig('AbovePreviousHigh', { period: '1m' }), st, lv(21)));
  assert.ok(!cond.evalSignal(sig('AbovePreviousHigh', { period: '1y' }), st, lv(21)));
  assert.ok(cond.evalSignal(sig('BelowPreviousLow', { period: '1m' }), st, lv(7)));
  assert.ok(!cond.evalSignal(sig('BelowPreviousLow', { period: '1y' }), st, lv(7)));
});

test('KL dự kiến vượt trung bình', () => {
  const st = { v4: 100 };
  const s = sig('EstimatedVolumeSurge', { period: 5, pct: 50 });
  assert.ok(cond.evalSignal(s, st, lv(10, { est: 200 })));
  assert.ok(!cond.evalSignal(sig('EstimatedVolumeSurge', { period: 5, pct: 100 }), st, lv(10, { est: 200 })));
  assert.ok(!cond.evalSignal(s, st, lv(10, { est: null })));
});

test('thiếu số thì không khớp và không vỡ', () => {
  const s = sig('PriceCrossAboveSMA', { period: 5 });
  assert.ok(!cond.evalSignal(s, null, lv(11)));
  assert.ok(!cond.evalSignal(s, {}, lv(11)));
  assert.ok(!cond.evalSignal(s, { lc: 10, p5: 10, p4: 10 }, lv(0)));
  assert.ok(!cond.evalSignal({ id: 'KhongCo' }, { lc: 1 }, lv(1)));
});

test('chuẩn hoá tín hiệu từ cài đặt', () => {
  assert.equal(cond.normalizeSignal({ id: 'KhongCo' }), null);
  assert.equal(cond.normalizeSignal('rác'), null);
  assert.deepEqual(cond.normalizeSignal({ id: 'PriceCrossAboveSMA' }).params, { period: 5 });
  assert.deepEqual(sig('PriceCrossAboveSMA', { period: 7 }).params, { period: 5 });
  assert.deepEqual(sig('PriceCrossAboveSMA', { period: 10.0 }).params, { period: 10 });
  assert.deepEqual(sig('RSIAboveOverBoughtLine', { level: 72.5 }).params, { level: 72.5 });
  assert.deepEqual(sig('RSIAboveOverBoughtLine', { level: 500 }).params, { level: 70 });
  assert.deepEqual(sig('PriceAboveBollingerBands', { std: 'abc' }).params, { std: 2 });
  assert.deepEqual(sig('ShortSMACrossAboveLongSMA', { short: 15, long: 15 }).params, { short: 5, long: 15 });
});

test('mô tả tín hiệu', () => {
  assert.equal(cond.describeSignal(sig('PriceCrossAboveSMA', { period: 5 })), 'Giá cắt lên SMA(5)');
  assert.equal(cond.describeSignal(sig('AbovePreviousHigh', { period: '1m' })), 'Giá vượt đỉnh 1 tháng');
  assert.equal(cond.describeSignal(sig('RSICrossAboveOverBoughtLine', { level: 70 })), 'RSI(14) đi vào vùng quá mua (trên 70)');
  assert.equal(cond.describeSignal(sig('EstimatedVolumeSurge', { period: 5, pct: 50 })), 'KL dự kiến vượt TB 5 phiên tối thiểu 50%');
  assert.equal(cond.describeSignal(sig('MACDCrossAboveZeroLine')), 'MACD cắt lên đường 0');
});

test('danh mục cho bộ chọn điều kiện', () => {
  const cat = cond.catalog();
  assert.deepEqual(Object.keys(cat), cond.GROUPS.map(([g]) => g));
  assert.ok(Object.values(cat).every((v) => v.length));
  assert.equal(Object.values(cat).reduce((a, v) => a + v.length, 0), 45 + 79);
  assert.deepEqual(cat.price[0], ['Thay đổi giá 1 tuần (%)', 'metric', 'change1w']);
  assert.ok(cat.ma.some((x) => x[2] === 'PriceCrossAboveSMA' && x[0] === 'Giá cắt lên SMA(…)'));
  assert.ok(cat.macd.some((x) => x[2] === 'MACDCrossAboveZeroLine' && x[0] === 'MACD cắt lên đường 0'));
  assert.equal(cond.paramText('1m'), '1 tháng');
  assert.equal(cond.paramText(70.0), '70');
  assert.equal(cond.paramText(3.5), '3.5');
});

test('danh mục đủ 79 tín hiệu', () => {
  assert.equal(cond.SIGNAL_LIST.length, 79);
  const groups = new Set(cond.GROUPS.map(([g]) => g));
  for (const s of cond.SIGNAL_LIST) {
    assert.ok(groups.has(s.group));
    for (const p of s.params) assert.ok(p.choices.includes(p.default), `${s.id}.${p.id}`);
  }
});

// ── RSI tạo đáy (luật Long hệ phái sinh của anh) + chọn khung 15 phút / ngày ──
// RSI 30 nến 15 phút đã chốt: rơi xuống đáy 23 (13 nến trước) rồi đi lên 44
const RS = [...Array(10).fill(50), 45, 40, 35, 30, 26, 24, 23, 25, 27, 29, 31, 33, 35, 37, 38, 39, 40, 41, 42, 44];
const ev15 = ({ rs = RS, lc = 11, p10 = 10, ...params } = {}) =>
  cond.evalSignal(sig('RSIBottom', { tf: '15m', ...params }), null, { ...lv(lc), intra: { '15m': { rs, lc, p10 } } });

test('RSI tạo đáy: đủ 3 dấu hiệu khung 15 phút', () => {
  assert.equal(ev15(), true);
  assert.equal(ev15({ look: 8 }), false);                         // đáy 23 nằm ngoài 8 nến gần nhất
  assert.equal(ev15({ rs: [...RS.slice(0, -1), 29] }), false);    // RSI chưa thoát vùng 30
  assert.equal(ev15({ rs: [...RS.slice(0, -1), 31] }), false);    // thoát 30 nhưng tụt dưới Signal (WMA14 ≈ 36.3)
  assert.equal(ev15({ lc: 9.9 }), false);                         // giá dưới MA10
  assert.equal(ev15({ level: 25 }), true);
  assert.equal(ev15({ level: 20 }), false);                       // đáy chưa xuống tới 20
  assert.equal(ev15({ rs: RS.slice(-10) }), false);               // thiếu nến (WMA14 cần 14 RSI)
  // Khung 15 phút chỉ đọc thống kê nến 15 phút: chưa tải (hoặc mã ít nến) thì không khớp
  const s = sig('RSIBottom', { tf: '15m' });
  assert.equal(cond.evalSignal(s, { rs: RS, lc: 11, p10: 10 }, lv(11)), false);
  assert.equal(cond.evalSignal(s, { lc: 1 }, { ...lv(11), intra: { '15m': {} } }), false);
});

test('RSI tạo đáy: khung ngày ghép giá hiện tại khớp với nến đã chốt', () => {
  // Rơi đều 60 nến rồi tăng 3 nến (RSI ≈ 28.6): giá hiện tại quyết định nến thứ 4 có đủ 3 dấu hiệu không
  const closes = [...Array.from({ length: 60 }, (_, i) => 60 - 0.5 * i), ...[1, 2, 3].map((j) => 30.5 + 0.8 * j)];
  const [bars, days] = makeBars(closes.length, { close: (i) => closes[i] });
  const st = tech.statsFromBars(bars, addDays(days[days.length - 1], 1), keep);
  const seen = new Set();
  for (const live of [31.5, 32.4, 32.9, 33.3, 33.7, 35]) {
    const c = [...closes, live];
    const intra = tech.intradayStats({ s: 'ok', t: c.map((_, i) => i), o: c, h: c, l: c, c, v: c.map(() => 1) });
    const want = cond.evalSignal(sig('RSIBottom', { tf: '15m' }), null, { ...lv(live), intra: { '15m': intra } });
    assert.equal(cond.evalSignal(sig('RSIBottom', { tf: 'D' }), st, lv(live)), want, String(live));
    seen.add(want);
  }
  assert.deepEqual([...seen].sort(), [false, true]);              // có cả ca khớp lẫn không khớp
});

test('RSI từng nến khớp Wilder', () => {
  const closes = Array.from({ length: 60 }, (_, i) => 10 + (i % 7) - (i % 3) * 0.5);
  const rs = tech.rsiTail(closes);
  assert.equal(rs.length, tech.RSI_KEEP);
  near(rs[rs.length - 1], tech.rsiOf(...tech.wilderRsiParts(closes)));
  near(rs[rs.length - 2], tech.rsiOf(...tech.wilderRsiParts(closes.slice(0, -1))));
  assert.deepEqual(tech.rsiTail(closes.slice(0, 14)), []);
  assert.equal(statsOf(60)[0].rs.length, tech.RSI_KEEP);         // nến ngày cũng giữ RSI từng nến
});

test('nến 15 phút đã chốt', () => {
  const at = (d, h, m) => Date.UTC(2026, 9, d, h - 7, m, 30);     // 29/10 thứ Năm, 31/10 thứ Bảy
  const sec = (d, h, m) => Date.UTC(2026, 9, d, h - 7, m) / 1000;
  assert.equal(tech.intradayCutoff(at(29, 9, 7)), sec(29, 9, 0));
  assert.equal(tech.intradayCutoff(at(29, 11, 29)), sec(29, 11, 15));
  assert.equal(tech.intradayCutoff(at(29, 14, 50)), sec(29, 14, 45));    // nến ATC chờ tới 15:00
  for (const a of [[29, 8, 50], [29, 11, 30], [29, 12, 59], [29, 15, 0], [31, 10, 0]]) {
    assert.equal(tech.intradayCutoff(at(...a)), null, String(a));
  }
  assert.equal(tech.intradayKey(at(29, 9, 7)), '2026-10-29 09:00');
  assert.equal(tech.intradayKey(at(29, 12, 0)), '2026-10-29 11:30');     // nghỉ trưa: đã có nến 11:15 chốt
  assert.equal(tech.intradayKey(at(29, 20, 0)), '2026-10-29 15:00');
  assert.equal(tech.intradayKey(at(29, 8, 0)), '2026-10-29 00:00');
  assert.equal(tech.intradayKey(at(31, 10, 0)), '2026-10-31 00:00');
  assert.equal(tech.intradayKey(at(30, 6, 0)), '2026-10-30 00:00');      // 6h sáng giờ VN = 23h UTC hôm trước
  // Nến có giờ mở từ cutoff trở đi (đang chạy) bị bỏ; null = mọi nến; quá ít nến → null
  const c = Array.from({ length: 70 }, (_, i) => 10 + (i % 5));
  const bars = { s: 'ok', t: c.map((_, i) => i * 900), o: c, h: c, l: c, c, v: c.map(() => 1) };
  const st = tech.intradayStats(bars, 65 * 900);
  assert.deepEqual([st.n, st.lt, st.lc], [65, 64 * 900, c[64]]);
  assert.equal(st.p10, c.slice(55, 65).reduce((a, b) => a + b) / 10);
  assert.equal(tech.intradayStats(bars).n, 70);
  assert.equal(tech.intradayStats(bars, 50 * 900), null);
  assert.equal(tech.intradayStats({ s: 'no_data' }), null);
});

test('RSI tạo đáy: tham số, mô tả và nối vào bộ lọc', () => {
  assert.deepEqual(sig('RSIBottom').params, { tf: '15m', level: 30, look: 16 });
  assert.deepEqual(sig('RSIBottom', { tf: '4h', look: 17 }).params, { tf: '15m', level: 30, look: 16 });
  assert.equal(cond.describeSignal(sig('RSIBottom', { tf: 'D' })),
    'RSI tạo đáy khung ngày: thoát quá bán 30 (đáy trong 16 nến), RSI trên Signal, giá trên MA10');
  assert.equal(cond.paramText('15m'), '15 phút');
  const m15 = { signals: [sig('RSIBottom')] }, day = { signals: [sig('RSIBottom', { tf: 'D' })] };
  assert.deepEqual([core.needsIntraday(m15), core.needsTech(m15)], [true, false]);    // khỏi tải nến ngày cả năm
  assert.deepEqual([core.needsIntraday(day), core.needsTech(day)], [false, true]);
  assert.equal(core.needsIntraday({ signals: [sig('MACDAboveZeroLine')] }), false);
  const q = { Symbol: 'AAA', Exchange: 'HOSTC', PriceCurrent: 11000, TotalVolume: 0 };
  const st = { rs: RS, lc: 11, p10: 10 };
  const row = core.transformQuote(q, null, null, Date.now(), { '15m': st });
  assert.deepEqual(row._live.intra, { '15m': st });
  assert.deepEqual(core.applySignals([row], m15.signals), [row]);
  assert.ok(!('intra' in core.transformQuote(q)._live));
});

// ── Chỉ báo bổ sung (chép class ChiBaoBoSung của tests/test_conditions.py) ──
// Tăng đều: đóng cửa 1..60, cao = đóng + 0.5, thấp = đóng − 0.5, KL 1000
const ST = statsOf(60)[0];
const evB = (id, live, st = ST, params = {}) => cond.evalSignal(sig(id, params), st, live);

test('Parabolic SAR', () => {
  assert.equal(ST.sart, 1);
  assert.ok(ST.sar < 59.5);
  assert.equal(evB('SARUptrend', lv(61, { high: 61.5, low: 60.5 })), true);
  assert.equal(evB('SARFlipDown', lv(61, { high: 61.5, low: 60.5 })), false);
  const crash = lv(50, { high: 60, low: 49 });
  assert.equal(evB('SARFlipDown', crash), true);
  assert.equal(evB('SARDowntrend', crash), true);
  assert.equal(evB('SARUptrend', crash), false);
  assert.equal(evB('SARFlipUp', crash), false);
  assert.deepEqual(tech.sarStep(10, 20, 0.1, true, 21, 15), [11, 21, 0.1 + 0.02, true, false]);
  assert.deepEqual(tech.sarStep(10, 20, 0.1, true, 22, 9), [22, 9, 0.02, false, true]);
});

test('Stochastic và Williams %R', () => {
  near(ST.skr[ST.skr.length - 1], 13.5 / 14 * 100, 5);
  near(ST.skd, 13.5 / 14 * 100, 5);
  assert.equal(evB('StochAboveOverBoughtLine', lv(61, { high: 61.5 }), ST, { level: 80 }), true);
  const drop = lv(50, { high: 60, low: 50 });
  assert.equal(evB('StochKCrossBelowD', drop), true);
  assert.equal(evB('StochCrossBelowOverBoughtLine', drop, ST, { level: 80 }), true);
  assert.equal(evB('WillRCrossBelowOverBoughtLine', drop, ST, { level: 20 }), true);
  assert.equal(evB('StochKCrossAboveD', drop), false);
  assert.equal(tech.rawK(Array(14).fill([0, 1, 5, 5, 5, 1]), 13), null);
});

test('CCI', () => {
  near(tech.cci([1, 2, 3]), 100);
  assert.equal(tech.cci([5, 5, 5]), null);
  assert.equal(evB('CCIAboveOverBoughtLine', lv(70, { high: 70, low: 69 }), ST, { level: 100 }), true);
  assert.equal(evB('CCIBelowOverSoldLine', lv(70, { high: 70, low: 69 }), ST, { level: 100 }), false);
});

test('ADX / DMI', () => {
  assert.deepEqual(tech.dmTr([0, 0, 11, 9, 10], [0, 0, 12, 10, 11]), [1, 0, 2]);
  assert.equal(tech.dxFrac(0, 0), 0);
  const r = cond.dmiNow(ST, lv(61, { high: 61.5, low: 60.5 }));
  assert.ok(r[2] > r[3]);
  assert.ok(r[4] > 25);
  assert.equal(evB('ADXStrongUptrend', lv(61, { high: 61.5, low: 60.5 }), ST, { level: 25 }), true);
  assert.equal(evB('ADXAboveLevel', lv(61, { high: 61.5, low: 60.5 }), ST, { level: 25 }), true);
  assert.equal(evB('DIPlusCrossAboveDIMinus', lv(61, { high: 61.5, low: 60.5 })), false);
});

test('OBV', () => {
  assert.deepEqual([ST.obv, ST.ob19, ST.obm], [59000, 950000, 49500]);
  assert.equal(evB('OBVAboveMA', lv(61, { est: 1000 })), true);
  assert.equal(evB('OBVCrossBelowMA', lv(50, { est: 50000 })), true);
  assert.equal(evB('OBVCrossAboveMA', lv(61, { est: 1000 })), false);
});

test('Ichimoku', () => {
  const st = statsOf(100)[0];
  assert.equal(tech.midRange(tech.closedBars(makeBars(100)[0], '2099-01-01', keep), 99, 9), 96);
  assert.equal(evB('IchimokuAboveCloud', lv(101), st), true);
  assert.equal(evB('IchimokuBelowCloud', lv(101), st), false);
  assert.equal(evB('IchimokuBelowCloud', lv(1), st), true);
  assert.equal(evB('IchimokuAboveCloud', lv(1)), false);
});

test('giá so với MA, EMA cắt nhau', () => {
  assert.equal(evB('PriceAboveSMA', lv(61), ST, { period: 20 }), true);
  assert.equal(evB('PriceBelowSMA', lv(61), ST, { period: 20 }), false);
  assert.equal(evB('PriceBelowEMA', lv(40), ST, { period: 20 }), true);
  assert.equal(evB('ShortSMAAboveLongSMA', lv(61), ST, { short: 5, long: 15 }), true);
  assert.equal(evB('ShortSMAAboveLongSMA', lv(61)), false);
  assert.equal(evB('ShortEMACrossBelowLongEMA', lv(1), ST, { short: 10, long: 20 }), true);
  assert.equal(evB('ShortEMACrossAboveLongEMA', lv(61), ST, { short: 10, long: 20 }), false);
  assert.deepEqual(sig('ShortEMACrossAboveLongEMA', { short: 50, long: 20 }).params, { short: 10, long: 20 });
});

test('cột số chỉ báo', () => {
  const m = cond.indicatorMetrics(ST, lv(61, { high: 61.5, low: 60, volume: 1000 }));
  assert.equal(m.rsi14, 100);
  near(m.fromHigh1m, (61.5 - 61) / 61.5 * 100);
  assert.ok(Math.abs(m.willR - (m.stochK - 100)) <= 5);
  for (const k of ['mfi14', 'stochK', 'cci20', 'bbWidth', 'adx14', 'atrPct', 'fromLow1y']) assert.notEqual(m[k], null, k);
  assert.ok(Object.values(cond.indicatorMetrics(null, lv(61))).every((v) => v === null));
  assert.deepEqual([ST.v50, ST.v100], [1000, null]);
  near(ST.gv20, 50.5 * 1000 / 1e6);
  assert.deepEqual(core.formatMetric(12.345, 'upct'), ['12.3%', '']);
  assert.deepEqual(core.formatMetric(-45.67, 'num'), ['-45.7', '']);
  assert.deepEqual(core.formatMetric(3.46, 'bil'), ['3.5 tỷ', '']);
  // KL dự kiến hôm nay so với KLTB 20 / 50 phiên: "KL ≥ 80% TB 50 phiên" → volVs50 ≥ 80
  const t = cond.techMetrics(ST, 61, 1, 800);
  assert.deepEqual([t.volVs20, t.volVs50], [80, 80]);
  assert.equal(cond.techMetrics(ST, 61, 1).volVs50, null);
  assert.deepEqual(core.formatMetric(80, 'ratio'), ['80%', 'down']);
  assert.deepEqual(core.formatMetric(150.4, 'ratio'), ['150%', 'up']);
});

// ── Cột số kiểu FireAnt ─────────────────────────────────────────────────
test('thay đổi giá nhiều kỳ và chuỗi phiên', () => {
  const st = { px1w: 10, px1m: 8, streak: 2, v5: 500, v3m: 900 };
  let m = cond.techMetrics(st, 11, 0.5);
  near(m.change1w, 10);
  near(m.change1m, 37.5);
  assert.equal(m.change1y, null);
  assert.deepEqual([m.upDays, m.avgVol5, m.avgVol3m], [3, 500, 900]);
  assert.equal(m.downDays, null);
  m = cond.techMetrics(st, 11, -0.5);
  assert.deepEqual([m.upDaysBeforeDown, m.upDays], [2, null]);
  assert.equal(cond.techMetrics({ streak: -3 }, 11, -0.5).downDays, 4);
  m = cond.techMetrics({ streak: -3 }, 11, 0.5);
  assert.deepEqual([m.downDaysBeforeUp, m.downDays], [3, null]);
  assert.equal(cond.techMetrics({ streak: 2 }, 11, 0).upDays, null);
  assert.ok(Object.values(cond.techMetrics(null, 11, 0.5)).every((v) => v === null));
});

test('số lấy thẳng từ quote', () => {
  let m = cond.quoteMetrics({ TotalVolume: 1000, TotalActiveBuyVolume: 600, BuyForeignQuantity: 300,
    SellForeignQuantity: 100, BuyForeignValue: 6e9, SellForeignValue: 2.5e9 });
  assert.deepEqual([m.activeBuyPct, m.foreignNetVol, m.foreignNetValue], [60, 200, 3.5]);
  m = cond.quoteMetrics({ TotalVolume: 0 });
  assert.deepEqual([m.activeBuyPct, m.foreignNetVol, m.foreignNetValue], [null, null, null]);
});

test('định dạng ô', () => {
  const f = core.formatMetric;
  assert.deepEqual(f(12.345, 'pct'), ['+12.35%', 'up']);
  assert.deepEqual(f(-3.0, 'pct'), ['-3.00%', 'down']);
  assert.deepEqual(f(null, 'pct'), ['--', 'muted']);
  assert.deepEqual(f(3, 'int'), ['3', '']);
  assert.deepEqual(f(1500000, 'vol'), ['1.5M', '']);
  assert.deepEqual(f(-250000, 'svol'), ['-250.0K', 'down']);
  assert.deepEqual(f(3.5, 'sbil'), ['+3.5 tỷ', 'up']);
  assert.deepEqual(f(57.4, 'pct0'), ['57%', 'up']);
  assert.deepEqual(core.formatCell({ change1w: 5.5 }, 'change1w'), ['+5.50%', 'up']);
});

// ── Nối vào bộ lọc ──────────────────────────────────────────────────────
const ROW_A = { symbol: 'AAA', exchange: 'HSX', price: 11, change: 0.5, volume: 1000, value: 1.0, change1w: 10.0, upDays: 3,
  foreignNetValue: null, _tech: { lc: 10, p5: 10.2, p4: 10 }, _live: lv(11) };
const ROW_B = { symbol: 'BBB', exchange: 'HSX', price: 9, change: -0.5, volume: 500, value: 0.5, change1w: -4.0, upDays: null,
  foreignNetValue: 2.0, _tech: { lc: 10, p5: 10.2, p4: 10 }, _live: lv(9) };
const syms = (rows) => rows.map((r) => r.symbol);

test('toán tử ≥ ≤ trong khoảng', () => {
  const f = (op, v, v2 = null) => ({ change1w: { operator: op, value: v, value2: v2 } });
  assert.deepEqual(syms(core.applyFilters([ROW_A, ROW_B], f('ge', 10))), ['AAA']);
  assert.deepEqual(syms(core.applyFilters([ROW_A, ROW_B], f('gt', 10))), []);
  assert.deepEqual(syms(core.applyFilters([ROW_A, ROW_B], f('le', -4))), ['BBB']);
  assert.deepEqual(syms(core.applyFilters([ROW_A, ROW_B], f('bt', -5, 11))), ['AAA', 'BBB']);
  assert.deepEqual(syms(core.applyFilters([ROW_A, ROW_B], f('bt', 11, -5))), ['AAA', 'BBB']);
  assert.deepEqual(syms(core.applyFilters([ROW_A, ROW_B], f('bt', 0, 5))), []);
  assert.deepEqual(core.activeFilterKeys(f('bt', 0, null)), []);
  assert.deepEqual(core.activeFilterKeys(f('ge', 0, null)), ['change1w']);
});

test('cột mới thiếu số thì loại, cột cũ thiếu số coi như 0', () => {
  assert.deepEqual(syms(core.applyFilters([ROW_A, ROW_B], { foreignNetValue: { operator: 'lt', value: 100 } })), ['BBB']);
  assert.deepEqual(syms(core.applyFilters([ROW_A, ROW_B], { volRatio: { operator: 'lt', value: 100 } })), ['AAA', 'BBB']);
  assert.deepEqual(core.activeFilterKeys({ khongCoCot: { operator: 'gt', value: 1 } }), []);
});

test('lọc cả cột và tín hiệu phải thoả hết', () => {
  const all = { HSX: [ROW_A, ROW_B], HNX: [], UPCOM: [] };
  const cfg = { exchange: 'HSX', filters: { change1w: { operator: 'ge', value: -10 } },
    signals: [sig('PriceCrossAboveSMA', { period: 5 })], sortColumn: 'value', sortDirection: 'desc' };
  assert.deepEqual(syms(core.selectMatches(all, cfg)), ['AAA']);
  cfg.signals = [sig('PriceCrossAboveSMA', { period: 5 }), sig('PriceCrossBelowSMA', { period: 5 })];
  assert.deepEqual(core.selectMatches(all, cfg), []);
  delete cfg.signals;
  assert.equal(core.selectMatches(all, cfg).length, 2);
});

test('tiêu chí mang theo tín hiệu', () => {
  const c = core.criteriaFromConfig({ criteria: [
    { name: 'Cắt SMA', exchange: 'HSX', signals: [{ id: 'PriceCrossAboveSMA', params: { period: 10 } }, { id: 'KhongCo' }, 'rác'] },
    { name: 'Thường', filters: { price: { operator: 'lt', value: 20 } } }] });
  assert.deepEqual(c[0].signals, [{ id: 'PriceCrossAboveSMA', params: { period: 10 } }]);
  assert.ok(!('signals' in c[1]));
  assert.ok(core.hasConditions(c[0]));
  assert.ok(core.hasConditions(c[1]));
  assert.ok(!core.hasConditions({ filters: {} }));
  const other = { ...c[0], signals: [{ id: 'PriceCrossAboveSMA', params: { period: 20 } }] };
  assert.notEqual(core.criterionKey(c[0]), core.criterionKey(other));
  assert.equal(core.criterionKey(c[1]), core.criterionKey({ exchange: 'HSX', filters: { price: { operator: 'lt', value: 20 } } }));
});

test('cần tải lịch sử năm chỉ khi dùng điều kiện kỹ thuật', () => {
  assert.ok(!core.needsTech({ filters: { price: { operator: 'lt', value: 20 }, foreignNetValue: { operator: 'gt', value: 1 } } }));
  assert.ok(core.needsTech({ filters: { change1m: { operator: 'gt', value: 5 } } }));
  assert.ok(core.needsTech({ filters: {}, signals: [sig('MACDAboveZeroLine')] }));
});

test('cột hiện ra và mô tả', () => {
  const filters = { price: { operator: 'lt', value: 20 }, change1m: { operator: 'bt', value: 5, value2: 15 },
    upDays: { operator: 'ge', value: 3 } };
  assert.deepEqual(core.compactColumns(filters).map((c) => c[0]), ['symbol', 'price', 'change1m', 'upDays']);
  assert.equal(core.tableColumns({ exchange: 'HSX', filters }, true).length, 13);
  assert.equal(core.describeFilters(filters, [sig('PriceCrossAboveSMA', { period: 5 })]),
    'Giá < 20 · Thay đổi giá 1 tháng (%) từ 5 đến 15 · Số phiên tăng giá liên tục ≥ 3 · Giá cắt lên SMA(5)');
  assert.equal(core.HEAD_LABEL.change1m, '% 1 tháng');
  const withSig = { exchange: 'HSX', filters: { avgVol20: { operator: 'ge', value: 1 } }, signals: [sig('MACDAboveZeroLine')] };
  assert.deepEqual(core.tableColumns(withSig, false).map((c) => c[0]), ['symbol', 'price', 'changePercent', 'avgVol20']);
  assert.deepEqual(core.tableColumns({ exchange: 'HSX', filters: {}, signals: [sig('MACDAboveZeroLine')] }, false).map((c) => c[0]),
    ['symbol', 'price', 'changePercent']);
  assert.deepEqual(core.tableColumns({ exchange: 'HSX', filters: { avgVol20: { operator: 'ge', value: 1 } } }, false).map((c) => c[0]),
    ['symbol', 'avgVol20']);
  assert.equal(core.tableColumns(withSig, true).length, 12);
});

test('quote đi qua transform mang đủ số', () => {
  const [bars, days] = makeBars(60);
  const st = tech.statsFromBars(bars, addDays(days[days.length - 1], 1), keep);
  const q = { Symbol: 'AAA', Exchange: 'HOSTC', PriceCurrent: 66000, PriceChange: 6000, PriceHigh: 67000, PriceLow: 61000,
    TotalVolume: 5000, TotalValue: 3e8, TotalActiveBuyVolume: 3000, Date: '2026-10-14T08:00:00Z' };
  const now = vnAt(10, 0);
  let r = core.transformQuote(q, null, st, now);
  assert.deepEqual([r.price, r.change], [66, 6]);
  near(r.change1w, (66 - 54) * 100 / 54);
  assert.deepEqual([r.upDays, r.activeBuyPct], [60, 60]);
  assert.deepEqual(r._live, { last: 66, high: 67, low: 61, volume: 5000, est: 5000 * 255 / 60 });
  r = core.transformQuote({ ...q, Date: '2026-10-09T08:00:00Z' }, null, st, now);
  assert.equal(r._live.est, 5000);
  r = core.transformQuote(q, null, null, now);
  assert.equal(r.change1w, null);
  assert.deepEqual(core.applySignals([r], [sig('MACDAboveZeroLine')]), []);
});
