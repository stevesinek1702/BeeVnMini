// Cài đặt bộ lọc (trong tab của extension). Mỗi tiêu chí một thẻ; điều kiện là danh sách sửa ngay tại chỗ (tham số nằm
// trong câu); thêm điều kiện bằng ô tìm / nhóm, từ tiêu chí mẫu, hoặc tả bằng lời cho AI. Mọi thay đổi nằm trên bản nháp,
// bấm "Lưu & áp dụng" mới lên bảng giá.
import * as core from './lib/core.js';
import * as cond from './lib/conditions.js';
import * as ai from './lib/ai.js';
import { SYMBOLS } from './lib/symbols.js';

const SYMBOL_SET = new Set(SYMBOLS);
const EXCHANGES = [['HSX', 'HSX'], ['HNX', 'HNX'], ['UPCOM', 'UpCom'], ['ALL', 'Cả 3 sàn']];
const ALERTS = [['speak', '🔊 Đọc tên mã'], ['beep', '🔔 Kêu "ting"'], ['off', '🔕 Im lặng']];
const OPS = [['gt', '>'], ['ge', '≥'], ['lt', '<'], ['le', '≤'], ['eq', '='], ['bt', 'từ … đến']];
const SORT_COLUMNS = [...core.COLUMNS, ...cond.METRIC_KEYS.map((k) => [k, cond.METRIC_LABEL[k]])];
const BOARD_GROUP = ['board', 'Cột bảng giá'];
const GROUP_NAME = Object.fromEntries([BOARD_GROUP, ...cond.GROUPS]);

const el = (tag, attrs = {}, ...kids) => {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === 'class') e.className = v;
    else if (k.startsWith('on')) e[k] = v;
    else if (v !== undefined && v !== null && v !== false) e.setAttribute(k, v === true ? '' : v);
  }
  for (const kid of kids.flat(Infinity)) if (kid !== null && kid !== undefined && kid !== false) e.append(kid);
  return e;
};
// JSON khoá xếp theo thứ tự — so bản nháp với cài đặt đang dùng mà không lệ thuộc thứ tự khoá
const stable = (v) => (Array.isArray(v) ? `[${v.map(stable).join(',')}]`
  : v && typeof v === 'object' ? `{${Object.keys(v).sort().map((k) => JSON.stringify(k) + ':' + stable(v[k])).join(',')}}`
    : JSON.stringify(v ?? null));
const toNum = (raw) => {
  const s = String(raw ?? '').trim().replace(',', '.');
  if (!s || !/^[+-]?(\d+\.?\d*|\.\d+)(e[+-]?\d+)?$/i.test(s)) return null;
  return Number(s);
};
// Bỏ dấu tiếng Việt để tìm "cach dinh" ra "cách đỉnh"
const fold = (s) => s.normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/đ/g, 'd').replace(/Đ/g, 'D').toLowerCase();
const segmented = (pairs, value, onPick, cls = '') => el('div', { class: 'seg ' + cls },
  pairs.map(([v, t]) => el('button', { type: 'button', class: v === value ? 'on' : '', onclick: () => onPick(v) }, t)));

// Mọi điều kiện chọn được: cột bảng giá, cột số kiểu FireAnt, tín hiệu — [nhóm, tên, 'filter' | 'signal', khoá, chữ để tìm]
function allConditions() {
  const out = core.FILTERABLE.map(([k, label]) => ['board', label, 'filter', k]);
  for (const [k, label, , group] of cond.METRICS) out.push([group, label, 'filter', k]);
  for (const s of cond.SIGNAL_LIST) out.push([s.group, cond.signalTitle(s), 'signal', s.id]);
  return out.map((x) => [...x, fold(`${x[1]} ${GROUP_NAME[x[0]]} ${x[3]}`)]);
}

export class Settings {
  constructor(host, app) {
    this.app = app;
    this.host = host;
    this.items = allConditions();
    this.group = '';
    this.build();
    this.load();
    this.loadAi();
  }

  build() {
    const h = this.host;
    h.replaceChildren();
    const $ = (sel) => h.querySelector(sel);
    h.append(
      el('div', { class: 'st-title' }, el('h2', {}, '⚙ Bộ lọc'),
        el('span', { class: 'hint' }, 'Mỗi tiêu chí là một khối trên bảng giá; mã phải thoả tất cả điều kiện của tiêu chí.')),
      el('div', { class: 'card ai' },
        el('h3', {}, '✨ Tạo tiêu chí bằng AI'),
        el('p', { class: 'hint' }, 'Gõ tiêu chí như nói chuyện, AI sẽ dựng bộ lọc. Vd: ',
          el('i', {}, 'giá trên 10k, KLTB 50 phiên > 100 nghìn, cách đỉnh 1 năm dưới 35%, giá trên MA20, RSI dưới 60')),
        el('textarea', { id: 'ai-text', rows: 2, spellcheck: 'false', placeholder: 'Mô tả tiêu chí lọc… (Ctrl + Enter để tạo)' }),
        el('div', { class: 'row' },
          el('button', { class: 'main', id: 'ai-go', type: 'button' }, '✨ Tạo tiêu chí'),
          el('span', { class: 'hint', id: 'ai-status' })),
        el('div', { id: 'ai-out' })),
      el('div', { class: 'tabs', id: 's-tabs' }),
      el('div', { class: 'card', id: 's-card' }),
      el('details', { class: 'card', id: 's-watch-card' },
        el('summary', {}, '★ Danh mục theo dõi'),
        el('p', { class: 'hint' }, 'Gõ mã cách nhau bằng dấu cách (vd VIB MBB HPG) → khối riêng cuối bảng giá. ',
          'Hoặc chuột phải lên một mã trên bảng giá → ★ Theo dõi.'),
        el('input', { id: 's-watch', class: 'wide', placeholder: 'VIB MBB HPG' })),
      el('details', { class: 'card', id: 's-ai-card' },
        el('summary', {}, '🤖 Cài đặt AI', el('span', { class: 'hint', id: 'ai-state' })),
        el('div', { class: 'form' },
          el('label', {}, 'Hãng AI'), el('select', { id: 'ai-provider' },
            Object.entries(ai.PROVIDERS).map(([k, p]) => el('option', { value: k }, p.name))),
          el('label', { id: 'ai-url-l' }, 'Địa chỉ API'), el('input', { id: 'ai-url', placeholder: 'https://…/v1' }),
          el('label', {}, 'Khoá API'), el('div', { class: 'row tight' },
            el('input', { id: 'ai-key', type: 'password', autocomplete: 'off', spellcheck: 'false' }),
            el('button', { type: 'button', class: 'ghost', id: 'ai-show' }, '👁')),
          el('label', {}, 'Model'), el('input', { id: 'ai-model' })),
        el('p', { class: 'hint', id: 'ai-help' })),
      el('details', { class: 'card' },
        el('summary', {}, '⇪ Chép cài đặt từ app Bee.vn mini (Windows)'),
        el('p', { class: 'hint' }, 'Chọn file ', el('code', {}, '%APPDATA%\\BeeVnMini\\config.json'),
          ' (dán đường dẫn đó vào ô chọn file) → lấy các tiêu chí + danh mục theo dõi sang đây, rồi bấm Lưu.'),
        el('input', { type: 'file', id: 's-import', accept: '.json,application/json' })),
      el('p', { class: 'hint', id: 's-voice' }),
      el('div', { class: 'savebar' },
        el('span', { id: 's-dirty' }),
        el('button', { type: 'button', class: 'ghost', id: 's-revert' }, 'Huỷ thay đổi'),
        el('button', { type: 'button', class: 'main', id: 's-save' }, 'Lưu & áp dụng')),
    );
    Object.assign(this, {
      tabs: $('#s-tabs'), card: $('#s-card'), watch: $('#s-watch'), voice: $('#s-voice'), dirty: $('#s-dirty'),
      aiText: $('#ai-text'), aiGo: $('#ai-go'), aiStatus: $('#ai-status'), aiOut: $('#ai-out'),
    });
    $('#s-save').onclick = () => this.save();
    $('#s-revert').onclick = () => { this.load(); };
    $('#s-import').onchange = (e) => this.importConfig(e.target.files[0]);
    this.watch.oninput = () => this.markDirty();
    this.aiGo.onclick = () => this.runAi();
    this.aiText.onkeydown = (e) => { if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) this.runAi(); };
    for (const id of ['ai-provider', 'ai-url', 'ai-key', 'ai-model']) {
      $('#' + id).addEventListener(id === 'ai-provider' ? 'change' : 'input', () => this.storeAi(id === 'ai-provider'));
    }
    $('#ai-show').onclick = () => { const k = $('#ai-key'); k.type = k.type === 'password' ? 'text' : 'password'; };
    document.addEventListener('click', (e) => { if (this.menu && !this.menu.contains(e.target)) this.closeMenu(); });
  }

  showVoice(name) {
    this.voice.textContent = name ? `Giọng đọc: ${name}` :
      'Máy chưa có giọng tiếng Việt cho Chrome — sẽ đọc tiếng Anh. Cài thêm: Settings → Time & language → Speech → Add voices → Tiếng Việt.';
  }

  // Bản nháp từ cài đặt đang dùng
  load() {
    this.crits = structuredClone(this.app.cfg.criteria);
    this.cur = Math.max(0, Math.min(this.cur || 0, this.crits.length - 1));
    this.loadWatch();
    this.render();
  }

  loadWatch() {
    this.watch.value = this.app.cfg.watch.join(' ');
    this.markDirty();
  }

  get crit() {
    return this.crits[this.cur];
  }

  // ── Vẽ ──
  render() {
    this.renderTabs();
    this.renderCard();
    this.markDirty();
  }

  renderTabs() {
    const n = (c) => Object.keys(c.filters || {}).length + (c.signals || []).length;
    this.tabs.replaceChildren(
      ...this.crits.map((c, i) => el('button', { type: 'button', class: 'tab' + (i === this.cur ? ' on' : ''),
        title: core.describeFilters(c.filters || {}, c.signals) || 'chưa có điều kiện',
        onclick: () => { this.cur = i; this.render(); } }, c.name || `Tiêu chí ${i + 1}`, el('span', { class: 'badge' }, String(n(c))))),
      el('button', { type: 'button', class: 'tab add', onclick: () => this.addCriterion() }, '＋ Tiêu chí'),
      el('button', { type: 'button', class: 'tab add', onclick: (e) => this.showTemplates(e) }, '📋 Mẫu'),
    );
  }

  renderCard() {
    const c = this.crit;
    const set = (k, v) => { c[k] = v; this.renderCard(); this.renderTabs(); this.markDirty(); };
    const sortSel = el('select', { onchange: (e) => { c.sortColumn = e.target.value; this.markDirty(); } },
      SORT_COLUMNS.map(([k, t]) => el('option', { value: k }, t)));
    sortSel.value = SORT_COLUMNS.some(([k]) => k === c.sortColumn) ? c.sortColumn : 'value';
    const name = el('input', { class: 'name', value: c.name, placeholder: 'Tên tiêu chí', maxlength: 60 });
    name.oninput = () => { c.name = name.value; this.renderTabs(); this.markDirty(); };
    name.onblur = () => { if (!name.value.trim()) { c.name = `Tiêu chí ${this.cur + 1}`; name.value = c.name; this.renderTabs(); } };
    this.search = el('input', { type: 'search', class: 'search', placeholder: '🔍 Tìm điều kiện để thêm: rsi, ma20, kltb, cách đỉnh, sar, mây…' });
    this.search.oninput = () => this.renderResults();
    this.results = el('div', { class: 'results' });
    this.chips = el('div', { class: 'chips' });
    this.card.replaceChildren(
      el('div', { class: 'card-head' }, name,
        el('button', { type: 'button', class: 'ghost danger', onclick: () => this.deleteCriterion() }, '🗑 Xoá tiêu chí')),
      el('div', { class: 'fields' },
        el('label', {}, 'Sàn'), segmented(EXCHANGES, c.exchange || 'HSX', (v) => set('exchange', v)),
        el('label', {}, 'Khi có mã mới'), el('div', { class: 'row tight' },
          segmented(ALERTS, c.alert || 'speak', (v) => set('alert', v)),
          el('button', { type: 'button', class: 'ghost', onclick: () => this.testAlert() }, '▶ Nghe thử')),
        el('label', {}, 'Sắp xếp theo'), el('div', { class: 'row tight' }, sortSel,
          segmented([['desc', '▼ Lớn → nhỏ'], ['asc', '▲ Nhỏ → lớn']], c.sortDirection === 'asc' ? 'asc' : 'desc',
            (v) => set('sortDirection', v), 'small'))),
      el('h3', {}, 'Điều kiện ', el('span', { class: 'hint' }, '— sửa số / tham số ngay trong dòng, ✕ để bỏ')),
      this.condList = el('div', { class: 'conds' }),
      el('div', { class: 'picker' }, this.search, this.chips, this.results),
    );
    this.renderConds();
    this.renderChips();
    this.renderResults();
  }

  renderConds() {
    const c = this.crit;
    const rows = [
      ...Object.keys(c.filters || {}).map((k) => this.filterRow(c, k)),
      ...(c.signals || []).map((s, i) => this.signalRow(c, s, i)),
    ];
    this.condList.replaceChildren(...(rows.length ? rows
      : [el('div', { class: 'empty' }, 'Chưa có điều kiện. Tìm ở ô bên dưới, chọn 📋 Mẫu, hoặc nhờ ✨ AI tạo giúp.')]));
  }

  filterRow(c, key) {
    const f = c.filters[key];
    const op = el('select', { class: 'op' }, OPS.map(([v, t]) => el('option', { value: v }, t)));
    op.value = OPS.some(([v]) => v === f.operator) ? f.operator : 'ge';
    const num = (field) => {
      const inp = el('input', { class: 'num', inputmode: 'decimal', placeholder: 'số',
        value: f[field] === undefined || f[field] === null ? '' : String(f[field]) });
      inp.oninput = () => {
        const v = toNum(inp.value);
        inp.classList.toggle('bad', v === null);
        f[field] = v === null ? inp.value : v;
        this.markDirty();
      };
      inp.classList.toggle('bad', inp.value !== '' && toNum(inp.value) === null);
      return inp;
    };
    const v1 = num('value'), v2 = num('value2');
    const to = el('span', { class: 'hint' }, 'đến');
    const toggle = () => { to.hidden = v2.hidden = op.value !== 'bt'; };
    op.onchange = () => { f.operator = op.value; if (op.value !== 'bt') delete f.value2; toggle(); this.markDirty(); };
    toggle();
    const row = el('div', { class: 'cond', 'data-key': key },
      el('span', { class: 'text' }, core.LABEL[key] ?? key), op, v1, to, v2, el('span', { class: 'unit' }, ai.unitOf(key)),
      el('button', { type: 'button', class: 'x', title: 'Bỏ điều kiện này', onclick: () => {
        delete c.filters[key]; this.renderConds(); this.renderTabs(); this.markDirty(); } }, '✕'));
    row.focusValue = () => v1.focus();
    return row;
  }

  // Câu tín hiệu với ô tham số đặt đúng chỗ {tham số} trong câu
  signalRow(c, s, i) {
    const spec = cond.SIGNALS[s.id];
    const control = (p) => {
      if (!p.free) {
        const sel = el('select', {}, p.choices.map((v, j) => el('option', { value: j }, cond.paramText(v))));
        sel.value = String(p.choices.findIndex((v) => v === s.params[p.id]));
        sel.onchange = () => this.setParam(c, i, p, p.choices[Number(sel.value)], sel);
        return sel;
      }
      const id = `dl-${s.id}-${p.id}`;
      const inp = el('input', { class: 'num', list: id, inputmode: 'decimal', value: cond.paramText(s.params[p.id]) });
      inp.oninput = () => {
        const v = toNum(inp.value);
        const ok = v !== null && p.lo <= v && v <= p.hi;
        inp.classList.toggle('bad', !ok);
        inp.title = ok ? '' : `Số từ ${p.lo} đến ${p.hi}`;
        if (ok) this.setParam(c, i, p, v, inp);
      };
      return [inp, el('datalist', { id }, p.choices.map((v) => el('option', { value: cond.paramText(v) })))];
    };
    const used = new Set();
    const parts = spec.label.split(/(\{\w+\})/).map((part) => {
      const m = part.match(/^\{(\w+)\}$/);
      const p = m && spec.params.find((x) => x.id === m[1]);
      if (!p) return part;
      used.add(p.id);
      return control(p);
    });
    for (const p of spec.params) if (!used.has(p.id)) parts.push(` · ${p.name} `, control(p));
    return el('div', { class: 'cond sig', 'data-sig': s.id },
      el('span', { class: 'text' }, parts),
      el('button', { type: 'button', class: 'x', title: 'Bỏ điều kiện này', onclick: () => {
        c.signals.splice(i, 1);
        if (!c.signals.length) delete c.signals;
        this.renderConds(); this.renderTabs(); this.markDirty();
      } }, '✕'));
  }

  setParam(c, i, p, v, widget) {
    const s = c.signals[i];
    const next = cond.normalizeSignal({ id: s.id, params: { ...s.params, [p.id]: v } });
    if (String(next.params[p.id]) !== String(v)) {       // vd SMA ngắn ≥ SMA dài
      widget.classList.add('bad');
      widget.title = 'Đường ngắn phải ngắn hơn đường dài';
      return;
    }
    widget.classList.remove('bad');
    widget.title = '';
    c.signals[i] = next;
    this.renderTabs();
    this.markDirty();
  }

  renderChips() {
    const groups = [['', 'Tất cả'], BOARD_GROUP, ...cond.GROUPS];
    this.chips.replaceChildren(...groups.map(([g, t]) => el('button', { type: 'button', class: 'chip' + (g === this.group ? ' on' : ''),
      onclick: () => { this.group = g; this.renderChips(); this.renderResults(); } }, t)));
  }

  renderResults() {
    const words = fold(this.search.value).split(/\s+/).filter(Boolean);
    const hits = this.items.filter(([g, , , , text]) => (!this.group || g === this.group) && words.every((w) => text.includes(w)));
    const c = this.crit;
    this.results.replaceChildren(...(hits.length ? hits.map(([g, title, kind, key]) => {
      const added = kind === 'filter' ? key in (c.filters || {}) : false;
      return el('button', { type: 'button', class: 'res' + (added ? ' added' : ''), onclick: () => this.addCondition(kind, key) },
        el('span', { class: 'grp' }, GROUP_NAME[g]), el('span', {}, title), added ? el('span', { class: 'hint' }, ' ✓ đã có') : null);
    }) : [el('div', { class: 'empty' }, 'Không có điều kiện nào khớp — thử từ khác, hoặc nhờ ✨ AI.')]));
  }

  addCondition(kind, key) {
    const c = this.crit;
    if (kind === 'filter') {
      c.filters ||= {};
      if (!(key in c.filters)) {
        c.filters[key] = { operator: core.LEGACY_KEYS.has(key) ? 'gt' : (cond.METRIC_FMT[key] === 'ago' ? 'le' : 'ge'), value: '' };
      }
    } else {
      const s = cond.normalizeSignal({ id: key });
      c.signals ||= [];
      if (!c.signals.some((x) => JSON.stringify(x) === JSON.stringify(s))) c.signals.push(s);
    }
    this.renderConds();
    this.renderTabs();
    this.renderResults();
    this.markDirty();
    const row = kind === 'filter' ? this.condList.querySelector(`[data-key="${key}"]`)
      : [...this.condList.querySelectorAll(`[data-sig="${key}"]`)].pop();
    if (row) {
      row.classList.add('flash');
      row.scrollIntoView({ block: 'nearest' });
      if (row.focusValue) row.focusValue();
    }
  }

  // ── Tiêu chí ──
  uniqueName(base) {
    const names = new Set(this.crits.map((c) => c.name));
    if (!names.has(base)) return base;
    for (let i = 2; ; i++) if (!names.has(`${base} (${i})`)) return `${base} (${i})`;
  }

  addCriterion(from = null) {
    const c = this.crit;
    const next = from ? { ...structuredClone(from), name: this.uniqueName(from.name) }
      : { name: this.uniqueName(`Tiêu chí ${this.crits.length + 1}`), exchange: c.exchange || 'HSX', filters: {} };
    next.alert ||= c.alert || 'speak';
    next.sortColumn ||= c.sortColumn || 'value';
    next.sortDirection ||= c.sortDirection || 'desc';
    this.crits.push(next);
    this.cur = this.crits.length - 1;
    this.render();
    if (!from) this.card.querySelector('.name').select();
  }

  deleteCriterion() {
    if (this.crits.length === 1) {
      alert('Phải còn ít nhất 1 tiêu chí. Muốn tắt lọc thì bỏ hết điều kiện.');
      return;
    }
    if (!confirm(`Xoá tiêu chí "${this.crit.name}"?`)) return;
    this.crits.splice(this.cur, 1);
    this.cur = Math.max(0, this.cur - 1);
    this.render();
  }

  showTemplates(e) {
    e.stopPropagation();
    this.closeMenu();
    const m = el('div', { class: 'menu' },
      el('div', { class: 'menu-head' }, 'Tiêu chí mẫu — bấm để thêm, sửa tiếp được'),
      core.TEMPLATES.map((t) => el('button', { type: 'button', onclick: () => {
        this.closeMenu();
        const { desc, ...crit } = t;
        this.addCriterion(crit);
      } }, el('b', {}, t.name), el('span', { class: 'hint' }, t.desc))));
    const r = e.currentTarget.getBoundingClientRect(), box = this.host.getBoundingClientRect();
    m.style.left = Math.max(0, r.left - box.left) + 'px';
    m.style.top = r.bottom - box.top + 4 + 'px';
    this.host.append(m);
    this.menu = m;
  }

  closeMenu() {
    if (this.menu) { this.menu.remove(); this.menu = null; }
  }

  testAlert() {
    const c = this.crit;
    const sec = this.app.sections.find(([x]) => x.name === c.name);
    const syms = sec ? sec[1].slice(0, 2).map((s) => s.symbol) : [];
    if ((c.alert || 'speak') === 'off') {
      alert(`Tiêu chí "${c.name}" đang để Im lặng: có mã mới chỉ sáng vàng, không kêu.`);
      return;
    }
    this.app.alert([[c.name, syms.length ? syms : ['VIB', 'MBB'], c.alert || 'speak']], this.crits.length > 1);
  }

  // ── Lưu ──
  // Bản nháp đã chuẩn hoá (số là số) hoặc danh sách ô còn trống / sai
  collect() {
    const bad = [];
    const crits = this.crits.map((c, i) => {
      const filters = {};
      for (const [k, f] of Object.entries(c.filters || {})) {
        const value = toNum(f.value), value2 = toNum(f.value2);
        if (value === null || (f.operator === 'bt' && value2 === null)) { bad.push(`${c.name}: ${core.LABEL[k] ?? k}`); continue; }
        filters[k] = f.operator === 'bt' ? { operator: 'bt', value, value2 } : { operator: f.operator, value };
      }
      const out = { name: String(c.name || '').trim() || `Tiêu chí ${i + 1}`, exchange: c.exchange || 'HSX', filters,
        alert: c.alert || 'speak', sortColumn: c.sortColumn || 'value', sortDirection: c.sortDirection || 'desc' };
      if (c.signals && c.signals.length) out.signals = c.signals;
      return out;
    });
    if (this.host.querySelector('.conds .bad')) bad.push(`${this.crit.name}: tham số chưa hợp lệ (ô đỏ)`);
    return { crits, bad };
  }

  markDirty() {
    if (!this.crits) return;
    const { crits } = this.collect();
    const norm = (cs) => stable(core.criteriaFromConfig({ criteria: cs }));
    const changed = norm(crits) !== norm(this.app.cfg.criteria)
      || core.parseSymbols(this.watch.value).join(' ') !== this.app.cfg.watch.join(' ');
    this.dirty.textContent = changed ? '● Có thay đổi chưa lưu' : '';
    this.host.classList.toggle('is-dirty', changed);
  }

  save() {
    const { crits, bad } = this.collect();
    if (bad.length) {
      alert('Còn ô chưa điền số / sai:\n• ' + bad.join('\n• '));
      return;
    }
    const watch = core.parseSymbols(this.watch.value);
    const unknown = watch.filter((s) => !SYMBOL_SET.has(s));
    if (unknown.length) {
      alert('Không có mã: ' + unknown.join(', ') + '\nKiểm tra lại ô ★ Theo dõi.');
      return;
    }
    const cur = this.cur;
    this.app.applySettings({ criteria: crits, watch });       // app gọi lại load() → vẽ lại bản nháp mới
    this.cur = cur;
    this.render();
    this.dirty.textContent = '✓ Đã lưu';
    setTimeout(() => this.markDirty(), 1500);
  }

  async importConfig(file) {
    if (!file) return;
    try {
      const cfg = JSON.parse(await file.text());
      this.crits = structuredClone(core.criteriaFromConfig(cfg));
      this.cur = 0;
      if (cfg.watch) this.watch.value = core.parseSymbols(cfg.watch).join(' ');
      this.render();
      alert(`Đã chép ${this.crits.length} tiêu chí` + (cfg.watch && cfg.watch.length ? ` và ${cfg.watch.length} mã theo dõi` : '') +
        '. Bấm "Lưu & áp dụng" để dùng.');
    } catch (e) {
      alert('Không đọc được file cài đặt: ' + e.message);
    }
  }

  // ── AI ──
  async loadAi() {
    const { ai: saved } = await chrome.storage.local.get('ai');
    this.aiCfg = { provider: 'deepseek', key: '', model: '', url: '', ...(saved || {}) };
    const $ = (id) => this.host.querySelector('#' + id);
    $('ai-provider').value = ai.PROVIDERS[this.aiCfg.provider] ? this.aiCfg.provider : 'deepseek';
    $('ai-key').value = this.aiCfg.key;
    $('ai-model').value = this.aiCfg.model;
    $('ai-url').value = this.aiCfg.url;
    this.showAiHelp();
  }

  showAiHelp() {
    const $ = (id) => this.host.querySelector('#' + id);
    const p = ai.PROVIDERS[this.aiCfg.provider] || ai.PROVIDERS.deepseek;
    const custom = this.aiCfg.provider === 'custom';
    $('ai-url').hidden = $('ai-url-l').hidden = !custom;
    $('ai-model').placeholder = p.model || 'tên model';
    $('ai-key').placeholder = p.keyHint;
    $('ai-help').replaceChildren(...(custom
      ? ['Máy chủ nhận kiểu gọi /chat/completions như OpenAI (vd Muse, OpenRouter, Groq… hoặc web riêng của anh).']
      : ['Lấy khoá ở ', el('a', { href: p.site, target: '_blank', rel: 'noreferrer' }, p.site.replace(/^https:\/\//, '')),
        '. Khoá chỉ lưu trong Chrome máy này, chỉ gửi tới máy chủ của ', p.name, '.']));
    $('ai-state').textContent = this.aiReady() ? `  — ${p.name}` : '  — chưa có khoá';
  }

  aiReady() {
    const c = this.aiCfg || {};
    return c.provider === 'custom' ? !!String(c.url || '').trim() : !!String(c.key || '').trim();
  }

  async storeAi(providerChanged) {
    const $ = (id) => this.host.querySelector('#' + id);
    this.aiCfg = { provider: $('ai-provider').value, key: $('ai-key').value.trim(), model: $('ai-model').value.trim(),
      url: $('ai-url').value.trim() };
    if (providerChanged) { this.aiCfg.model = ''; $('ai-model').value = ''; }
    this.showAiHelp();
    await chrome.storage.local.set({ ai: this.aiCfg });
  }

  async runAi() {
    const text = this.aiText.value.trim();
    if (!text) { this.aiText.focus(); return; }
    if (!this.aiReady()) {
      this.host.querySelector('#s-ai-card').open = true;
      this.host.querySelector(this.aiCfg.provider === 'custom' ? '#ai-url' : '#ai-key').focus();
      this.aiStatus.textContent = 'Nhập khoá API ở "🤖 Cài đặt AI" trước.';
      return;
    }
    // Quyền gọi máy chủ AI: Chrome hỏi 1 lần cho mỗi địa chỉ (đang trong cú bấm nên được phép hỏi)
    let origin;
    try {
      const u = new URL(ai.endpoint(this.aiCfg));
      origin = `${u.protocol}//${u.hostname}/*`;
    } catch {
      this.aiStatus.textContent = 'Địa chỉ API không hợp lệ.';
      return;
    }
    if (!(await chrome.permissions.request({ origins: [origin] }))) {
      this.aiStatus.textContent = 'Chưa cho phép gọi máy chủ AI — bấm lại và chọn Cho phép (Allow).';
      return;
    }
    this.aiGo.disabled = true;
    this.aiStatus.textContent = '⏳ AI đang dựng tiêu chí…';
    this.aiOut.replaceChildren();
    try {
      const r = await ai.ask(this.aiCfg, text);
      this.aiStatus.textContent = '';
      this.showAiResult(r);
    } catch (e) {
      this.aiStatus.textContent = '⚠ ' + e.message;
    } finally {
      this.aiGo.disabled = false;
    }
  }

  showAiResult(r) {
    const c = r.crit;
    const lines = [...core.activeFilterKeys(c.filters).map((k) => core.describeFilters({ [k]: c.filters[k] })),
      ...(c.signals || []).map(cond.describeSignal)];
    const warn = [...r.unsupported.map((x) => `Chưa lọc được: ${x}`), ...r.issues];
    this.aiOut.replaceChildren(el('div', { class: 'ai-result' },
      el('div', {}, el('b', {}, c.name), el('span', { class: 'hint' }, ` · ${EXCHANGES.find(([k]) => k === c.exchange)[1]}`)),
      r.note ? el('div', { class: 'hint' }, r.note) : null,
      lines.length ? el('ul', {}, lines.map((t) => el('li', {}, t))) : el('div', { class: 'empty' }, 'AI không tạo được điều kiện nào.'),
      warn.length ? el('ul', { class: 'warn' }, warn.map((t) => el('li', {}, t))) : null,
      lines.length ? el('div', { class: 'row' },
        el('button', { type: 'button', class: 'main', onclick: () => { this.addCriterion(c); this.aiOut.replaceChildren(); this.save(); } },
          '＋ Thêm & áp dụng'),
        el('button', { type: 'button', class: 'ghost', onclick: () => { this.addCriterion(c); this.aiOut.replaceChildren(); } },
          'Thêm để sửa tiếp')) : null));
  }
}
