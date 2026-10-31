// Tạo tiêu chí lọc từ câu tiếng Việt bằng AI (DeepSeek, Gemini, hoặc máy chủ bất kỳ tương thích OpenAI).
// Khoá API do người dùng nhập, chỉ lưu trong Chrome máy đó và chỉ gửi tới máy chủ AI đã chọn.
// AI chỉ được dùng các cột / tín hiệu có trong danh mục (gửi kèm câu lệnh); kết quả được kiểm lại từng điều kiện.
import * as core from './core.js';
import * as cond from './conditions.js';

export const PROVIDERS = {
  deepseek: { name: 'DeepSeek', kind: 'openai', url: 'https://api.deepseek.com/chat/completions', model: 'deepseek-chat',
    keyHint: 'sk-…', site: 'https://platform.deepseek.com/api_keys' },
  gemini: { name: 'Google Gemini', kind: 'gemini', model: 'gemini-2.5-flash',
    url: 'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent',
    keyHint: 'AIza…', site: 'https://aistudio.google.com/apikey' },
  custom: { name: 'Khác (tương thích OpenAI)', kind: 'openai', url: '', model: '', keyHint: 'khoá hoặc mã của máy chủ' },
};

const OPS = ['gt', 'lt', 'eq', 'ge', 'le', 'bt'];
const EXCHANGES = ['ALL', 'HSX', 'HNX', 'UPCOM'];
// Đơn vị của các cột (bảng giá + cột kiểu FireAnt) để AI đổi "10k", "5 tỷ"… cho đúng
const LEGACY_UNIT = { price: 'nghìn đồng', change: 'nghìn đồng', changePercent: '%', volume: 'cổ phiếu', volRatio: '% so với KLTB 45 phiên',
  value: 'tỷ đồng', ma10: 'nghìn đồng', ma20: 'nghìn đồng', ma45: 'nghìn đồng', demandStrength: '%' };
const FMT_UNIT = { pct: '%', upct: '%', pct0: '%', int: 'phiên', vol: 'cổ phiếu', svol: 'cổ phiếu', sbil: 'tỷ đồng', bil: 'tỷ đồng',
  ago: 'số phiên trước (0 = hôm nay)', price: 'nghìn đồng', num: 'giá trị chỉ báo' };

export function unitOf(key) {
  return LEGACY_UNIT[key] ?? FMT_UNIT[cond.METRIC_FMT[key]] ?? '';
}

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
  return `Bạn đổi yêu cầu lọc cổ phiếu Việt Nam (tiếng Việt) thành ĐÚNG 1 đối tượng JSON cho ứng dụng Bee Mini.
Chỉ trả JSON, không viết gì khác. Chỉ dùng mã cột / mã tín hiệu có trong danh mục bên dưới.

Mẫu JSON:
{"name": "tên ngắn, tối đa 40 ký tự", "exchange": "ALL" | "HSX" | "HNX" | "UPCOM",
 "filters": {"<mã cột>": {"operator": "gt" | "lt" | "eq" | "ge" | "le" | "bt", "value": <số>, "value2": <số, chỉ dùng với bt>}},
 "signals": [{"id": "<mã tín hiệu>", "params": {"<tham số>": <giá trị>}}],
 "unsupported": ["ý trong yêu cầu mà danh mục không có"],
 "note": "1 câu tóm tắt cách hiểu"}

Luật:
- Mỗi cột chỉ 1 điều kiện. "trên / lớn hơn / >" → gt; "từ / ít nhất / ≥" → ge; "dưới / nhỏ hơn / ít hơn / <" → lt;
  "tối đa / không quá / ≤" → le; "bằng" → eq; "từ a đến b / trong khoảng a–b" → bt (value = a, value2 = b).
- Đơn vị: giá, MA, giá vượt… tính bằng NGHÌN đồng (10k = 10.000đ → 10; 25,5 nghìn → 25.5).
  Khối lượng tính bằng cổ phiếu (100k → 100000; 1,5 triệu → 1500000).
  Giá trị giao dịch, GTTB, mua ròng tính bằng TỶ đồng (500 triệu → 0.5). Cột % dùng số phần trăm (35% → 35).
- Không nói sàn → "ALL". "Cách đỉnh / cách đáy" không nói kỳ → dùng 1 năm (fromHigh1y / fromLow1y).
- So giá với một đường trung bình (vd "giá trên MA20", "giá dưới EMA50") → dùng tín hiệu PriceAboveSMA / PriceBelowSMA /
  PriceAboveEMA / PriceBelowEMA với period, KHÔNG dùng cột ma10 / ma20 / ma45 (các cột đó là giá trị MA, so với một con số).
- "MA" không nói rõ là SMA. "RSI dưới 30" (giá trị) → cột rsi14; "RSI vừa thoát vùng quá bán" (sự kiện) → tín hiệu.
- Tham số tín hiệu phải theo đúng lựa chọn cho phép; người dùng không nói thì bỏ tham số đó (dùng mặc định).
- Ý nào danh mục không có (vd vốn hoá, P/E, EPS, lợi nhuận, ngành…) → ghi vào "unsupported", không tự bịa mã.

DANH MỤC CỘT (dùng trong "filters") — mã | ý nghĩa | đơn vị:
${cols.join('\n')}

DANH MỤC TÍN HIỆU (dùng trong "signals") — mã | ý nghĩa ("…" là chỗ tham số) | tham số:
${sigs.join('\n')}

Ví dụ: "giá trên 10k, KLTB 50 phiên > 100000, cách đỉnh ít hơn 35%, giá trên MA20, sàn HOSE" →
{"name": "Giá >10k, KLTB50 >100k, cách đỉnh <35%", "exchange": "HSX",
 "filters": {"price": {"operator": "gt", "value": 10}, "avgVol50": {"operator": "gt", "value": 100000},
  "fromHigh1y": {"operator": "lt", "value": 35}},
 "signals": [{"id": "PriceAboveSMA", "params": {"period": 20}}], "unsupported": [],
 "note": "Giá > 10 nghìn, KLTB 50 phiên > 100.000 cp, cách đỉnh 1 năm < 35%, giá trên SMA20, sàn HOSE"}`;
}

const isNum = (v) => typeof v === 'number' && Number.isFinite(v);
function toNum(v) {
  if (isNum(v)) return v;
  if (typeof v === 'string' && /^\s*[+-]?(\d+\.?\d*|\.\d+)\s*$/.test(v.replace(',', '.'))) return Number(v.replace(',', '.'));
  return null;
}

// Câu trả lời của AI → {crit, issues, unsupported, note}. Điều kiện không hợp lệ bị bỏ và ghi vào issues.
export function parseReply(text) {
  const m = String(text ?? '').match(/\{[\s\S]*\}/);
  if (!m) throw new Error('AI không trả về JSON');
  let obj;
  try {
    obj = JSON.parse(m[0]);
  } catch {
    throw new Error('AI trả về JSON hỏng');
  }
  const issues = [];
  const filters = {};
  for (const [key, f] of Object.entries(obj.filters && typeof obj.filters === 'object' ? obj.filters : {})) {
    if (!(key in core.LABEL)) { issues.push(`không có cột "${key}"`); continue; }
    const op = f && f.operator, value = toNum(f && f.value), value2 = toNum(f && f.value2);
    if (!OPS.includes(op) || value === null || (op === 'bt' && value2 === null)) {
      issues.push(`bỏ điều kiện sai dạng ở cột ${core.LABEL[key]}`);
      continue;
    }
    filters[key] = op === 'bt' ? { operator: op, value, value2 } : { operator: op, value };
  }
  const signals = [];
  for (const raw of Array.isArray(obj.signals) ? obj.signals : []) {
    const s = cond.normalizeSignal(raw);
    if (!s) { issues.push(`không có tín hiệu "${raw && raw.id}"`); continue; }
    const given = (raw && raw.params) || {};
    for (const [k, v] of Object.entries(given)) {
      if (k in s.params && String(s.params[k]) !== String(v)) {
        issues.push(`${cond.signalTitle(cond.SIGNALS[s.id])}: "${k}" = ${v} không hợp lệ, dùng ${cond.paramText(s.params[k])}`);
      }
    }
    if (!signals.some((x) => JSON.stringify(x) === JSON.stringify(s))) signals.push(s);
  }
  const name = String(obj.name ?? '').trim().slice(0, 40) || 'Tiêu chí AI';
  const crit = { name, exchange: EXCHANGES.includes(obj.exchange) ? obj.exchange : 'ALL', filters, alert: 'speak' };
  if (signals.length) crit.signals = signals;
  const unsupported = (Array.isArray(obj.unsupported) ? obj.unsupported : []).map(String).filter((x) => x.trim());
  return { crit, issues, unsupported, note: String(obj.note ?? '') };
}

function errorText(status, data) {
  const msg = (data && (data.error?.message || data.message)) || '';
  if (status === 401 || status === 403) return 'Khoá API sai, hết hạn hoặc không có quyền' + (msg ? ` (${msg})` : '');
  if (status === 402) return 'Tài khoản AI đã hết tiền — nạp thêm ở trang của hãng AI';
  if (status === 429) return 'Gọi AI quá nhanh hoặc hết hạn mức — thử lại sau ít phút';
  return `Máy chủ AI báo lỗi ${status}` + (msg ? `: ${msg}` : '');
}

// Địa chỉ gọi cho cấu hình {provider, key, model, url}
export function endpoint(cfg) {
  const p = PROVIDERS[cfg.provider] || PROVIDERS.deepseek;
  const model = String(cfg.model || p.model).trim();
  if (cfg.provider !== 'custom') return p.url.replace('{model}', encodeURIComponent(model));
  const base = String(cfg.url || '').trim().replace(/\/+$/, '');
  return /\/chat\/completions$/.test(base) ? base : base + '/chat/completions';
}

// Gọi AI với câu `text` → kết quả parseReply. Lỗi mạng / khoá sai… → ném Error có câu tiếng Việt dễ hiểu.
export async function ask(cfg, text, fetchFn = fetch, timeoutMs = 60000) {
  const p = PROVIDERS[cfg.provider] || PROVIDERS.deepseek;
  const model = String(cfg.model || p.model).trim();
  const url = endpoint(cfg);
  const system = systemPrompt();
  let init;
  if (p.kind === 'gemini') {
    init = { headers: { 'Content-Type': 'application/json', 'x-goog-api-key': cfg.key || '' },
      body: { systemInstruction: { parts: [{ text: system }] }, contents: [{ role: 'user', parts: [{ text }] }],
        generationConfig: { temperature: 0, responseMimeType: 'application/json' } } };
  } else {
    const body = { model, temperature: 0, messages: [{ role: 'system', content: system }, { role: 'user', content: text }] };
    if (cfg.provider !== 'custom') body.response_format = { type: 'json_object' };
    init = { headers: { 'Content-Type': 'application/json', ...(cfg.key ? { Authorization: `Bearer ${cfg.key}` } : {}) }, body };
  }
  const ctl = new AbortController();
  const timer = setTimeout(() => ctl.abort(), timeoutMs);
  let res, data;
  try {
    res = await fetchFn(url, { method: 'POST', headers: init.headers, body: JSON.stringify(init.body), signal: ctl.signal });
    data = await res.json().catch(() => null);
  } catch (e) {
    throw new Error(e.name === 'AbortError' ? 'AI trả lời quá lâu (quá 60 giây) — thử lại' : `Không gọi được máy chủ AI (${e.message})`);
  } finally {
    clearTimeout(timer);
  }
  if (!res.ok) throw new Error(errorText(res.status, data));
  const reply = p.kind === 'gemini'
    ? (data?.candidates?.[0]?.content?.parts || []).map((x) => x.text || '').join('')
    : data?.choices?.[0]?.message?.content;
  if (!reply) throw new Error('AI không trả lời (câu trả lời trống)');
  return parseReply(reply);
}
