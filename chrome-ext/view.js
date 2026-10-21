// Vẽ bảng giá vào một document (tab của extension hoặc cửa sổ nổi PiP) — chép cách render của beevn_mini.pyw:
// mỗi tiêu chí một khối (dòng tên · tiêu đề cột đứng yên · danh sách mã cuộn riêng). Khuôn bảng không đổi
// (giá cập nhật…) → chỉ đổi chữ / màu trong ô có sẵn, không dựng lại → không nháy.
import * as core from './lib/core.js';

const ROW_H = 20, HEAD_H = 20;

export class BoardView {
  // actions: toggleMode, refresh, settings, sortBy(key, crit), toggleSection(name), resizeSection(name, d, n),
  //          menu(event, sym, doc), userClick()
  constructor(doc, host, actions, { pip = false } = {}) {
    this.doc = doc;
    this.actions = actions;
    this.sig = null;
    this.built = [];
    this.blocks = [];
    this.scroll = {};          // {tên khối: vị trí cuộn} — giữ nguyên khi dựng lại
    const d = doc;
    this.root = d.createElement('div');
    this.root.className = 'board';
    this.root.innerHTML =
      '<div class="b-head"><span class="brand"><b>Bee</b><span>.vn</span></span><span class="meta"></span>' +
      '<span class="btn" data-act="refresh" title="Tải lại ngay">↻</span>' +
      '<span class="btn" data-act="mode" title="Thu gọn / đầy đủ">⤢</span>' +
      (pip ? '<span class="btn" data-act="settings" title="Cài đặt bộ lọc (mở tab Bee.vn)">⚙</span>' : '') +
      '</div><div class="b-filters" hidden></div><div class="b-body"></div><div class="b-msg" hidden></div>';
    this.meta = this.root.querySelector('.meta');
    this.filters = this.root.querySelector('.b-filters');
    this.body = this.root.querySelector('.b-body');
    this.msg = this.root.querySelector('.b-msg');
    host.replaceChildren(this.root);
    this.root.addEventListener('click', (e) => this.onClick(e));
    this.root.addEventListener('contextmenu', (e) => {
      e.preventDefault();
      const tr = e.target.closest('tr[data-sym]');
      this.actions.menu(e, tr ? tr.dataset.sym : null, this.doc);
    });
  }

  onClick(e) {
    this.handleClick(e.target);
    this.actions.userClick?.(this.doc);       // sau khi bảng đã vẽ lại: cửa sổ nổi co giãn theo nội dung mới
  }

  handleClick(t) {
    const act = t.closest('[data-act]');
    if (act) {
      const a = act.dataset.act;
      if (a === 'refresh') this.actions.refresh();
      else if (a === 'mode') this.actions.toggleMode();
      else if (a === 'settings') this.actions.settings();
      else if (a === 'collapse') this.actions.toggleSection(act.dataset.name);
      else if (a === 'plus' || a === 'minus') {
        const bi = Number(act.dataset.bi);
        this.actions.resizeSection(this.blocks[bi][0].name, a === 'plus' ? 3 : -3, this.blocks[bi][1].length);
      }
      return;
    }
    const th = t.closest('th[data-key]');
    if (th) {
      const bi = Number(th.dataset.bi);
      this.actions.sortBy(th.dataset.key, this.blocks[bi][0]);
      return;
    }
    if (t.closest('table.b tbody, .sec-desc, .sec-empty')) this.actions.toggleMode();
  }

  // m: {full, multi, blocks: [[tiêu chí, [hàng]]], meta, stale, filtersText, msg, msgErr, newUntil, rowsOf(name, multi), collapsed}
  render(m) {
    this.meta.textContent = m.meta;
    this.meta.classList.toggle('stale', !!m.stale);
    this.filters.hidden = !m.filtersText;
    if (m.filtersText) this.filters.textContent = m.filtersText;

    this.blocks = m.blocks;
    const sig = JSON.stringify([m.multi, m.full, m.blocks.map(([c, rows]) => this.sectionSig(c, rows, m))]);
    if (sig === this.sig) {
      this.built.forEach((info, i) => this.fill(info, m.blocks[i][0], m.blocks[i][1], m, i));
    } else {
      for (const info of this.built) if (info.scroller) this.scroll[info.name] = info.scroller.scrollTop;
      const frag = this.doc.createDocumentFragment();
      this.built = m.blocks.map(([c, rows], i) => this.build(frag, c, rows, m, i));
      this.body.replaceChildren(frag);
      this.sig = sig;
      for (const info of this.built) if (info.scroller) info.scroller.scrollTop = this.scroll[info.name] || 0;
    }
    this.msg.hidden = !m.msg;
    this.msg.textContent = m.msg || '';
    this.msg.classList.toggle('err', !!m.msgErr);
  }

  sectionSig(c, rows, m) {
    if (m.multi && m.collapsed.includes(c.name)) return [c.name, 'collapsed'];
    if (!rows.length) return [c.name, 'empty'];
    return [c.name, core.tableColumns(c, m.full).map((x) => x[0]), rows.length, m.rowsOf(c.name, m.multi)];
  }

  title(c, rows, m) {
    const collapsed = m.collapsed.includes(c.name);
    const ex = c.watch ? '' : (m.exchangeLabel[c.exchange] || c.exchange) + '  ·  ';
    const more = !collapsed && rows.length > m.rowsOf(c.name, m.multi) ? '  ·  lăn ↕ xem đủ' : '';
    return `${collapsed ? '▸' : '▾'} ${c.name}  ·  ${ex}${rows.length} mã${more}`;
  }

  build(parent, c, rows, m, bi) {
    const d = this.doc;
    const info = { name: c.name, title: null, desc: null, heads: [], rows: [], cols: [], scroller: null };
    const box = d.createElement('div');
    parent.appendChild(box);
    const collapsed = m.multi && m.collapsed.includes(c.name);
    const limit = m.rowsOf(c.name, m.multi);
    if (m.multi) {
      const bar = d.createElement('div');
      bar.className = 'sec-bar';
      const title = d.createElement('span');
      title.className = 'title';
      title.dataset.act = 'collapse';
      title.dataset.name = c.name;
      bar.appendChild(title);
      info.title = title;
      if (!collapsed) {
        for (const [txt, act] of [['－', 'minus'], ['＋', 'plus']]) {
          const b = d.createElement('span');
          b.className = 'pm';
          b.textContent = txt;
          b.dataset.act = act;
          b.dataset.bi = bi;
          bar.appendChild(b);
        }
      }
      box.appendChild(bar);
      if (collapsed) { this.fill(info, c, rows, m, bi); return info; }
      if (m.full && !c.watch) {
        info.desc = d.createElement('div');
        info.desc.className = 'sec-desc';
        box.appendChild(info.desc);
      }
    }
    if (!rows.length) {
      if (m.multi) {
        const e = d.createElement('div');
        e.className = 'sec-empty';
        e.textContent = 'chưa có mã nào khớp';
        box.appendChild(e);
      }
      this.fill(info, c, rows, m, bi);
      return info;
    }
    const cols = core.tableColumns(c, m.full);
    const table = d.createElement('table');
    table.className = 'b';
    const htr = table.createTHead().insertRow();
    for (const [key] of cols) {
      const th = d.createElement('th');
      th.dataset.key = key;
      th.dataset.bi = bi;
      htr.appendChild(th);
      info.heads.push(th);
    }
    const tbody = table.createTBody();
    for (let ri = 0; ri < rows.length; ri++) {
      const tr = tbody.insertRow();
      const cells = cols.map(([key]) => {
        const td = tr.insertCell();
        if (key === 'symbol') td.className = 'sym';
        return td;
      });
      info.rows.push([tr, cells]);
    }
    if (rows.length > limit) {
      const sc = d.createElement('div');
      sc.className = 'sec-scroll';
      sc.style.maxHeight = `${HEAD_H + ROW_H * limit}px`;
      sc.appendChild(table);
      box.appendChild(sc);
      info.scroller = sc;
    } else {
      box.appendChild(table);
    }
    const gap = d.createElement('div');
    gap.className = 'sec-gap';
    box.appendChild(gap);
    info.cols = cols;
    this.fill(info, c, rows, m, bi);
    return info;
  }

  fill(info, c, rows, m, bi) {
    if (info.title) setText(info.title, this.title(c, rows, m));
    if (info.desc) setText(info.desc, core.describeFilters(c.filters, c.signals));
    if (!info.rows.length) return;
    const active = new Set(core.activeFilterKeys(c.filters));
    const [sortCol, sortDir] = m.sortOf(c);
    info.cols.forEach(([key, label], i) => {
      const arrow = key === sortCol ? (sortDir === 'asc' ? ' ▲' : ' ▼') : '';
      const th = info.heads[i];
      setText(th, (core.HEAD_LABEL[key] ?? label) + (active.has(key) ? ' •' : '') + arrow);
      setClass(th, active.has(key) ? 'flt' : (key === sortCol ? 'on' : ''));
      th.dataset.bi = bi;
    });
    const now = Date.now();
    rows.forEach((st, ri) => {
      const [tr, cells] = info.rows[ri];
      tr.dataset.sym = st.symbol;
      setClass(tr, (m.newUntil[st.symbol] || 0) > now ? 'new' : (ri % 2 === 1 ? 'alt' : ''));
      info.cols.forEach(([key], ci) => {
        const [text, tone] = core.formatCell(st, key);
        setText(cells[ci], text);
        setClass(cells[ci], (key === 'symbol' ? 'sym ' : '') + tone);
      });
    });
  }
}

// Chỉ ghi khi khác — trình duyệt khỏi vẽ lại ô không đổi
function setText(el, text) {
  if (el.textContent !== text) el.textContent = text;
}
function setClass(el, cls) {
  cls = cls.trim();
  if (el.className !== cls) el.className = cls;
}
