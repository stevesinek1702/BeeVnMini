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
  assert.ok(p.includes('tf: khung nến (xem luật "Khung nến"; mặc định "15m")'));       // RSI tạo đáy
  assert.ok(p.includes('tf: khung nến (xem luật "Khung nến"; mặc định "D")'));         // các tín hiệu chỉ báo khác
  assert.ok(p.includes('"15m" (15 phút), "30m" (30 phút), "1h" (1 giờ), "2h" (2 giờ), "4h" (4 giờ), "D" (ngày), "W" (tuần)'));
  assert.ok(p.includes('\nrsi14@1h | RSI(14) hiện tại · khung 1 giờ | '));
  assert.ok(p.length < 40000, p.length);
});

test('đọc câu trả lời của AI', () => {
  const r = ai.parseReply('```json\n' + JSON.stringify(EXAMPLE) + '\n```');
  assert.deepEqual(r.crit, {
    name: EXAMPLE.name, exchange: 'HSX', alert: 'speak', filters: EXAMPLE.filters,
    signals: [{ id: 'PriceAboveSMA', params: { tf: 'D', period: 20 } }],
  });
  assert.deepEqual([r.issues, r.unsupported, r.note], [[], [], 'ok']);
  assert.equal(core.describeFilters(r.crit.filters, r.crit.signals),
    'Giá > 10 · KLTB 50 phiên > 100000 · Giá cách đỉnh 1 năm (%) < 35 · Giá đang trên SMA(20)');
});

test('AI trả sai thì bỏ phần sai, báo rõ', () => {
  const r = ai.parseReply(JSON.stringify({
    exchange: 'NYSE',
    filters: { pe: { operator: 'lt', value: 10 }, price: { operator: 'bt', value: 10 }, value: { operator: 'ge', value: '5,5' } },
    signals: [{ id: 'Khong' }, { id: 'RSIBottom', params: { tf: '3h' } }, { id: 'RSIBottom', params: { tf: '3h' } }],
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

test('đọc lời gọi hàm (dạng mảng) — đúng câu trả lời thật của Muse, toán tử ">" thay vì "gt"', () => {
  const args = { name: 'Giá trên 10k, KLTB 20 phiên trên 200.000', exchange: 'HOSE',
    filters: [{ column: 'price', operator: '>', value: 10 }, { column: 'avgVol20', operator: '>', value: 200000 },
      { column: 'volVs50', operator: '>=', value: '80' }, { column: 'fromHigh1y', operator: '≤', value: '35' },
      { column: 'value', operator: 'between', value: 5, value2: 50 }, { column: 'volume', operator: '>', value: '200.000' }],
    signals: [{ id: 'PriceAboveSMA', params: [{ name: 'period', value: '50' }] }, { id: 'RSIBottom', params: [{ name: 'tf', value: 'D' }] }] };
  const r = ai.parseReply(args);
  assert.deepEqual(r.crit.filters, {
    price: { operator: 'gt', value: 10 }, avgVol20: { operator: 'gt', value: 200000 }, volVs50: { operator: 'ge', value: 80 },
    fromHigh1y: { operator: 'le', value: 35 }, value: { operator: 'bt', value: 5, value2: 50 }, volume: { operator: 'gt', value: 200000 } });
  assert.deepEqual(r.crit.signals, [{ id: 'PriceAboveSMA', params: { tf: 'D', period: 50 } }, { id: 'RSIBottom', params: { tf: 'D', level: 30, look: 16 } }]);
  assert.equal(r.crit.exchange, 'HSX');
  assert.deepEqual(r.issues, []);
});

test('hàm AI phải gọi: khuôn dữ liệu dùng mảng (Gemini cũng nhận)', () => {
  const p = ai.TOOL.parameters;
  assert.equal(ai.TOOL.name, 'tao_tieu_chi_loc');
  assert.deepEqual(p.required, ['name', 'exchange', 'filters', 'signals']);
  assert.equal(p.properties.filters.type, 'array');
  assert.equal(p.properties.signals.items.properties.params.type, 'array');
  assert.ok(!JSON.stringify(ai.TOOL).includes('additionalProperties'));
});

test('địa chỉ gọi từng hãng', () => {
  assert.equal(ai.endpoint({ provider: 'muse' }), 'https://api.botai.id.vn/v1/chat/completions');
  assert.equal(ai.endpoint({}), 'https://api.botai.id.vn/v1/chat/completions');
  assert.equal(ai.endpoint({ provider: 'deepseek' }), 'https://api.deepseek.com/chat/completions');
  assert.equal(ai.endpoint({ provider: 'gemini', model: 'gemini-x' }),
    'https://generativelanguage.googleapis.com/v1beta/models/gemini-x:generateContent');
  assert.equal(ai.endpoint({ provider: 'custom', url: 'https://muse.example/v1/' }), 'https://muse.example/v1/chat/completions');
  assert.equal(ai.endpoint({ provider: 'custom', url: 'https://x.vn/v1/chat/completions' }), 'https://x.vn/v1/chat/completions');
});

// fetch giả: trả lần lượt các [status, body] cho từng lần gọi
const fakeFetch = (replies, seen) => async (url, init) => {
  seen.push({ url, init: { ...init, body: JSON.parse(init.body) } });
  const [status, body] = replies.length > 1 ? replies.shift() : replies[0];
  return { ok: status < 300, status, json: async () => body };
};
const toolReply = (args) => ({ choices: [{ message: { content: null, tool_calls: [{ id: 'c1', type: 'function',
  function: { name: 'tao_tieu_chi_loc', arguments: JSON.stringify(args) } }] }, finish_reason: 'tool_calls' }] });

test('gọi Muse / DeepSeek / Gemini / máy chủ khác bằng tool (fetch giả)', async () => {
  let seen = [];
  // Muse: buộc gọi hàm, đọc đối số của tool_calls
  let r = await ai.ask({ provider: 'muse', key: 'vms-1' }, 'giá trên 10k',
    fakeFetch([[200, toolReply({ name: 'x', exchange: 'ALL', filters: [{ column: 'price', operator: '>', value: 10 }], signals: [] })]], seen));
  assert.equal(r.via, 'tool');
  assert.deepEqual(r.crit.filters, { price: { operator: 'gt', value: 10 } });
  const b = seen[0].init.body;
  assert.equal(seen[0].url, 'https://api.botai.id.vn/v1/chat/completions');
  assert.equal(seen[0].init.headers.Authorization, 'Bearer vms-1');
  assert.equal(b.model, 'muse-chat');
  assert.equal(b.tools[0].function.name, 'tao_tieu_chi_loc');
  assert.deepEqual(b.tool_choice, { type: 'function', function: { name: 'tao_tieu_chi_loc' } });
  assert.equal(b.response_format, undefined);
  assert.ok(b.messages[1].content.endsWith('Yêu cầu: giá trên 10k'));

  // DeepSeek từ chối tools (400) → gọi lại kiểu JSON (response_format)
  seen = [];
  r = await ai.ask({ provider: 'deepseek', key: 'sk-1' }, 'x',
    fakeFetch([[400, { error: { message: 'tool_choice not supported' } }], [200, { choices: [{ message: { content: JSON.stringify(EXAMPLE) } }] }]], seen));
  assert.equal(r.via, 'json');
  assert.equal(seen.length, 2);
  assert.ok(seen[0].init.body.tools && !seen[1].init.body.tools);
  assert.deepEqual(seen[1].init.body.response_format, { type: 'json_object' });
  assert.equal(r.crit.filters.price.value, 10);

  // Có trả lời nhưng không gọi hàm (trả chữ JSON) → đọc luôn, khỏi gọi lại
  seen = [];
  r = await ai.ask({ provider: 'custom', url: 'http://localhost:9/v1', model: 'm1' }, 'x',
    fakeFetch([[200, { choices: [{ message: { content: JSON.stringify(EXAMPLE) } }] }]], seen));
  assert.equal(r.via, 'json');
  assert.equal(seen.length, 1);
  assert.equal(seen[0].init.headers.Authorization, undefined);      // máy chủ riêng có thể không cần khoá
  assert.equal(seen[0].init.body.model, 'm1');

  // Gemini: functionDeclarations + mode ANY, đọc functionCall.args
  seen = [];
  r = await ai.ask({ provider: 'gemini', key: 'AIza1' }, 'x', fakeFetch([[200, { candidates: [{ content: { parts: [
    { functionCall: { name: 'tao_tieu_chi_loc', args: { name: 'g', exchange: 'HNX', filters: [{ column: 'price', operator: 'lt', value: 5 }], signals: [] } } }] } }] }]], seen));
  assert.equal(r.via, 'tool');
  assert.deepEqual([r.crit.exchange, r.crit.filters], ['HNX', { price: { operator: 'lt', value: 5 } }]);
  assert.equal(seen[0].init.headers['x-goog-api-key'], 'AIza1');
  assert.ok(!seen[0].url.includes('AIza1'));                       // khoá không nằm trên địa chỉ
  assert.equal(seen[0].init.body.tools[0].functionDeclarations[0].name, 'tao_tieu_chi_loc');
  assert.equal(seen[0].init.body.toolConfig.functionCallingConfig.mode, 'ANY');

  await assert.rejects(ai.ask({ provider: 'muse', key: 'x' }, 'x', fakeFetch([[401, { error: { message: 'bad key' } }]], seen)),
    /Khoá API sai/);
  await assert.rejects(ai.ask({ provider: 'muse', key: 'x' }, 'x', fakeFetch([[402, {}]], seen)), /hết tiền/);
  await assert.rejects(ai.ask({ provider: 'muse', key: 'x' }, 'x', fakeFetch([[200, { choices: [] }]], seen)), /trống/);
  // AI tự đặt mã (như Muse: "MACDCrossUpSignal") → vòng sửa: trả lỗi qua tin nhắn role "tool", AI gọi lại đúng mã
  seen = [];
  r = await ai.ask({ provider: 'muse', key: 'x' }, 'MACD cắt lên', fakeFetch([
    [200, toolReply({ name: 'm', exchange: 'ALL', filters: [], signals: [{ id: 'MACDCrossUpSignal' }] })],
    [200, toolReply({ name: 'm', exchange: 'ALL', filters: [], signals: [{ id: 'MACDCrossAboveSignalLine' }] })]], seen));
  assert.deepEqual([r.via, r.rounds, r.unknown], ['tool', 2, []]);
  assert.deepEqual(r.crit.signals, [{ id: 'MACDCrossAboveSignalLine', params: { tf: 'D' } }]);
  const m2 = seen[1].init.body.messages;
  assert.deepEqual(m2.slice(2).map((x) => x.role), ['assistant', 'tool']);
  assert.equal(m2[2].tool_calls[0].function.name, 'tao_tieu_chi_loc');
  assert.ok(m2[3].content.includes('MACDCrossUpSignal') && m2[3].content.includes('MACDCrossAboveSignalLine'));
  assert.equal(m2[3].tool_call_id, m2[2].tool_calls[0].id);
  // Vòng sửa vẫn sai hơn → giữ kết quả lần đầu
  r = await ai.ask({ provider: 'muse', key: 'x' }, 'x', fakeFetch([
    [200, toolReply({ name: 'a', exchange: 'ALL', filters: [{ column: 'price', operator: 'gt', value: 1 }], signals: [{ id: 'Sai1' }] })],
    [200, toolReply({ name: 'b', exchange: 'ALL', filters: [], signals: [{ id: 'Sai1' }, { id: 'Sai2' }] })]], []));
  assert.deepEqual([r.crit.name, r.unknown, r.rounds], ['a', ['Sai1'], 2]);

  // Không gọi hàm mà trả chữ lạc đề (Muse nhớ hội thoại cũ) → hỏi lại kiểu JSON; vẫn lạc đề thì báo nguyên câu AI trả
  const chat = (t) => [200, { choices: [{ message: { content: t } }] }];
  seen = [];
  r = await ai.ask({ provider: 'muse', key: 'x' }, 'x', fakeFetch([chat('Dạ, em giữ nguyên như vừa trả lời ạ.'), chat(JSON.stringify(EXAMPLE))], seen));
  assert.deepEqual([r.via, seen.length, !!seen[1].init.body.tools], ['json', 2, false]);
  assert.deepEqual(seen[1].init.body.response_format, { type: 'json_object' });
  assert.ok(seen[0].init.body.messages[1].content.includes('Yêu cầu: x'));      // câu hỏi ghi rõ là yêu cầu mới
  await assert.rejects(ai.ask({ provider: 'muse', key: 'x' }, 'x', fakeFetch([chat('Dạ, em không làm được ạ.')], seen)),
    /AI trả lời: "Dạ, em không làm được ạ."/);
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
