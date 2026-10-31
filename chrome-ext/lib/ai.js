// Tạo tiêu chí lọc từ câu tiếng Việt bằng AI (Muse, DeepSeek, Gemini, hoặc máy chủ bất kỳ tương thích OpenAI).
// Khoá API do người dùng nhập, chỉ lưu trong Chrome máy đó và chỉ gửi tới máy chủ AI đã chọn.
// AI được buộc GỌI HÀM tao_tieu_chi_loc (tool / function calling) với khuôn dữ liệu cố định; hãng nào không nhận tools
// thì lùi về trả JSON. AI chỉ được dùng các cột / tín hiệu có trong danh mục; kết quả được kiểm lại từng điều kiện.
import * as core from './core.js';
import * as cond from './conditions.js';

// json: hãng nhận response_format json_object (dùng khi lùi về JSON)
export const PROVIDERS = {
  muse: { name: 'Muse (botai.id.vn)', kind: 'openai', url: 'https://api.botai.id.vn/v1/chat/completions', model: 'muse-chat',
    models: ['muse-chat'], keyHint: 'vms-…', json: true },
  deepseek: { name: 'DeepSeek', kind: 'openai', url: 'https://api.deepseek.com/chat/completions', model: 'deepseek-chat',
    models: ['deepseek-chat'], keyHint: 'sk-…', site: 'https://platform.deepseek.com/api_keys', json: true },
  gemini: { name: 'Google Gemini', kind: 'gemini', model: 'gemini-2.5-flash', models: ['gemini-2.5-flash', 'gemini-2.5-pro'],
    url: 'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent',
    keyHint: 'AIza…', site: 'https://aistudio.google.com/apikey' },
  custom: { name: 'Khác (tương thích OpenAI)', kind: 'openai', url: '', model: '', models: [], keyHint: 'khoá hoặc mã của máy chủ' },
};

const OPS = ['gt', 'lt', 'eq', 'ge', 'le', 'bt'];
// AI hay trả ký hiệu thay cho mã toán tử (Muse trả ">" dù khuôn chỉ cho "gt") → đổi về mã
const OP_ALIAS = { '>': 'gt', '<': 'lt', '=': 'eq', '==': 'eq', '>=': 'ge', '=>': 'ge', '≥': 'ge', '<=': 'le', '=<': 'le', '≤': 'le',
  between: 'bt', range: 'bt', 'trong khoảng': 'bt' };
const EXCHANGES = ['ALL', 'HSX', 'HNX', 'UPCOM'];
const EX_ALIAS = { HOSE: 'HSX', HASTC: 'HNX', UPCOM: 'UPCOM', UPCOMS: 'UPCOM', TATCA: 'ALL', 'CẢ 3 SÀN': 'ALL' };
// Đơn vị của các cột (bảng giá + cột kiểu FireAnt) để AI đổi "10k", "5 tỷ"… cho đúng
const LEGACY_UNIT = { price: 'nghìn đồng', change: 'nghìn đồng', changePercent: '%', volume: 'cổ phiếu', volRatio: '% so với KLTB 45 phiên',
  value: 'tỷ đồng', ma10: 'nghìn đồng', ma20: 'nghìn đồng', ma45: 'nghìn đồng', demandStrength: '%' };
const FMT_UNIT = { pct: '%', upct: '%', pct0: '%', ratio: '% so với trung bình', int: 'phiên', vol: 'cổ phiếu', svol: 'cổ phiếu',
  sbil: 'tỷ đồng', bil: 'tỷ đồng', ago: 'số phiên trước (0 = hôm nay)', price: 'nghìn đồng', num: 'giá trị chỉ báo' };

export function unitOf(key) {
  return LEGACY_UNIT[key] ?? FMT_UNIT[cond.METRIC_FMT[key]] ?? '';
}

const COLUMN_IDS = [...core.FILTERABLE.map(([k]) => k), ...cond.METRIC_KEYS];
const SIGNAL_IDS = cond.SIGNAL_LIST.map((s) => s.id);

// Hàm AI phải gọi. Khuôn dùng mảng (không dùng khoá tự do) để Gemini cũng nhận được; mã cột / mã tín hiệu ghi sẵn
// danh sách hợp lệ (enum) — AI hay tự đặt tên kiểu "MACDCrossUpSignal" nếu chỉ đọc danh mục trong câu lệnh.
export const TOOL = {
  name: 'tao_tieu_chi_loc',
  description: 'Tạo 1 tiêu chí lọc cổ phiếu Việt Nam cho Bee Mini từ yêu cầu của người dùng. '
    + 'Chỉ dùng mã cột / mã tín hiệu có trong danh mục của câu lệnh hệ thống.',
  parameters: {
    type: 'object',
    properties: {
      name: { type: 'string', description: 'Tên ngắn của tiêu chí, tối đa 40 ký tự' },
      exchange: { type: 'string', enum: EXCHANGES, description: 'Sàn; không nói thì ALL' },
      filters: {
        type: 'array', description: 'Điều kiện so một cột với con số',
        items: {
          type: 'object',
          properties: {
            column: { type: 'string', enum: COLUMN_IDS, description: 'Mã cột trong DANH MỤC CỘT' },
            operator: { type: 'string', enum: OPS, description: 'gt >, ge ≥, lt <, le ≤, eq =, bt từ value đến value2' },
            value: { type: 'number', description: 'Số theo đúng đơn vị của cột' },
            value2: { type: 'number', description: 'Chỉ dùng với operator bt' },
          },
          required: ['column', 'operator', 'value'],
        },
      },
      signals: {
        type: 'array', description: 'Tín hiệu (sự kiện / trạng thái) trong DANH MỤC TÍN HIỆU',
        items: {
          type: 'object',
          properties: {
            id: { type: 'string', enum: SIGNAL_IDS, description: 'Mã tín hiệu trong DANH MỤC TÍN HIỆU (đúng từng chữ)' },
            params: {
              type: 'array', description: 'Tham số người dùng nói tới; không nói thì bỏ trống (dùng mặc định)',
              items: { type: 'object', properties: { name: { type: 'string' }, value: { type: 'string', description: 'Giá trị, vd "20", "15m", "có"' } },
                required: ['name', 'value'] },
            },
          },
          required: ['id'],
        },
      },
      unsupported: { type: 'array', items: { type: 'string' }, description: 'Ý trong yêu cầu mà danh mục không có' },
      note: { type: 'string', description: '1 câu tóm tắt cách hiểu' },
    },
    required: ['name', 'exchange', 'filters', 'signals'],
  },
};

function paramSpec(p) {
  const show = (v) => (typeof v === 'string' ? `"${v}"` : String(v));
  return p.free
    ? `${p.id}: số từ ${p.lo} đến ${p.hi} (gợi ý ${p.choices.map(show).join(', ')}; mặc định ${show(p.default)})`
    : `${p.id}: một trong ${p.choices.map(show).join(', ')} (mặc định ${show(p.default)})`;
}

// Câu lệnh hệ thống: luật + toàn bộ danh mục cột / tín hiệu (sinh từ code nên luôn đúng với bản đang chạy)
export function systemPrompt() {
  const cols = [
    ...core.FILTERABLE.map(([k, label]) => `${k} | ${label} (hôm nay) | ${unitOf(k)}`),
    ...cond.METRICS.map(([k, label]) => `${k} | ${label} | ${unitOf(k)}`),
  ];
  const sigs = cond.SIGNAL_LIST.map((s) =>
    `${s.id} | ${cond.signalTitle(s)} | ${s.params.length ? s.params.map(paramSpec).join('; ') : 'không có tham số'}`);
  return `Bạn đổi yêu cầu lọc cổ phiếu Việt Nam (tiếng Việt) thành 1 tiêu chí lọc cho ứng dụng Bee Mini.
Trả kết quả bằng cách GỌI HÀM ${TOOL.name}. Nếu không gọi được hàm thì trả đúng 1 đối tượng JSON cùng dạng, không viết gì khác:
{"name": "tên ngắn", "exchange": "ALL" | "HSX" | "HNX" | "UPCOM",
 "filters": [{"column": "<mã cột>", "operator": "gt" | "lt" | "eq" | "ge" | "le" | "bt", "value": <số>, "value2": <số, chỉ với bt>}],
 "signals": [{"id": "<mã tín hiệu>", "params": [{"name": "<tham số>", "value": "<giá trị>"}]}],
 "unsupported": ["ý mà danh mục không có"], "note": "1 câu tóm tắt cách hiểu"}
Chỉ dùng mã cột / mã tín hiệu có trong danh mục bên dưới.

Luật:
- Mỗi cột chỉ 1 điều kiện. "trên / lớn hơn / >" → gt; "từ / ít nhất / ≥" → ge; "dưới / nhỏ hơn / ít hơn / <" → lt;
  "tối đa / không quá / ≤" → le; "bằng" → eq; "từ a đến b / trong khoảng a–b" → bt (value = a, value2 = b).
- Đơn vị: giá, MA, giá vượt… tính bằng NGHÌN đồng (10k = 10.000đ → 10; 25,5 nghìn → 25.5).
  Khối lượng tính bằng cổ phiếu (100k → 100000; 1,5 triệu → 1500000).
  Giá trị giao dịch, GTTB, mua ròng tính bằng TỶ đồng (500 triệu → 0.5). Cột % dùng số phần trăm (35% → 35).
- Không nói sàn → "ALL" (HOSE = HSX). "Cách đỉnh / cách đáy" không nói kỳ → dùng 1 năm (fromHigh1y / fromLow1y).
- So giá với một đường trung bình (vd "giá trên MA20", "giá dưới EMA50") → dùng tín hiệu PriceAboveSMA / PriceBelowSMA /
  PriceAboveEMA / PriceBelowEMA với tham số period, KHÔNG dùng cột ma10 / ma20 / ma45 (các cột đó là giá trị MA).
- "MA" không nói rõ là SMA. "RSI dưới 30" (giá trị) → cột rsi14; "RSI vừa thoát vùng quá bán" (sự kiện) → tín hiệu.
- Khối lượng hôm nay so với trung bình theo % (vd "KL ≥ 80% TB 50 phiên", "KL gấp 2 lần TB 20") → cột volVs20 / volVs50
  (80% → 80; gấp 2 lần → 200). Không có kỳ 20 / 50 thì chọn kỳ gần nhất.
- "Thanh khoản" không nói rõ: số cổ phiếu → KLTB 20 phiên (avgVol20); số tiền tỷ đồng → GTTB 20 phiên (avgValue20).
- Tham số tín hiệu phải theo đúng lựa chọn cho phép; người dùng không nói thì bỏ tham số đó (dùng mặc định).
- Ý nào danh mục không có (vd vốn hoá, P/E, EPS, lợi nhuận, ngành…) → ghi vào "unsupported", không tự bịa mã.
  Trước khi ghi "unsupported" phải dò lại danh mục: các chỉ báo kỹ thuật dưới đây ĐỀU CÓ.

Gợi ý mã hay dùng: Stochastic cắt lên từ vùng quá bán → StochKCrossAboveDOverSold; Stochastic cắt lên → StochKCrossAboveD;
Parabolic SAR báo tăng / SAR dưới giá → SARUptrend; SAR đảo chiều tăng → SARFlipUp; giá trên mây Ichimoku → IchimokuAboveCloud;
ADX trên 25 / xu hướng mạnh → ADXAboveLevel; +DI cắt lên −DI → DIPlusCrossAboveDIMinus; MACD cắt lên đường tín hiệu →
MACDCrossAboveSignalLine; MACD trên 0 → MACDAboveZeroLine; RSI tạo đáy → RSIBottom; RSI thoát quá bán → RSICrossAboveOverSoldLine;
vượt đỉnh N tháng → AbovePreviousHigh; KL đột biến → EstimatedVolumeSurge hoặc cột volVs20; pullback MA20 → PullbackToSMA;
vượt trendline giảm → BreakDownTrendline; giá cắt lên MA → PriceCrossAboveSMA; MA ngắn cắt lên MA dài → ShortSMACrossAboveLongSMA;
Bollinger thắt chặt → cột bbWidth nhỏ; OBV cắt lên → OBVCrossAboveMA.

DANH MỤC CỘT (dùng trong "filters") — mã | ý nghĩa | đơn vị:
${cols.join('\n')}

DANH MỤC TÍN HIỆU (dùng trong "signals") — mã | ý nghĩa ("…" là chỗ tham số) | tham số:
${sigs.join('\n')}

Ví dụ: "giá trên 10k, KLTB 50 phiên > 100000, cách đỉnh ít hơn 35%, giá trên MA20, sàn HOSE" →
{"name": "Giá >10k, KLTB50 >100k, cách đỉnh <35%", "exchange": "HSX",
 "filters": [{"column": "price", "operator": "gt", "value": 10}, {"column": "avgVol50", "operator": "gt", "value": 100000},
  {"column": "fromHigh1y", "operator": "lt", "value": 35}],
 "signals": [{"id": "PriceAboveSMA", "params": [{"name": "period", "value": "20"}]}], "unsupported": [],
 "note": "Giá > 10 nghìn, KLTB 50 phiên > 100.000 cp, cách đỉnh 1 năm < 35%, giá trên SMA20, sàn HOSE"}`;
}

const isNum = (v) => typeof v === 'number' && Number.isFinite(v);
function toNum(v) {
  if (isNum(v)) return v;
  if (typeof v !== 'string') return null;
  let s = v.trim().replace(/\s+/g, '');
  if (/^\d{1,3}(\.\d{3})+$/.test(s)) s = s.replace(/\./g, '');          // "200.000" kiểu Việt = 200000
  s = s.replace(',', '.');
  return /^[+-]?(\d+\.?\d*|\.\d+)$/.test(s) ? Number(s) : null;
}
const opOf = (op) => (OPS.includes(op) ? op : OP_ALIAS[String(op ?? '').trim().toLowerCase()] ?? null);

// Kết quả AI (chuỗi JSON, hoặc đối số đã đọc của lời gọi hàm) → {crit, issues, unsupported, note}.
// Nhận cả dạng mảng (khuôn hàm) lẫn dạng {cột: {…}} / params {tên: giá trị}. Điều kiện sai thì bỏ, ghi vào issues.
export function parseReply(reply) {
  let obj = reply;
  if (typeof reply !== 'object' || reply === null) {
    const m = String(reply ?? '').match(/\{[\s\S]*\}/);
    if (!m) throw new Error('AI không trả về tiêu chí (không có JSON)');
    try {
      obj = JSON.parse(m[0]);
    } catch {
      throw new Error('AI trả về JSON hỏng');
    }
  }
  const issues = [];
  const unknown = [];                                           // mã cột / mã tín hiệu AI tự đặt (không có trong danh mục)
  const rawFilters = Array.isArray(obj.filters) ? obj.filters
    : Object.entries(obj.filters && typeof obj.filters === 'object' ? obj.filters : {}).map(([column, f]) => ({ column, ...(f || {}) }));
  const filters = {};
  for (const f of rawFilters) {
    const key = f && (f.column ?? f.key ?? f.id);
    if (!(key in core.LABEL)) { issues.push(`không có cột "${key}"`); unknown.push(String(key)); continue; }
    const op = opOf(f.operator), value = toNum(f.value), value2 = toNum(f.value2);
    if (!op || value === null || (op === 'bt' && value2 === null)) {
      issues.push(`bỏ điều kiện sai dạng ở cột ${core.LABEL[key]}`);
      continue;
    }
    filters[key] = op === 'bt' ? { operator: op, value, value2 } : { operator: op, value };
  }
  const signals = [];
  for (const raw of Array.isArray(obj.signals) ? obj.signals : []) {
    const given = {};
    const ps = raw && raw.params;
    for (const [k, v] of Array.isArray(ps) ? ps.map((p) => [p && p.name, p && p.value]) : Object.entries(ps && typeof ps === 'object' ? ps : {})) {
      if (k) given[k] = toNum(v) ?? v;                          // "20" → 20 (tham số chọn là số), "15m" giữ nguyên
    }
    const s = cond.normalizeSignal({ id: raw && raw.id, params: given });
    if (!s) { issues.push(`không có tín hiệu "${raw && raw.id}"`); unknown.push(String(raw && raw.id)); continue; }
    for (const [k, v] of Object.entries(given)) {
      if (k in s.params && String(s.params[k]) !== String(v)) {
        issues.push(`${cond.signalTitle(cond.SIGNALS[s.id])}: "${k}" = ${v} không hợp lệ, dùng ${cond.paramText(s.params[k])}`);
      }
    }
    if (!signals.some((x) => JSON.stringify(x) === JSON.stringify(s))) signals.push(s);
  }
  const name = String(obj.name ?? '').trim().slice(0, 40) || 'Tiêu chí AI';
  const ex = String(obj.exchange ?? '').trim().toUpperCase();
  const crit = { name, exchange: EXCHANGES.includes(ex) ? ex : (EX_ALIAS[ex] || 'ALL'), filters, alert: 'speak' };
  if (signals.length) crit.signals = signals;
  const unsupported = (Array.isArray(obj.unsupported) ? obj.unsupported : []).map(String).filter((x) => x.trim());
  return { crit, issues, unsupported, unknown, note: String(obj.note ?? '') };
}

function errorText(status, data) {
  const msg = (data && (data.error?.message || data.message)) || '';
  if (status === 401 || status === 403) return 'Khoá API sai, hết hạn hoặc không có quyền' + (msg ? ` (${msg})` : '');
  if (status === 402) return 'Tài khoản AI đã hết tiền — nạp thêm ở nơi cấp khoá';
  if (status === 429) return 'Gọi AI quá nhanh hoặc hết hạn mức — thử lại sau ít phút';
  return `Máy chủ AI báo lỗi ${status}` + (msg ? `: ${msg}` : '');
}

// Địa chỉ gọi cho cấu hình {provider, key, model, url}
export function endpoint(cfg) {
  const p = PROVIDERS[cfg.provider] || PROVIDERS.muse;
  const model = String(cfg.model || p.model).trim();
  if (cfg.provider !== 'custom') return p.url.replace('{model}', encodeURIComponent(model));
  const base = String(cfg.url || '').trim().replace(/\/+$/, '');
  return /\/chat\/completions$/.test(base) ? base : base + '/chat/completions';
}

// Câu báo lại cho AI khi nó dùng mã không có trong danh mục (vòng sửa: trả kết quả gọi hàm rồi để AI gọi lại)
export function feedbackOf(unknown) {
  return `LỖI: các mã sau không có trong danh mục: ${unknown.join(', ')}. Chỉ dùng đúng từng chữ các mã dưới đây rồi gọi lại hàm `
    + `${TOOL.name} với ĐẦY ĐỦ yêu cầu.\nMã tín hiệu hợp lệ: ${SIGNAL_IDS.join(', ')}\nMã cột hợp lệ: ${COLUMN_IDS.join(', ')}`;
}

// Thân yêu cầu: useTool = buộc gọi hàm; không thì xin JSON (response_format nếu hãng nhận).
// Câu hỏi ghi rõ là yêu cầu mới, độc lập: máy chủ nhớ hội thoại cũ theo khoá (Muse đang vậy) dễ trả lời lạc đề.
// retry = {got, feedback}: vòng sửa — gửi kèm câu trả lời trước của AI (lời gọi hàm / chữ) và lời báo lỗi.
function requestOf(cfg, question, useTool, retry = null) {
  const p = PROVIDERS[cfg.provider] || PROVIDERS.muse;
  const model = String(cfg.model || p.model).trim();
  const system = systemPrompt();
  const text = `Yêu cầu lọc mới, độc lập — bỏ qua mọi hội thoại trước đó. Hãy gọi hàm ${TOOL.name}.\nYêu cầu: ${question}`;
  if (p.kind === 'gemini') {
    const contents = [{ role: 'user', parts: [{ text }] }];
    if (retry) {
      const [, via, raw] = retry.got;
      contents.push(via === 'tool'
        ? { role: 'model', parts: [{ functionCall: raw }] }
        : { role: 'model', parts: [{ text: String(raw) }] });
      contents.push(via === 'tool'
        ? { role: 'user', parts: [{ functionResponse: { name: TOOL.name, response: { error: retry.feedback } } }] }
        : { role: 'user', parts: [{ text: retry.feedback }] });
    }
    const body = { systemInstruction: { parts: [{ text: system }] }, contents, generationConfig: { temperature: 0 } };
    if (useTool) {
      body.tools = [{ functionDeclarations: [TOOL] }];
      body.toolConfig = { functionCallingConfig: { mode: 'ANY', allowedFunctionNames: [TOOL.name] } };
    } else {
      body.generationConfig.responseMimeType = 'application/json';
    }
    return { headers: { 'Content-Type': 'application/json', 'x-goog-api-key': cfg.key || '' }, body };
  }
  const messages = [{ role: 'system', content: system }, { role: 'user', content: text }];
  if (retry) {
    const [, via, raw] = retry.got;
    if (via === 'tool') {
      const id = raw.id || 'call_1';
      messages.push({ role: 'assistant', content: null, tool_calls: [{ id, type: 'function', function: raw.function }] },
        { role: 'tool', tool_call_id: id, content: retry.feedback });
    } else {
      messages.push({ role: 'assistant', content: String(raw) }, { role: 'user', content: retry.feedback });
    }
  }
  const body = { model, temperature: 0, messages };
  if (useTool) {
    body.tools = [{ type: 'function', function: TOOL }];
    body.tool_choice = { type: 'function', function: { name: TOOL.name } };
  } else if (p.json) {
    body.response_format = { type: 'json_object' };
  }
  return { headers: { 'Content-Type': 'application/json', ...(cfg.key ? { Authorization: `Bearer ${cfg.key}` } : {}) }, body };
}

// Đọc câu trả lời: ưu tiên lời gọi hàm, không có thì đọc chữ (JSON).
// → [đối số / chữ, 'tool' | 'json', nguyên lời gọi hàm / chữ (để gửi lại ở vòng sửa)] hoặc null
function replyOf(kind, data) {
  if (kind === 'gemini') {
    const parts = data?.candidates?.[0]?.content?.parts || [];
    const call = parts.find((x) => x.functionCall && x.functionCall.name === TOOL.name);
    if (call) return [call.functionCall.args || {}, 'tool', call.functionCall];
    const text = parts.map((x) => x.text || '').join('');
    return text ? [text, 'json', text] : null;
  }
  const msg = data?.choices?.[0]?.message || {};
  const call = (msg.tool_calls || []).find((c) => c.function && c.function.name === TOOL.name);
  if (call) {
    const args = call.function.arguments;
    if (typeof args !== 'string') return [args || {}, 'tool', call];
    try {
      return [JSON.parse(args), 'tool', call];
    } catch {
      return [args, 'tool', call];                              // để parseReply báo "JSON hỏng"
    }
  }
  return msg.content ? [msg.content, 'json', msg.content] : null;
}

// Gọi AI với câu `text` → kết quả parseReply + via ('tool' | 'json') + rounds (số lần gọi). Hãng từ chối tools (400 / 422),
// hoặc không gọi hàm mà trả chữ không có JSON → gọi lại 1 lần kiểu JSON. AI dùng mã không có trong danh mục → vòng sửa:
// báo lại mã sai + danh sách mã đúng, AI gọi lại 1 lần; lấy kết quả nào ít mã sai hơn. Lỗi mạng / khoá sai… → ném Error
// có câu tiếng Việt dễ hiểu. Muse mất 15–60 giây mỗi lần (có lúc hơn) → chờ tối đa 3 phút mỗi lần.
export async function ask(cfg, text, fetchFn = fetch, timeoutMs = 180000) {
  const p = PROVIDERS[cfg.provider] || PROVIDERS.muse;
  const url = endpoint(cfg);
  let rounds = 0;
  const post = async (useTool, retry = null) => {
    rounds++;
    const { headers, body } = requestOf(cfg, text, useTool, retry);
    const ctl = new AbortController();
    const timer = setTimeout(() => ctl.abort(), timeoutMs);
    try {
      const res = await fetchFn(url, { method: 'POST', headers, body: JSON.stringify(body), signal: ctl.signal });
      return [res, await res.json().catch(() => null)];
    } catch (e) {
      throw new Error(e.name === 'AbortError' ? `AI trả lời quá lâu (quá ${Math.round(timeoutMs / 1000)} giây) — thử lại`
        : `Không gọi được máy chủ AI (${e.message})`);
    } finally {
      clearTimeout(timer);
    }
  };
  const usable = (g) => !!g && (g[1] === 'tool' || /\{[\s\S]*\}/.test(String(g[0])));
  let [res, data] = await post(true);
  let got = res.ok ? replyOf(p.kind, data) : null;
  if ((!res.ok && (res.status === 400 || res.status === 422)) || (res.ok && !usable(got))) {
    [res, data] = await post(false);                            // không nhận tools / không gọi hàm / trả lạc đề → xin JSON
    got = res.ok ? replyOf(p.kind, data) : null;
  }
  if (!res.ok) throw new Error(errorText(res.status, data));
  if (!got) throw new Error('AI không trả lời (câu trả lời trống)');
  if (!usable(got)) throw new Error(`AI không tạo được tiêu chí. AI trả lời: "${String(got[0]).trim().slice(0, 240)}"`);
  let best = { ...parseReply(got[0]), via: got[1] };
  if (best.unknown.length) {
    try {
      const [res2, data2] = await post(got[1] === 'tool', { got, feedback: feedbackOf(best.unknown) });
      const got2 = res2.ok ? replyOf(p.kind, data2) : null;
      if (usable(got2)) {
        const next = { ...parseReply(got2[0]), via: got2[1] };
        const size = (r) => Object.keys(r.crit.filters).length + (r.crit.signals || []).length;
        if (next.unknown.length < best.unknown.length || (next.unknown.length === best.unknown.length && size(next) > size(best))) {
          best = next;
        }
      }
    } catch { /* vòng sửa hỏng thì giữ kết quả lần đầu */ }
  }
  return { ...best, rounds };
}
