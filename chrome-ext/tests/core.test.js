// Chép tests/test_core.py (bỏ phần tự cập nhật và cookie FireAnt — bản extension không có hai việc đó).
import { test } from 'node:test';
import assert from 'node:assert/strict';
import * as core from '../lib/core.js';

const VIB = { symbol: 'VIB', price: 14.2, change: 0.3, changePercent: 2.54, volume: 3000000, volRatio: 0, value: 42.9, demandStrength: 76 };
const FPT = { symbol: 'FPT', price: 98.5, change: -1.2, changePercent: -1.2, volume: 5200000, volRatio: 130, value: 512.3, demandStrength: 40 };
const HPG = { symbol: 'HPG', price: 26.1, change: 0.4, changePercent: 1.56, volume: 800000, volRatio: 90, value: 20.8, demandStrength: null };
const FILTERS = { price: { operator: 'lt', value: 20 }, changePercent: { operator: 'gt', value: 2 }, volume: { operator: 'gt', value: 1000000 } };
// Quote FireAnt thật của VIB lúc 10:04 ngày 14/10/2026 (rút gọn trường)
const VIB_Q = { Symbol: 'VIB', Name: 'Ngân hàng TMCP Quốc tế Việt Nam', Exchange: 'HOSTC', PriceCurrent: 14000, PriceChange: 200,
  PricePercentChange: 0.01449275362318847, TotalVolume: 4505800, TotalValue: 63403235000, TotalActiveBuyVolume: 2566950,
  PriceAverage: 14071.4712148786 };
const syms = (rows) => rows.map((s) => s.symbol);

test('chỉ giữ mã thoả hết điều kiện', () => {
  assert.deepEqual(syms(core.applyFilters([VIB, FPT, HPG], FILTERS)), ['VIB']);
});

test('bỏ qua lọc rỗng, thiếu giá trị coi như 0', () => {
  assert.equal(core.applyFilters([VIB, FPT], { price: { operator: 'gt', value: '' } }).length, 2);
  assert.equal(core.applyFilters([HPG], { demandStrength: { operator: 'lt', value: 1 } }).length, 1);
});

test('thu gọn hiện mã và cột đang lọc', () => {
  assert.deepEqual(core.compactColumns(FILTERS).map((c) => c[0]), ['symbol', 'price', 'changePercent', 'volume']);
  assert.deepEqual(core.compactColumns({}).map((c) => c[0]), ['symbol']);
});

test('lọc theo sàn và sắp xếp', () => {
  const all = { HSX: [VIB, HPG], HNX: [FPT], UPCOM: [] };
  const cfg = { exchange: 'HSX', filters: { volume: { operator: 'gt', value: 0 } }, sortColumn: 'value', sortDirection: 'desc' };
  assert.deepEqual(syms(core.selectMatches(all, cfg)), ['VIB', 'HPG']);
  assert.deepEqual(syms(core.selectMatches(all, { ...cfg, exchange: 'ALL' })), ['FPT', 'VIB', 'HPG']);
  assert.deepEqual(syms(core.selectMatches(all, { ...cfg, sortColumn: 'symbol', sortDirection: 'asc' })), ['HPG', 'VIB']);
  assert.deepEqual(syms(core.sortStocks([HPG, VIB], 'demandStrength', 'desc')), ['VIB', 'HPG']);
});

test('cả 3 sàn thêm cột Sàn', () => {
  const cfg = { exchange: 'ALL', filters: FILTERS };
  assert.deepEqual(core.tableColumns(cfg, false).map((c) => c[0]), ['symbol', 'price', 'changePercent', 'volume']);
  assert.deepEqual(core.tableColumns(cfg, true).map((c) => c[0]).slice(0, 2), ['symbol', 'exchange']);
  assert.equal(core.tableColumns(cfg, true).length, 12);
  assert.ok(!core.tableColumns({ ...cfg, exchange: 'HSX' }, true).some((c) => c[0] === 'exchange'));
  assert.deepEqual(core.formatCell({ exchange: 'UPCOM' }, 'exchange'), ['UpCom', 'muted']);
});

test('bấm tiêu đề cột để sắp xếp', () => {
  assert.deepEqual(core.nextSort('value', 'desc', 'value'), ['value', 'asc']);
  assert.deepEqual(core.nextSort('value', 'asc', 'value'), ['value', 'desc']);
  assert.deepEqual(core.nextSort('value', 'desc', 'changePercent'), ['changePercent', 'desc']);
  assert.deepEqual(core.nextSort('value', 'desc', 'symbol'), ['symbol', 'asc']);
  const rows = [{ symbol: 'A', exchange: 'HSX', value: 1 }, { symbol: 'B', exchange: 'HNX', value: 5 }, { symbol: 'C', exchange: 'HSX', value: 9 }];
  assert.deepEqual(syms(core.sortStocks(rows, 'exchange', 'asc')), ['B', 'C', 'A']);
});

test('định dạng giống hàng VIB', () => {
  assert.deepEqual(core.formatCell(VIB, 'symbol'), ['VIB', 'up']);
  assert.deepEqual(core.formatCell(FPT, 'symbol'), ['FPT', 'down']);
  assert.equal(core.HEAD_LABEL.changePercent, '%');
  assert.deepEqual(core.formatCell(VIB, 'price'), ['14.2', 'up']);
  assert.equal(core.formatCell(VIB, 'change')[0], '+0.3');
  assert.deepEqual(core.formatCell(VIB, 'changePercent'), ['+2.54%', 'up']);
  assert.equal(core.formatCell(VIB, 'volume')[0], '3.0M');
  assert.equal(core.formatCell(VIB, 'value')[0], '42.9 tỷ');
  assert.deepEqual(core.formatCell(VIB, 'demandStrength'), ['76%', 'up']);
  assert.deepEqual(core.formatCell(FPT, 'changePercent'), ['-1.20%', 'down']);
  assert.equal(core.formatCell(HPG, 'demandStrength')[0], '—');
  assert.equal(core.formatCell({ ma10: 11.0 }, 'ma10')[0], '11');
});

test('làm tròn như JavaScript', () => {
  assert.equal(core.formatPrice(0.25), '0.3');
  assert.equal(core.formatPrice(13.95), '13.9');
  assert.equal(core.formatVolume(999), '999');
});

test('câu đọc mã mới', () => {
  assert.deepEqual(core.alertText(['VIB', 'MBB']), ['Mã mới: V I B, M B B.', 'New: V I B, M B B.']);
  const [vi, en] = core.alertText(['A1', 'B2', 'C3', 'D4', 'E5', 'F6', 'G7']);
  assert.equal(vi, 'Mã mới: A 1, B 2, C 3, D 4, E 5, và 2 mã khác.');
  assert.ok(en.endsWith('and 2 more.'));
});

test('nhiều tiêu chí', () => {
  const old = core.criteriaFromConfig({ exchange: 'ALL', filters: FILTERS });
  assert.deepEqual(old, [{ name: 'Tiêu chí 1', exchange: 'ALL', filters: FILTERS, alert: 'speak' }]);
  const mixed = core.criteriaFromConfig({ alert: 'off', criteria: [{ name: 'A', alert: 'beep' }, { name: 'B' }, { name: 'C', alert: 'lung tung' }] });
  assert.deepEqual(mixed.map((c) => c.alert), ['beep', 'off', 'off']);
  assert.equal(core.criterionKey(mixed[0]), core.criterionKey({ ...mixed[0], alert: 'speak' }));
  const fresh = core.criteriaFromConfig({ criteria: [{ name: 'Đột biến KL', exchange: 'HSX', filters: {} }, { name: '  ', filters: FILTERS }] });
  assert.deepEqual(fresh.map((c) => c.name), ['Đột biến KL', 'Tiêu chí 2']);
  assert.equal(fresh[1].exchange, 'HSX');
  assert.equal(core.criterionKey({ ...fresh[0], name: 'X' }), core.criterionKey(fresh[0]));
  assert.notEqual(core.criterionKey(fresh[0]), core.criterionKey(fresh[1]));
});

test('mỗi tiêu chí xếp riêng', () => {
  const c = core.criteriaFromConfig({ sortColumn: 'volRatio', sortDirection: 'asc',
    criteria: [{ name: 'A' }, 'rác', { name: 'B', sortColumn: 'price', sortDirection: 'desc' }, { name: 'C', sortColumn: 'volume' }] });
  assert.deepEqual(c.map((x) => [x.sortColumn, x.sortDirection]), [['volRatio', 'asc'], ['price', 'desc'], ['volume', 'asc']]);
  const legacy = core.criteriaFromConfig({ sortColumn: 'value', sortDirection: 'desc', filters: FILTERS });
  assert.deepEqual([legacy[0].sortColumn, legacy[0].sortDirection], ['value', 'desc']);
  assert.ok(!('sortColumn' in core.criteriaFromConfig({ criteria: [{ name: 'A' }] })[0]));
  const all = { HSX: [VIB, FPT, HPG], HNX: [], UPCOM: [] };
  const base = { exchange: 'HSX', filters: { volume: { operator: 'gt', value: 0 } } };
  const a = { ...base, sortColumn: 'price', sortDirection: 'asc' };
  const b = { ...base, sortColumn: 'price', sortDirection: 'desc' };
  assert.deepEqual(syms(core.selectMatches(all, a)), ['VIB', 'HPG', 'FPT']);
  assert.deepEqual(syms(core.selectMatches(all, b)), ['FPT', 'HPG', 'VIB']);
  assert.equal(core.criterionKey(a), core.criterionKey(b));
});

test('câu đọc nhiều tiêu chí', () => {
  assert.equal(core.alertTextGroups([['A', ['VIB']]])[0], 'Mã mới: V I B.');
  assert.equal(core.alertTextGroups([['bùng nổ KL', ['HHP']]], 6, true)[0], 'bùng nổ KL: H H P.');
  assert.equal(core.alertTextGroups([['Đột biến KL', ['HHP', 'VEA']], ['Vượt MA20', ['MBB']], ['Trống', []]])[0],
    'Đột biến KL: H H P, V E A. Vượt MA20: M B B.');
  assert.equal(core.alertTextGroups([['A', [...'ABCDE']], ['B', [...'FGHI']]])[0], 'A: A, B, C, D, E. B: F. Và 3 mã khác.');
});

test('mô tả bộ lọc', () => {
  assert.equal(core.describeFilters(FILTERS), 'Giá < 20 · % Thay đổi > 2 · KLGD > 1000000');
});

test('danh mục theo dõi', () => {
  assert.deepEqual(core.parseSymbols(' vib, mbb;;VIB  hpg\n'), ['VIB', 'MBB', 'HPG']);
  assert.deepEqual(core.parseSymbols(['vib', 'VIB', 'fpt']), ['VIB', 'FPT']);
  assert.deepEqual(core.parseSymbols(null), []);
  const rows = [VIB, FPT, HPG];
  assert.deepEqual(syms(core.selectWatch(rows, ['HPG', 'XYZ', 'VIB'])), ['HPG', 'VIB']);
  assert.deepEqual(syms(core.selectWatch(rows, ['HPG', 'FPT', 'VIB'], 'changePercent', 'desc')), ['VIB', 'HPG', 'FPT']);
  assert.deepEqual(core.selectWatch(rows, []), []);
  const hnx = { ...FPT, exchange: 'HNX' };
  assert.deepEqual(syms(core.selectWatch([{ ...VIB, exchange: 'HSX' }, hnx], ['FPT', 'VIB'])), ['FPT', 'VIB']);
  const wc = { name: core.WATCH_NAME, exchange: 'ALL', filters: {}, watch: true };
  assert.deepEqual(core.tableColumns(wc, false).map((c) => c[0]), ['symbol', 'price', 'changePercent']);
  const full = core.tableColumns(wc, true).map((c) => c[0]);
  assert.deepEqual([full.slice(0, 2), full.length], [['symbol', 'exchange'], 12]);
  assert.ok(!core.hasConditions(wc));
});

test('giờ giao dịch theo giờ VN', () => {
  const ts = (y, mo, d, h, mi) => Date.UTC(y, mo - 1, d, h, mi) / 1000;
  assert.ok(core.isTradingTime(ts(2026, 10, 14, 3, 0)));
  assert.ok(!core.isTradingTime(ts(2026, 10, 14, 9, 0)));
  assert.ok(!core.isTradingTime(ts(2026, 10, 17, 3, 0)));
});

test('đổi quote FireAnt sang hàng bảng giá', () => {
  const r = core.transformQuote(VIB_Q, { ma10: 13.7, ma20: 13.6, ma45: 13.4, avgVol: 4505800 / 2 });
  assert.deepEqual([r.symbol, r.exchange, r.price, r.change], ['VIB', 'HSX', 14, 0.2]);
  assert.deepEqual([r.changePercent, r.volume, r.value, r.volRatio], [1.45, 4505800, 63.4, 200]);
  assert.equal(r.ma10, 13.7);
  assert.equal(r.demandStrength, 57);
});

test('thiếu lịch sử không vỡ', () => {
  const r = core.transformQuote(VIB_Q, null);
  assert.equal(r.ma10, null);
  assert.equal(r.volRatio, null);
  assert.deepEqual(core.formatCell(r, 'volRatio'), ['--', 'muted']);
  assert.deepEqual(core.applyFilters([r], { volRatio: { operator: 'lt', value: 1 } }), [r]);
});

test('trần / sàn có màu riêng', () => {
  const base = { ...VIB_Q, PriceCeiling: 15000, PriceFloor: 13000 };
  const up = core.transformQuote({ ...base, PriceCurrent: 15000, PriceChange: 1000, PricePercentChange: 0.0714 });
  const down = core.transformQuote({ ...base, PriceCurrent: 13000, PriceChange: -1000, PricePercentChange: -0.0714 });
  const mid = core.transformQuote(base);
  assert.deepEqual([up.limit, down.limit, mid.limit], ['ceil', 'floor', null]);
  for (const key of ['symbol', 'price', 'change', 'changePercent']) {
    assert.equal(core.formatCell(up, key)[1], 'ceil');
    assert.equal(core.formatCell(down, key)[1], 'floor');
    assert.equal(core.formatCell(mid, key)[1], 'up');
  }
  assert.equal(core.formatCell(up, 'volume')[1], '');
  assert.deepEqual(core.formatCell(down, 'changePercent'), ['-7.14%', 'floor']);
  assert.equal(core.transformQuote(VIB_Q).limit, null);
  assert.equal(core.transformQuote({ ...base, PriceCurrent: 0, PriceFloor: 0 }).limit, null);
  assert.equal(core.transformQuote({ ...base, PriceCurrent: null }).limit, null);
});

test('lực cầu bỏ mã nhiễu', () => {
  assert.equal(core.lucCau({ ...VIB_Q, TotalValue: 50_000_000 }), null);
  assert.equal(core.lucCau({ ...VIB_Q, TotalVolume: 20_000 }), null);
  assert.equal(core.lucCau({ ...VIB_Q, TotalActiveBuyVolume: 4_000_000 }), null);
});

test('gom theo sàn, bỏ OTC', () => {
  const rows = ['HOSTC', 'HASTC', 'UPCOM', 'OTC'].map((ex, i) => core.transformQuote({ ...VIB_Q, Symbol: `X${i}`, Exchange: ex }));
  const g = core.groupByExchange(rows);
  assert.deepEqual([g.HSX.length, g.HNX.length, g.UPCOM.length], [1, 1, 1]);
});

test('MA trên phiên đã đóng, bỏ nến hôm nay', () => {
  const start = Date.UTC(2026, 7, 1) / 1000;
  const n = 50;
  const t = Array.from({ length: n }, (_, i) => start + i * 86400);
  const c = Array.from({ length: n }, (_, i) => i + 1);
  const v = Array(n).fill(1000);
  c[n - 1] = 999; v[n - 1] = 999999;
  const s = core.histStats({ s: 'ok', t, c, v }, core.vnDate(t[n - 1]));
  assert.deepEqual([s.ma10, s.ma20, s.ma45, s.avgVol], [44.5, 39.5, 27, 1000]);
});

test('lịch sử ngắn hoặc không có', () => {
  const s = core.histStats({ s: 'ok', t: [1, 2, 3], c: [1, 2, 3], v: [1, 1, 1] }, '2099-01-01');
  assert.equal(s.ma45, null);
  assert.equal(s.avgVol, 0);
  assert.equal(core.histStats({ s: 'no_data' }, '2099-01-01'), null);
  assert.equal(core.histStats(null, '2099-01-01'), null);
});
