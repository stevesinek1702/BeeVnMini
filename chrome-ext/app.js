// Bee.vn mini trong Chrome — trang chính (tab của extension). Chép luồng của beevn_mini.pyw:
// lấy giá 30 s/lần trong giờ (10 phút ngoài giờ), MA / KL trung bình từ VNDirect mỗi ngày, chỉ báo kỹ thuật khi có
// tiêu chí cần, lọc từng tiêu chí, báo mã mới (đọc tên / ting / im), vẽ bảng ở tab và ở cửa sổ nổi (PiP).
import * as core from './lib/core.js';
import * as tech from './lib/tech.js';
import { SYMBOLS } from './lib/symbols.js';
import { fetchQuotes, fetchAllHistory } from './data.js';
import { BoardView } from './view.js';
import { Settings } from './settings.js';

const OFF_HOURS_SEC = 600;
const HIST_CHECK_SEC = 600;
const STALE_SEC = 120;
const MAX_ROWS = 25;          // 1 khối: quá số hàng này thì lăn chuột để xem tiếp
const SECTION_ROWS = 8;       // nhiều khối: mỗi khối mặc định hiện chừng này hàng (＋/－ để đổi)
const NEW_HIGHLIGHT_SEC = 6;

export const EXCHANGE_LABEL = { HSX: 'HSX', HNX: 'HNX', UPCOM: 'UpCom', ALL: 'Cả 3 sàn' };
const DEFAULT_CONFIG = {
  exchange: 'HSX', filters: {}, sortColumn: 'value', sortDirection: 'desc', mode: 'compact',
  alert: 'speak', watch: [], watchSort: ['symbol', 'asc'], collapsed: [], sectionRows: {},
};

const $ = (id) => document.getElementById(id);
const today = () => core.vnDate(Date.now() / 1000);

class App {
  async init() {
    const saved = await chrome.storage.local.get(['config', 'hist', 'tech']);
    this.cfg = { ...DEFAULT_CONFIG, ...(saved.config || {}) };
    this.cfg.criteria = core.criteriaFromConfig(this.cfg);
    this.cfg.watch = core.parseSymbols(this.cfg.watch);
    this.hist = saved.hist || {};
    this.tech = saved.tech || {};
    this.histProgress = this.hist.day === today() && this.histComplete() ? 1 : 0;
    this.techProgress = this.techFresh(today()) ? 1 : 0;
    this.quotes = null;
    this.fetchedAt = null;
    this.lastQuoteTry = 0;
    this.error = null;
    this.prevByKey = null;
    this.newUntil = {};
    this.sections = [];
    this.matches = [];
    this.watchBlock = null;
    this.forceTech = false;
    this.busy = {};
    this.lastHistCheck = 0;
    this.lastTechCheck = 0;
    this.pending = [];            // câu đọc đến lúc đang đọc dở → đọc tiếp sau
    this.speaking = false;
    this.pip = null;
    this.pipView = null;

    const actions = this.actions();
    this.tabView = new BoardView(document, $('boardHost'), actions);
    this.settings = new Settings($('settings'), this);
    this.cssText = await (await fetch('board.css')).text();

    $('openPip').onclick = () => this.openPip();
    document.addEventListener('click', () => this.closeMenu(document));
    chrome.runtime.onMessage.addListener((msg) => { if (msg && msg.type === 'tick') this.tick(); });
    // Phòng khi service worker lỡ nhịp: tự gõ nhịp (tab ẩn thì Chrome cho tối đa 1 lần/phút)
    setInterval(() => { if (Date.now() - (this.lastTick || 0) > 45000) this.tick(); }, 30000);
    chrome.tabs.getCurrent().then((tab) => {
      if (!tab) return;
      this.tabId = tab.id;
      this.windowId = tab.windowId;
      // Tab phải sống thì cửa sổ nổi mới sống → xin Chrome đừng tự giải phóng tab
      chrome.tabs.update(tab.id, { autoDiscardable: false });
    });
    // Chrome nạp danh sách giọng dần (giọng Windows như "Microsoft An" đến sau vài giây) → liệt kê lại mỗi lần đổi
    speechSynthesis.onvoiceschanged = () => this.loadVoices();
    speechSynthesis.getVoices();
    this.loadVoices();

    this.render();
    this.tick(true);
  }

  // ── Nhịp 30 giây (chrome.alarms ở service worker gửi sang) ──
  tick(first = false) {
    this.lastTick = Date.now();
    const now = Date.now();
    if (first || core.isTradingTime() || now - this.lastQuoteTry >= OFF_HOURS_SEC * 1000) this.loadQuotes();
    if (first || now - this.lastHistCheck >= HIST_CHECK_SEC * 1000) this.loadHist();
    if (first || now - this.lastTechCheck >= HIST_CHECK_SEC * 1000) this.loadTech();
    this.render();
  }

  async loadQuotes() {
    if (this.busy.quotes) return;
    this.busy.quotes = true;
    this.lastQuoteTry = Date.now();
    try {
      this.quotes = await fetchQuotes(SYMBOLS);
      this.fetchedAt = Date.now();
      this.error = null;
      this.compute();
    } catch (e) {
      this.error = String(e.message || e);
      console.warn('quotes', e);
    } finally {
      this.busy.quotes = false;
      this.render();
    }
  }

  histComplete() {
    return Object.keys(this.hist.data || {}).length >= SYMBOLS.length;
  }

  // MA10/20/45 + KL trung bình 45 phiên tự tính từ VNDirect, mỗi ngày một lần.
  // (Bản Python còn lấy được từ FireAnt TradingStatistic bằng cookie Google Sheet — bản extension chưa làm.)
  async loadHist() {
    if (this.busy.hist) return;
    this.busy.hist = true;
    this.lastHistCheck = Date.now();
    try {
      const day = today();
      const hist = this.hist.day === day ? this.hist : { day, data: {} };
      if (Object.keys(hist.data).length < SYMBOLS.length) {
        const data = await fetchAllHistory(SYMBOLS, day, hist.data, (p) => { this.histProgress = p; this.renderSoon(); });
        this.hist = { day, data, source: 'vndirect' };
        await chrome.storage.local.set({ hist: this.hist });
        this.histProgress = Object.keys(data).length / SYMBOLS.length;
        // MA vừa có → cả loạt mã bỗng khớp; đó không phải "mã mới lọt lọc" → lấy lại mốc so, không báo
        this.prevByKey = null;
        this.compute();
      }
    } catch (e) {
      console.warn('hist', e);
    } finally {
      this.busy.hist = false;
      this.render();
    }
  }

  techFresh(day) {
    return this.tech.day === day && this.tech.ver === tech.VERSION;
  }

  techData() {
    return this.techFresh(today()) ? (this.tech.data || {}) : {};
  }

  techPending() {
    return this.techProgress < 1 && this.cfg.criteria.some(core.needsTech);
  }

  // Thống kê kỹ thuật từ nến ngày (~1 phút cho cả thị trường) — chỉ tải khi có tiêu chí cần, mỗi ngày một lần.
  // Tính trong Web Worker để trang không đơ.
  async loadTech() {
    if (this.busy.tech) return;
    this.lastTechCheck = Date.now();
    if (!this.cfg.criteria.some(core.needsTech)) return;
    this.busy.tech = true;
    try {
      const day = today();
      const bt = this.cfg.criteria.some(core.needsBreakHistory);
      const fresh = this.techFresh(day) && (this.tech.bt || !bt) && !this.forceTech;
      this.forceTech = false;
      const cur = fresh ? this.tech : { day, ver: tech.VERSION, bt, data: {} };
      if (Object.keys(cur.data).length < SYMBOLS.length) {
        this.techProgress = Object.keys(cur.data).length / SYMBOLS.length;
        this.render();
        const data = await this.runWorker({ symbols: SYMBOLS, today: day, done: cur.data, history: !!cur.bt },
          (p) => { this.techProgress = p; this.renderSoon(); });
        this.tech = { day, ver: tech.VERSION, bt: !!cur.bt, data };
        await chrome.storage.local.set({ tech: this.tech });
        this.techProgress = Object.keys(data).length / SYMBOLS.length;
        this.prevByKey = null;          // chỉ báo vừa có → không báo "mã mới" cả loạt
        this.compute();
      } else {
        this.techProgress = 1;
      }
    } catch (e) {
      console.warn('tech', e);
    } finally {
      this.busy.tech = false;
      this.render();
    }
  }

  runWorker(msg, onProgress) {
    return new Promise((resolve, reject) => {
      const w = new Worker('techworker.js', { type: 'module' });
      w.onmessage = (e) => {
        if (e.data.progress !== undefined) onProgress(e.data.progress);
        if (e.data.data) { w.terminate(); resolve(e.data.data); }
      };
      w.onerror = (e) => { w.terminate(); reject(e.message || e); };
      w.postMessage(msg);
    });
  }

  rescanTech() {
    if (!this.cfg.criteria.some(core.needsTech)) {
      alert('Chưa có tiêu chí nào dùng trendline / chỉ báo kỹ thuật để quét.');
      return;
    }
    this.forceTech = true;
    this.techProgress = 0;
    this.render();
    this.loadTech();
  }

  // ── Lọc ──
  watchCrit() {
    const [col, dir] = this.cfg.watchSort || ['symbol', 'asc'];
    return { name: core.WATCH_NAME, exchange: 'ALL', filters: {}, watch: true, sortColumn: col, sortDirection: dir };
  }

  compute() {
    if (this.quotes === null) return;
    const data = (this.hist.day === today() && this.hist.data) || {};
    const td = this.techData();
    const now = Date.now();
    const rows = this.quotes.map((q) => core.transformQuote(q, data[q.Symbol], td[q.Symbol], now));
    const all = core.groupByExchange(rows);
    const sort = { sortColumn: this.cfg.sortColumn, sortDirection: this.cfg.sortDirection };

    const wc = this.watchCrit();
    const mine = core.selectWatch(rows, this.cfg.watch, wc.sortColumn, wc.sortDirection);
    this.watchBlock = mine.length ? [wc, mine] : null;

    this.sections = [];
    const seen = new Set(), flat = [];
    for (const c of this.cfg.criteria) {
      if (!core.hasConditions(c)) continue;
      const m = core.selectMatches(all, { ...sort, ...c });
      this.sections.push([c, m]);
      for (const st of m) if (!seen.has(st.symbol)) { seen.add(st.symbol); flat.push(st); }
    }
    this.matches = flat;

    const nowByKey = new Map(this.sections.map(([c, m]) => [core.criterionKey(c), new Set(m.map((s) => s.symbol))]));
    if (this.prevByKey) {
      const groups = [];
      for (const [c, m] of this.sections) {
        const before = this.prevByKey.get(core.criterionKey(c));
        if (!before) continue;          // tiêu chí vừa thêm / vừa sửa → chưa có gì để so
        const fresh = m.map((s) => s.symbol).filter((s) => !before.has(s));
        if (fresh.length) groups.push([c.name, fresh, c.alert || 'speak']);
      }
      if (groups.length) {
        const until = now + NEW_HIGHLIGHT_SEC * 1000;
        for (const [, syms] of groups) for (const s of syms) this.newUntil[s] = until;
        this.alert(groups);
        setTimeout(() => this.render(), NEW_HIGHLIGHT_SEC * 1000 + 100);
      }
    }
    this.prevByKey = nowByKey;
  }

  // ── Báo mã mới ──
  loadVoices() {
    chrome.tts.getVoices((voices) => {
      const vi = (voices || []).find((v) => /^vi\b/i.test(v.lang || ''));
      this.viVoice = vi ? vi.voiceName : null;
      this.settings?.showVoice(this.viVoice);
    });
  }

  // groups = [[tên tiêu chí, [mã mới…], kiểu báo]]: "đọc tên mã" đọc gộp một câu; có "kêu ting" thì kêu một tiếng
  alert(groups, names = null) {
    groups = groups.filter(([, s]) => s.length);
    let speak = groups.filter(([, , mode]) => mode === 'speak').map(([n, s]) => [n, s]);
    let beep = groups.some(([, , mode]) => mode === 'beep');
    if (speak.length) {
      if (this.speaking) {
        this.pending.push(...speak);
        speak = [];
      } else if (!this.say(speak, names)) {
        beep = true;
      }
    }
    if (beep) this.beep();
  }

  say(groups, names = null) {
    if (names === null) names = this.cfg.criteria.length > 1;
    const [vi, en] = core.alertTextGroups(groups, 6, names);
    try {
      this.speaking = true;
      chrome.tts.speak(this.viVoice ? vi : en, {
        lang: this.viVoice ? 'vi-VN' : 'en-US',
        ...(this.viVoice ? { voiceName: this.viVoice } : {}),
        onEvent: (e) => {
          if (['end', 'interrupted', 'cancelled', 'error'].includes(e.type)) {
            this.speaking = false;
            this.sayPending();
          }
        },
      });
      return true;
    } catch (e) {
      this.speaking = false;
      console.warn('tts', e);
      return false;
    }
  }

  // Đọc nốt những mã mới đến trong lúc đang đọc dở (gộp theo tiêu chí, bỏ mã trùng)
  sayPending() {
    if (!this.pending.length || this.speaking) return;
    const merged = new Map();
    for (const [name, syms] of this.pending) {
      const lst = merged.get(name) || [];
      for (const x of syms) if (!lst.includes(x)) lst.push(x);
      merged.set(name, lst);
    }
    this.pending = [];
    this.alert([...merged].map(([n, s]) => [n, s, 'speak']));
  }

  beep() {
    try {
      this.audio ||= new AudioContext();
      const ctx = this.audio;
      ctx.resume();
      const o = ctx.createOscillator(), g = ctx.createGain();
      o.frequency.value = 1320;
      g.gain.setValueAtTime(0.25, ctx.currentTime);
      g.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.35);
      o.connect(g).connect(ctx.destination);
      o.start();
      o.stop(ctx.currentTime + 0.35);
    } catch (e) {
      console.warn('beep', e);
    }
  }

  // ── Vẽ ──
  sectionRows(name, multi) {
    return Number((this.cfg.sectionRows || {})[name] ?? (multi ? SECTION_ROWS : MAX_ROWS));
  }

  sortOf(c) {
    return [c.sortColumn || this.cfg.sortColumn, c.sortDirection || this.cfg.sortDirection];
  }

  maSourceNote() {
    if (this.histProgress < 1) return `đang tính MA ${Math.floor(this.histProgress * 100)}%`;
    return 'MA: tự tính từ VNDirect';
  }

  techNote() {
    return `đang tính chỉ báo kỹ thuật ${Math.floor(this.techProgress * 100)}%`;
  }

  model() {
    const cfg = this.cfg;
    const full = cfg.mode === 'full';
    const crits = cfg.criteria;
    const sections = this.quotes !== null ? this.sections : [];
    const watch = this.quotes !== null ? this.watchBlock : null;
    const nCrit = crits.filter(core.hasConditions).length;
    const hasFilter = nCrit > 0;
    const blocks = [...sections, ...(watch ? [watch] : [])];
    const multi = nCrit + (watch ? 1 : 0) > 1;

    let parts;
    if (nCrit > 1) parts = [`${sections.length || crits.length} tiêu chí`];
    else if (hasFilter || !cfg.watch.length) {
      const first = crits.find(core.hasConditions) || crits[0];
      parts = [EXCHANGE_LABEL[first.exchange] || first.exchange];
    } else parts = [core.WATCH_NAME];
    if (hasFilter && this.quotes !== null) parts.push(`${this.matches.length} mã`);
    else if (watch) parts.push(`${watch[1].length} mã`);
    if (this.fetchedAt) parts.push(new Date(this.fetchedAt).toLocaleTimeString('vi-VN', { hour12: false }));
    const stale = !!(this.error || (this.fetchedAt && core.isTradingTime() && Date.now() - this.fetchedAt > STALE_SEC * 1000));

    let filtersText = null;
    if (full && (hasFilter || watch)) {
      filtersText = this.maSourceNote();
      if (this.techPending()) filtersText += '   ·   ' + this.techNote();
      if (!multi && sections.length) filtersText = core.describeFilters(sections[0][0].filters, sections[0][0].signals) + '   ·   ' + filtersText;
    }

    const total = sections.reduce((a, [, m]) => a + m.length, 0);
    let msg = '', msgErr = false;
    if (this.quotes === null && !this.error) msg = 'Đang tải giá…';
    else if (this.error && this.quotes === null) { msg = `${this.error}. Sẽ tự thử lại — kiểm tra mạng Internet.`; msgErr = true; }
    else if (!hasFilter && !cfg.watch.length) msg = 'Chưa có bộ lọc. Bấm ⚙ để đặt lọc\n(vd Giá < 20, % Thay đổi > 2), hoặc gõ mã vào ô ★ Theo dõi.';
    else if (total === 0 && this.techPending()) msg = this.techNote().replace(/^./, (c) => c.toUpperCase()) + '…';
    else if (hasFilter && !multi && total === 0) msg = 'Chưa có mã nào khớp bộ lọc.';

    return {
      full, multi, blocks, meta: parts.join(' · '), stale, filtersText, msg, msgErr,
      newUntil: this.newUntil, collapsed: cfg.collapsed || [], exchangeLabel: EXCHANGE_LABEL,
      rowsOf: (n, mu) => this.sectionRows(n, mu), sortOf: (c) => this.sortOf(c),
    };
  }

  render() {
    const m = this.model();
    this.tabView.render(m);
    if (this.pipView) this.pipView.render(m);
    this.renderStatus();
  }

  renderSoon() {
    if (this.renderTimer) return;
    this.renderTimer = setTimeout(() => { this.renderTimer = null; this.render(); }, 500);
  }

  renderStatus() {
    const bits = [];
    bits.push(this.pip ? 'Cửa sổ nổi: đang mở' : 'Cửa sổ nổi: chưa mở');
    bits.push(this.maSourceNote());
    if (this.cfg.criteria.some(core.needsTech)) {
      bits.push(this.techProgress < 1 ? this.techNote() : `chỉ báo kỹ thuật: xong (${this.tech.day || ''})`);
    }
    if (this.error) bits.push('lỗi: ' + this.error);
    $('status').textContent = bits.join('   ·   ');
  }

  // ── Thao tác (bấm trên bảng ở tab hoặc ở cửa sổ nổi) ──
  actions() {
    return {
      toggleMode: () => this.toggleMode(),
      refresh: () => { this.loadQuotes(); },
      settings: () => this.focusTab(),
      sortBy: (key, crit) => this.sortBy(key, crit),
      toggleSection: (name) => this.toggleSection(name),
      resizeSection: (name, d, n) => this.resizeSection(name, d, n),
      menu: (e, sym, doc) => this.showMenu(e, sym, doc),
      userClick: (doc) => { if (this.pip && doc === this.pip.document) this.fitPip(); },
    };
  }

  async saveConfig() {
    await chrome.storage.local.set({ config: this.cfg });
  }

  toggleMode() {
    this.cfg.mode = this.cfg.mode === 'full' ? 'compact' : 'full';
    this.saveConfig();
    this.render();
  }

  sortBy(key, crit) {
    [crit.sortColumn, crit.sortDirection] = core.nextSort(...this.sortOf(crit), key);
    if (crit.watch) this.cfg.watchSort = [crit.sortColumn, crit.sortDirection];
    this.saveConfig();
    for (const v of [this.tabView, this.pipView]) if (v) v.scroll[crit.name] = 0;
    this.compute();
    this.render();
  }

  toggleSection(name) {
    const col = [...(this.cfg.collapsed || [])];
    const i = col.indexOf(name);
    if (i >= 0) col.splice(i, 1); else col.push(name);
    this.cfg.collapsed = col;
    this.saveConfig();
    this.render();
  }

  resizeSection(name, delta, n) {
    const rows = { ...(this.cfg.sectionRows || {}) };
    const cur = this.sectionRows(name, true);
    rows[name] = Math.max(2, Math.min(cur + delta, Math.max(n, 2), 40));
    this.cfg.sectionRows = rows;
    this.saveConfig();
    this.render();
  }

  toggleWatch(sym) {
    const watch = this.cfg.watch.filter((s) => s !== sym);
    if (watch.length === this.cfg.watch.length) watch.push(sym);
    this.cfg.watch = watch;
    this.saveConfig();
    this.settings.loadWatch();
    this.compute();
    this.render();
  }

  setExchange(key) {
    const crits = this.cfg.criteria.map((c) => ({ ...c }));
    crits[0].exchange = key;
    this.applySettings({ criteria: crits });
  }

  applySettings(newCfg) {
    Object.assign(this.cfg, newCfg);
    this.cfg.criteria = core.criteriaFromConfig(this.cfg);
    this.cfg.watch = core.parseSymbols(this.cfg.watch);
    this.saveConfig();
    for (const v of [this.tabView, this.pipView]) if (v) v.scroll = {};
    this.compute();
    this.render();
    this.settings.load();
    this.lastTechCheck = 0;          // vừa thêm điều kiện cần chỉ báo kỹ thuật → bắt đầu tải ngay
    this.loadTech();
  }

  focusTab() {
    if (this.tabId === undefined) return;
    chrome.tabs.update(this.tabId, { active: true });
    chrome.windows.update(this.windowId, { focused: true });
    $('settings').scrollIntoView();
  }

  // ── Menu chuột phải ──
  showMenu(e, sym, doc) {
    this.closeMenu(doc);
    const m = doc.createElement('div');
    m.className = 'ctx';
    const add = (label, fn, on = false) => {
      const it = doc.createElement('div');
      it.textContent = label;
      if (on) it.className = 'on';
      it.onclick = (ev) => { ev.stopPropagation(); this.closeMenu(doc); fn(); };
      m.appendChild(it);
    };
    const sep = () => m.appendChild(doc.createElement('hr'));
    if (sym) {
      add(this.cfg.watch.includes(sym) ? `✕ Bỏ theo dõi ${sym}` : `★ Theo dõi ${sym}`, () => this.toggleWatch(sym));
      sep();
    }
    add('Thu gọn / đầy đủ', () => this.toggleMode());
    add('Tải lại ngay', () => this.loadQuotes());
    add('Quét lại trendline / chỉ báo ngay', () => this.rescanTech());
    add('Cài đặt bộ lọc…', () => this.focusTab());
    if (this.cfg.criteria.length === 1) {
      sep();
      for (const key of ['HSX', 'HNX', 'UPCOM', 'ALL']) {
        add('Sàn: ' + EXCHANGE_LABEL[key], () => this.setExchange(key), this.cfg.criteria[0].exchange === key);
      }
    }
    doc.body.appendChild(m);
    const w = doc.documentElement.clientWidth, h = doc.documentElement.clientHeight;
    m.style.left = Math.max(0, Math.min(e.clientX, w - m.offsetWidth - 2)) + 'px';
    m.style.top = Math.max(0, Math.min(e.clientY, h - m.offsetHeight - 2)) + 'px';
    this.menuEl = m;
  }

  closeMenu() {
    if (this.menuEl) { this.menuEl.remove(); this.menuEl = null; }
  }

  // ── Cửa sổ nổi (Document Picture-in-Picture) — mở được từ tab của extension, cần cú bấm ──
  async openPip() {
    if (!('documentPictureInPicture' in window)) {
      alert('Chrome này chưa có Document Picture-in-Picture (cần Chrome 116 trở lên).');
      return;
    }
    // Cỡ đầu = cỡ bảng đang hiện ở tab; Chrome giữ diện tích PiP ≤ ¼ màn hình → ưu tiên bề ngang
    const r = this.tabView.root.getBoundingClientRect();
    const width = Math.max(260, Math.ceil(r.width) + 4);
    let height = Math.min(Math.max(120, Math.ceil(r.height) + 4), 800);
    const maxArea = screen.width * screen.height / 4 * 0.9;
    if (width * height > maxArea) height = Math.max(200, Math.floor(maxArea / width));
    const w = await documentPictureInPicture.requestWindow({ width, height });
    const st = w.document.createElement('style');
    st.textContent = this.cssText;
    w.document.head.appendChild(st);
    w.document.title = 'Bee.vn';
    const icon = w.document.createElement('link');
    icon.rel = 'icon';
    icon.href = chrome.runtime.getURL('icons/icon32.png');
    w.document.head.appendChild(icon);
    w.document.body.className = 'pip';
    this.pip = w;
    this.pipView = new BoardView(w.document, w.document.body, this.actions(), { pip: true });
    w.document.addEventListener('click', () => this.closeMenu());
    w.addEventListener('pagehide', () => {
      if (this.pip !== w) return;      // mở PiP mới khi cái cũ còn → Chrome đóng cái cũ; đừng xoá cái mới
      this.pip = null;
      this.pipView = null;
      this.render();
    });
    this.render();
  }

  // Co giãn cửa sổ nổi vừa nội dung — Chrome chỉ cho đổi cỡ PiP ngay sau một cú bấm trong nó
  fitPip() {
    const w = this.pip;
    if (!w) return;
    // Tính ngay (không chờ khung hình: tab bị che thì requestAnimationFrame của nó không chạy, quá lâu thì hết lượt bấm)
    try {
      // Đo cỡ tự nhiên của bảng (không bị kéo giãn theo cửa sổ đang có)
      const root = this.pipView.root;
      root.style.width = 'max-content';
      root.style.minWidth = '0';
      const natW = root.offsetWidth, natH = root.offsetHeight;
      root.style.width = root.style.minWidth = '';
      const dw = w.outerWidth - w.innerWidth, dh = w.outerHeight - w.innerHeight;
      let W = Math.max(260, natW + 2) + dw;
      let H = Math.min(Math.max(120, natH + 6) + dh, w.screen.availHeight - 40);
      // Chrome giữ diện tích cửa sổ PiP ≤ ¼ màn hình (đo trên Chrome 155: xin to hơn thì nó thu cả hai chiều cùng tỷ lệ).
      // Ưu tiên đủ bề ngang (đủ cột), bớt chiều cao — các khối vốn tự cuộn dọc.
      const maxArea = w.screen.width * w.screen.height / 4 * 0.98;
      if (W * H > maxArea) {
        H = Math.max(200, Math.floor(maxArea / W));
        if (W * H > maxArea) W = Math.floor(maxArea / H);
      }
      if (H - dh < natH) W += 16;      // sẽ có thanh cuộn dọc → chừa chỗ cho khỏi sinh thêm thanh cuộn ngang
      this.lastFit = { natW, natH, W, H };
      if (Math.abs(W - w.outerWidth) < 4 && Math.abs(H - w.outerHeight) < 4) return;
      // Chỉ đổi cỡ được (góc trên-trái đứng yên; phóng to quá mép thì Chrome tự đẩy vào trong màn hình).
      // moveTo bị Chrome bỏ qua với cửa sổ PiP → không giữ được góc dưới-phải như app cũ.
      w.resizeTo(W, H);
    } catch (e) {
      console.warn('fitPip', e.message);
    }
  }
}

const app = new App();
window.beeApp = app;
app.init();
