// Cài đặt bộ lọc — chép SettingsWindow của beevn_mini.pyw sang HTML (nằm trong tab của extension).
// Sửa trên bản nháp các tiêu chí; bấm Lưu mới áp dụng lên bảng giá.
import * as core from './lib/core.js';
import * as cond from './lib/conditions.js';
import { SYMBOLS } from './lib/symbols.js';

const SYMBOL_SET = new Set(SYMBOLS);
const EXCHANGE_LABEL = { HSX: 'HSX', HNX: 'HNX', UPCOM: 'UpCom', ALL: 'Cả 3 sàn' };
const ALERT_LABEL = [['speak', 'Đọc tên mã'], ['beep', 'Kêu "ting"'], ['off', 'Im lặng']];
const OP_LABEL = [['gt', 'Lớn hơn (>)'], ['lt', 'Nhỏ hơn (<)'], ['eq', 'Bằng (=)']];
const METRIC_OP_LABEL = [['ge', 'Từ (≥)'], ['le', 'Đến (≤)'], ['bt', 'Trong khoảng']];
const METRIC_UNIT = { pct: '%', pct0: '%', int: 'phiên', vol: 'cổ phiếu', svol: 'cổ phiếu', sbil: 'tỷ đồng',
  ago: 'phiên trước (0 = hôm nay)', price: 'nghìn đồng' };
const SORT_COLUMNS = [...core.COLUMNS, ...cond.METRIC_KEYS.map((k) => [k, cond.METRIC_LABEL[k]])];

const el = (tag, attrs = {}, ...kids) => {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === 'class') e.className = v;
    else if (k.startsWith('on')) e[k] = v;
    else if (v !== undefined && v !== null) e.setAttribute(k, v);
  }
  for (const kid of kids) e.append(kid);
  return e;
};
const options = (sel, pairs) => sel.replaceChildren(...pairs.map(([v, t]) => el('option', { value: v }, t)));
const toNum = (raw) => {
  const s = String(raw ?? '').trim().replace(',', '.');
  if (!s || !/^[+-]?(\d+\.?\d*|\.\d+)(e[+-]?\d+)?$/i.test(s)) return null;
  return Number(s);
};

export class Settings {
  constructor(host, app) {
    this.app = app;
    this.host = host;
    this.build();
    this.load();
  }

  build() {
    const h = this.host;
    h.innerHTML = `
      <h2>⚙ Cài đặt bộ lọc</h2>
      <div class="cols">
        <div class="left">
          <p class="hint">Mỗi tiêu chí gồm nhiều điều kiện (phải thoả TẤT CẢ). Có nhiều tiêu chí thì bảng giá hiện mỗi
          tiêu chí một khối. Để trống ô giá trị = không lọc cột đó. Giá bằng nghìn đồng (14.2 = 14.200đ), KLGD bằng
          cổ phiếu, GTGD bằng tỷ đồng.</p>
          <div class="row"><label>Tiêu chí</label><select id="s-crit"></select>
            <button id="s-add">＋ Thêm tiêu chí</button><button id="s-del">Xoá</button></div>
          <div class="grid">
            <label>Tên</label><input id="s-name" size="30"><span></span>
            <label>Sàn</label><select id="s-ex"></select><span></span>
            <label>Khi có mã mới</label><select id="s-alert"></select><button id="s-test">Nghe thử</button>
            <label>Sắp xếp theo</label><select id="s-sort"></select><select id="s-dir"></select>
          </div>
          <div class="grid" id="s-legacy"></div>
          <h3>Điều kiện đã thêm</h3>
          <div id="s-extra"></div>
        </div>
        <div class="right">
          <h3>Thêm điều kiện</h3>
          <p class="hint">Chọn nhóm → điều kiện → đặt giá trị → ＋ Thêm. Điều kiện sẽ hiện ở danh sách bên trái.
          Cần lịch sử giá (RSI, MACD, SMA, pullback, trendline, đỉnh/đáy…): lần đầu dùng sẽ tải ~1 phút.
          Khung 15 phút: xét nến đã chốt, tự tải lại mỗi 15 phút.</p>
          <select id="s-grp" class="wide"></select>
          <select id="s-cond" class="wide"></select>
          <div id="s-form"></div>
          <hr>
          <h3>★ Theo dõi</h3>
          <p class="hint">Gõ mã cách nhau bằng dấu cách (vd VIB MBB HPG) → hiện thành khối riêng cuối bảng giá.
          Hoặc chuột phải lên một mã trên bảng giá → ★ Theo dõi.</p>
          <input id="s-watch" class="wide">
          <hr>
          <h3>Chép cài đặt từ app Bee.vn mini (Windows)</h3>
          <p class="hint">Chọn file <code>%APPDATA%\\BeeVnMini\\config.json</code> (dán đường dẫn đó vào ô chọn file)
          → lấy các tiêu chí + danh mục theo dõi sang đây. Bấm Lưu để áp dụng.</p>
          <input type="file" id="s-import" accept=".json,application/json">
          <p class="hint" id="s-voice"></p>
        </div>
      </div>
      <div class="btns"><span id="s-saved"></span><button id="s-save" class="main">Lưu</button></div>`;
    const $ = (id) => h.querySelector('#' + id);
    Object.assign(this, {
      critBox: $('s-crit'), name: $('s-name'), ex: $('s-ex'), alertBox: $('s-alert'), sortCol: $('s-sort'),
      sortDir: $('s-dir'), extra: $('s-extra'), grp: $('s-grp'), cond: $('s-cond'), form: $('s-form'),
      watch: $('s-watch'), saved: $('s-saved'), voice: $('s-voice'),
    });
    options(this.ex, ['HSX', 'HNX', 'UPCOM', 'ALL'].map((k) => [k, EXCHANGE_LABEL[k]]));
    options(this.alertBox, ALERT_LABEL);
    options(this.sortCol, SORT_COLUMNS);
    options(this.sortDir, [['desc', 'Giảm dần'], ['asc', 'Tăng dần']]);

    // Các ô lọc cột có sẵn của bảng giá (toán tử > < = và một giá trị)
    const legacy = $('s-legacy');
    this.rows = {};
    for (const [key, label] of core.FILTERABLE) {
      const op = el('select');
      options(op, OP_LABEL);
      const val = el('input', { size: 12 });
      legacy.append(el('label', {}, label), op, val);
      this.rows[key] = [op, val];
    }

    this.catalog = cond.catalog();
    options(this.grp, [['', '— chọn nhóm —'], ...cond.GROUPS]);
    this.grp.onchange = () => this.onGroup();
    this.cond.onchange = () => this.onCond();
    this.critBox.onchange = () => this.switchTo(Number(this.critBox.value));
    $('s-add').onclick = () => this.addCriterion();
    $('s-del').onclick = () => this.deleteCriterion();
    $('s-test').onclick = () => this.testAlert();
    $('s-save').onclick = () => this.save();
    $('s-import').onchange = (e) => this.importConfig(e.target.files[0]);
    this.onGroup();
  }

  showVoice(name) {
    this.voice.textContent = name ? `Giọng đọc: ${name}` :
      'Máy chưa có giọng tiếng Việt cho Chrome — sẽ đọc tiếng Anh. Cài thêm: Settings → Time & language → Speech → Add voices → Tiếng Việt.';
  }

  // Bản nháp từ cài đặt đang dùng
  load() {
    this.crits = structuredClone(this.app.cfg.criteria);
    this.cur = Math.min(this.cur || 0, this.crits.length - 1);
    this.loadForm();
    this.loadWatch();
  }

  loadWatch() {
    this.watch.value = this.app.cfg.watch.join(' ');
  }

  loadForm() {
    const c = this.crits[this.cur];
    options(this.critBox, this.crits.map((x, i) => [i, x.name]));
    this.critBox.value = this.cur;
    this.name.value = c.name;
    this.ex.value = EXCHANGE_LABEL[c.exchange] ? c.exchange : 'HSX';
    this.alertBox.value = c.alert || 'speak';
    this.sortCol.value = SORT_COLUMNS.some(([k]) => k === c.sortColumn) ? c.sortColumn : 'value';
    this.sortDir.value = c.sortDirection === 'asc' ? 'asc' : 'desc';
    for (const [key, [op, val]] of Object.entries(this.rows)) {
      const f = c.filters[key] || {};
      op.value = OP_LABEL.some(([k]) => k === f.operator) ? f.operator : 'gt';
      val.value = f.value === undefined || f.value === null || f.value === '' ? '' : String(Number(f.value));
    }
    this.refreshExtra();
  }

  // Ghi ô đang sửa vào bản nháp. false (và báo) nếu có ô không phải số.
  storeForm() {
    const cur = this.crits[this.cur];
    const filters = Object.fromEntries(Object.entries(cur.filters).filter(([k]) => !core.LEGACY_KEYS.has(k)));
    const bad = [];
    for (const [key, [op, val]] of Object.entries(this.rows)) {
      const raw = val.value.trim();
      if (!raw) continue;
      const v = toNum(raw);
      if (v === null) bad.push(core.LABEL[key]);
      else filters[key] = { operator: op.value, value: v };
    }
    if (bad.length) {
      alert('Giá trị không phải số: ' + bad.join(', '));
      return false;
    }
    const next = {
      name: this.name.value.trim() || `Tiêu chí ${this.cur + 1}`,
      exchange: this.ex.value,
      filters,
      alert: this.alertBox.value,
      sortColumn: this.sortCol.value,
      sortDirection: this.sortDir.value,
    };
    if (cur.signals && cur.signals.length) next.signals = cur.signals;
    this.crits[this.cur] = next;
    return true;
  }

  switchTo(i) {
    if (i === this.cur) return;
    if (!this.storeForm()) { this.critBox.value = this.cur; return; }
    this.cur = i;
    this.loadForm();
  }

  addCriterion() {
    if (!this.storeForm()) return;
    const cur = this.crits[this.cur];
    this.crits.push({ name: `Tiêu chí ${this.crits.length + 1}`, exchange: cur.exchange, filters: {},
      alert: cur.alert || 'speak', sortColumn: cur.sortColumn || 'value', sortDirection: cur.sortDirection || 'desc' });
    this.cur = this.crits.length - 1;
    this.loadForm();
    this.name.focus();
    this.name.select();
  }

  deleteCriterion() {
    if (this.crits.length === 1) {
      alert('Phải còn ít nhất 1 tiêu chí. Muốn tắt lọc thì xoá trống các ô giá trị.');
      return;
    }
    if (!confirm(`Xoá tiêu chí "${this.crits[this.cur].name}"?`)) return;
    this.crits.splice(this.cur, 1);
    this.cur = Math.max(0, this.cur - 1);
    this.loadForm();
  }

  testAlert() {
    const name = this.name.value.trim() || this.crits[this.cur].name;
    const orig = this.crits[this.cur].name;
    const sec = this.app.sections.find(([c]) => c.name === orig);
    const syms = sec ? sec[1].slice(0, 2).map((s) => s.symbol) : [];
    const mode = this.alertBox.value;
    if (mode === 'off') {
      alert(`Tiêu chí "${name}" đang để Im lặng: có mã mới chỉ sáng vàng, không kêu.`);
      return;
    }
    this.app.alert([[name, syms.length ? syms : ['VIB', 'MBB'], mode]], this.crits.length > 1);
  }

  // ── Điều kiện thêm (kiểu FireAnt): chọn nhóm → điều kiện → đặt giá trị → ＋ Thêm ──
  onGroup() {
    this.items = this.catalog[this.grp.value] || [];
    options(this.cond, [['', this.items.length ? '— chọn điều kiện —' : ''], ...this.items.map(([t], i) => [i, t])]);
    this.form.replaceChildren();
    this.formSpec = null;
  }

  onCond() {
    if (this.cond.value === '') { this.form.replaceChildren(); this.formSpec = null; return; }
    const [, kind, key] = this.items[Number(this.cond.value)];
    this.buildForm(kind, key);
  }

  buildForm(kind, key) {
    const f = this.form;
    f.replaceChildren();
    if (kind === 'metric') {
      const op = el('select');
      options(op, METRIC_OP_LABEL);
      op.value = cond.METRIC_FMT[key] === 'ago' ? 'le' : 'ge';      // "vượt trong N phiên qua" → Đến (≤)
      const v1 = el('input', { size: 10 }), v2 = el('input', { size: 10 });
      const unit = METRIC_UNIT[cond.METRIC_FMT[key]];
      const second = el('div', { class: 'row' }, el('label', {}, 'đến'), v2);
      const toggle = () => { second.hidden = op.value !== 'bt'; };
      op.onchange = toggle;
      toggle();
      f.append(el('div', { class: 'row' }, op, v1, el('span', { class: 'hint' }, unit || '')), second);
      this.formSpec = { kind, key, op, v1, v2 };
    } else {
      const widgets = {};
      for (const p of cond.SIGNALS[key].params) {
        let w;
        if (p.free) {
          const id = `dl-${key}-${p.id}`;
          w = el('input', { size: 10, list: id });
          w.value = cond.paramText(p.default);
          f.append(el('datalist', { id }, ...p.choices.map((c) => el('option', { value: cond.paramText(c) }))));
        } else {
          w = el('select');
          options(w, p.choices.map((c, i) => [i, cond.paramText(c)]));
          w.value = p.choices.indexOf(p.default);
        }
        widgets[p.id] = w;
        f.append(el('div', { class: 'row' }, el('label', {}, p.name), w));
      }
      this.formSpec = { kind, key, widgets };
    }
    f.append(el('div', { class: 'row' }, el('button', { class: 'main', onclick: () => this.addCondition() }, '＋ Thêm')));
  }

  addCondition() {
    const spec = this.formSpec;
    if (!spec) return;
    const c = this.crits[this.cur];
    if (spec.kind === 'metric') {
      const value = toNum(spec.v1.value);
      const value2 = toNum(spec.v2.value);
      if (value === null || (spec.op.value === 'bt' && value2 === null)) {
        alert('Hãy nhập số vào ô giá trị.');
        return;
      }
      const flt = { operator: spec.op.value, value };
      if (spec.op.value === 'bt') flt.value2 = value2;
      c.filters[spec.key] = flt;                  // cùng một cột chỉ có 1 điều kiện — thêm lại là thay
    } else {
      const params = {};
      for (const p of cond.SIGNALS[spec.key].params) {
        const w = spec.widgets[p.id];
        if (p.free) {
          const v = toNum(w.value);
          if (v === null) { alert(`"${p.name}" phải là số.`); return; }
          if (!(p.lo <= v && v <= p.hi)) {
            alert(`"${p.name}" phải từ ${cond.paramText(p.lo)} đến ${cond.paramText(p.hi)}.`);
            return;
          }
          params[p.id] = v;
        } else {
          params[p.id] = p.choices[Number(w.value)];
        }
      }
      const s = cond.normalizeSignal({ id: spec.key, params });
      if (Object.entries(params).some(([k, v]) => typeof v === 'number' && s.params[k] !== v)) {
        alert('SMA ngắn phải ngắn hơn SMA dài.');
        return;
      }
      c.signals ||= [];
      if (!c.signals.some((x) => JSON.stringify(x) === JSON.stringify(s))) c.signals.push(s);
    }
    this.refreshExtra();
    this.cond.value = '';            // thêm xong → bỏ chọn, thấy rõ điều kiện đã sang danh sách bên trái
    this.form.replaceChildren();
    this.formSpec = null;
  }

  refreshExtra() {
    const c = this.crits[this.cur];
    const items = [
      ...core.activeFilterKeys(c.filters).filter((k) => !core.LEGACY_KEYS.has(k))
        .map((k) => [core.describeFilters({ [k]: c.filters[k] }), () => { delete c.filters[k]; this.refreshExtra(); }]),
      ...(c.signals || []).map((s, i) => [cond.describeSignal(s), () => {
        c.signals.splice(i, 1);
        if (!c.signals.length) delete c.signals;
        this.refreshExtra();
      }]),
    ];
    if (!items.length) {
      this.extra.replaceChildren(el('div', { class: 'hint' }, '(chưa có — chọn ở cột bên phải)'));
      return;
    }
    this.extra.replaceChildren(...items.map(([text, drop]) =>
      el('div', { class: 'cond' }, el('span', { class: 'x', title: 'Bỏ điều kiện này', onclick: drop }, '✕'), el('span', {}, text))));
  }

  save() {
    if (!this.storeForm()) return;
    const watch = core.parseSymbols(this.watch.value);
    const unknown = watch.filter((s) => !SYMBOL_SET.has(s));
    if (unknown.length) {
      alert('Không có mã: ' + unknown.join(', ') + '\nKiểm tra lại ô ★ Theo dõi.');
      return;
    }
    const cur = this.cur;
    this.app.applySettings({ criteria: structuredClone(this.crits), watch });
    this.cur = cur;
    this.loadForm();
    this.saved.textContent = '✓ Đã lưu';
    setTimeout(() => { this.saved.textContent = ''; }, 1500);
  }

  async importConfig(file) {
    if (!file) return;
    try {
      const cfg = JSON.parse(await file.text());
      this.crits = structuredClone(core.criteriaFromConfig(cfg));
      this.cur = 0;
      this.loadForm();
      if (cfg.watch) this.watch.value = core.parseSymbols(cfg.watch).join(' ');
      alert(`Đã chép ${this.crits.length} tiêu chí` + (cfg.watch && cfg.watch.length ? ` và ${cfg.watch.length} mã theo dõi` : '') +
        '. Bấm Lưu để áp dụng.');
    } catch (e) {
      alert('Không đọc được file cài đặt: ' + e.message);
    }
  }
}
