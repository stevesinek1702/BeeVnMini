// Tạo tiêu chí bằng AI (lib/ai.js) + tiêu chí mẫu (core.TEMPLATES). Không gọi mạng: fetch giả.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import * as ai from '../lib/ai.js';
import * as core from '../lib/core.js';
import * as cond from '../lib/conditions.js';

const EXAMPLE = {
  name: 'Giá >10k, KLTB50 >100k, cách đỉnh <35%', exchange: 'HSX',
  filters: { price: { operator: 'gt', value: 10 }, avgVol50: { operator: 'gt', value: 100000 }, fromHigh1y: { operator: 'lt', value: 35 } },
  signals: [{ id: 'PriceAboveSMA', params: { period: 20 } }], unsupported: [], note: 'ok',
};

test('câu lệnh gửi AI có đủ danh mục cột và tín hiệu', () => {
  const p = ai.systemPrompt();
  for (const [k] of core.FILTERABLE) assert.ok(p.includes(`\n${k} | `), k);
  for (const k of cond.METRIC_KEYS) assert.ok(p.includes(`\n${k} | `), k);
  for (const s of cond.SIGNAL_LIST) assert.ok(p.includes(`\n${s.id} | `), s.id);
  assert.ok(p.includes('tf: một trong "15m", "D"'));
  assert.ok(p.length < 40000);
});

test('đọc câu trả lời của AI', () => {
  const r = ai.parseReply('```json\n' + JSON.stringify(EXAMPLE) + '\n```');
  assert.deepEqual(r.crit, {
    name: EXAMPLE.name, exchange: 'HSX', alert: 'speak', filters: EXAMPLE.filters,
    signals: [{ id: 'PriceAboveSMA', params: { period: 20 } }],
  });
  assert.deepEqual([r.issues, r.unsupported, r.note], [[], [], 'ok']);
  assert.equal(core.describeFilters(r.crit.filters, r.crit.signals),
    'Giá > 10 · KLTB 50 phiên > 100000 · Giá cách đỉnh 1 năm (%) < 35 · Giá đang trên SMA(20)');
});

test('AI trả sai thì bỏ phần sai, báo rõ', () => {
  const r = ai.parseReply(JSON.stringify({
    exchange: 'NYSE',
    filters: { pe: { operator: 'lt', value: 10 }, price: { operator: 'bt', value: 10 }, value: { operator: 'ge', value: '5,5' } },
    signals: [{ id: 'Khong' }, { id: 'RSIBottom', params: { tf: '4h' } }, { id: 'RSIBottom', params: { tf: '4h' } }],
    unsupported: ['P/E dưới 10'],
  }));
  assert.equal(r.crit.exchange, 'ALL');
  assert.equal(r.crit.name, 'Tiêu chí AI');
  assert.deepEqual(r.crit.filters, { value: { operator: 'ge', value: 5.5 } });
  assert.deepEqual(r.crit.signals, [{ id: 'RSIBottom', params: { tf: '15m', level: 30, look: 16 } }]);    // trùng → 1
  assert.equal(r.issues.length, 5);
  assert.deepEqual(r.unsupported, ['P/E dưới 10']);
  assert.throws(() => ai.parseReply('xin lỗi, tôi không hiểu'), /JSON/);
  assert.throws(() => ai.parseReply('{hỏng'), /JSON/);
});

test('địa chỉ gọi từng hãng', () => {
  assert.equal(ai.endpoint({ provider: 'deepseek' }), 'https://api.deepseek.com/chat/completions');
  assert.equal(ai.endpoint({ provider: 'gemini', model: 'gemini-x' }),
    'https://generativelanguage.googleapis.com/v1beta/models/gemini-x:generateContent');
  assert.equal(ai.endpoint({ provider: 'custom', url: 'https://muse.example/v1/' }), 'https://muse.example/v1/chat/completions');
  assert.equal(ai.endpoint({ provider: 'custom', url: 'https://x.vn/v1/chat/completions' }), 'https://x.vn/v1/chat/completions');
});

const fakeFetch = (status, body, seen) => async (url, init) => {
  seen.push({ url, init: { ...init, body: JSON.parse(init.body) } });
  return { ok: status < 300, status, json: async () => body };
};

test('gọi DeepSeek / Gemini / máy chủ khác (fetch giả)', async () => {
  const seen = [];
  let r = await ai.ask({ provider: 'deepseek', key: 'sk-1' }, 'giá trên 10k',
    fakeFetch(200, { choices: [{ message: { content: JSON.stringify(EXAMPLE) } }] }, seen));
  assert.equal(r.crit.filters.price.value, 10);
  assert.equal(seen[0].init.headers.Authorization, 'Bearer sk-1');
  assert.deepEqual(seen[0].init.body.response_format, { type: 'json_object' });
  assert.equal(seen[0].init.body.model, 'deepseek-chat');
  assert.equal(seen[0].init.body.messages[1].content, 'giá trên 10k');

  r = await ai.ask({ provider: 'gemini', key: 'AIza1' }, 'x',
    fakeFetch(200, { candidates: [{ content: { parts: [{ text: JSON.stringify(EXAMPLE) }] } }] }, seen));
  assert.equal(r.crit.exchange, 'HSX');
  assert.equal(seen[1].init.headers['x-goog-api-key'], 'AIza1');
  assert.ok(!seen[1].url.includes('AIza1'));                       // khoá không nằm trên địa chỉ
  assert.equal(seen[1].init.body.generationConfig.responseMimeType, 'application/json');

  r = await ai.ask({ provider: 'custom', url: 'http://localhost:9/v1', model: 'muse-1' }, 'x',
    fakeFetch(200, { choices: [{ message: { content: JSON.stringify(EXAMPLE) } }] }, seen));
  assert.equal(seen[2].init.headers.Authorization, undefined);      // máy chủ riêng có thể không cần khoá
  assert.equal(seen[2].init.body.response_format, undefined);
  assert.equal(seen[2].init.body.model, 'muse-1');

  await assert.rejects(ai.ask({ provider: 'deepseek', key: 'x' }, 'x', fakeFetch(401, { error: { message: 'bad key' } }, seen)),
    /Khoá API sai/);
  await assert.rejects(ai.ask({ provider: 'deepseek', key: 'x' }, 'x', fakeFetch(402, {}, seen)), /hết tiền/);
  await assert.rejects(ai.ask({ provider: 'deepseek', key: 'x' }, 'x', fakeFetch(200, { choices: [] }, seen)), /trống/);
  await assert.rejects(ai.ask({ provider: 'deepseek', key: 'x' }, 'x', async () => { throw new Error('mất mạng'); }),
    /Không gọi được/);
});

test('tiêu chí mẫu đều hợp lệ', () => {
  assert.ok(core.TEMPLATES.length >= 8);
  for (const t of core.TEMPLATES) {
    assert.ok(t.name && t.desc, t.name);
    const [c] = core.criteriaFromConfig({ criteria: [t] });
    assert.deepEqual(c.signals || [], t.signals || [], t.name);       // tín hiệu đã chuẩn hoá, không bị đổi
    assert.equal(core.activeFilterKeys(t.filters).length, Object.keys(t.filters).length, t.name);
    assert.ok(core.hasConditions(c), t.name);
  }
});
