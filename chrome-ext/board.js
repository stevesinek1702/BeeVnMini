// Trang thử: dùng được cả dạng tab (board.html) lẫn side panel (board.html?panel=1).
const PANEL = new URLSearchParams(location.search).has('panel');
document.body.classList.toggle('panel', PANEL);
const $ = (id) => document.getElementById(id);

// Trạng thái để đọc từ DevTools / script kiểm thử: window.beeTest
const T = window.beeTest = {
  mode: PANEL ? 'panel' : 'tab', checks: {}, refreshes: 0, timerTicks: [], intervals: [],
  pipOpen: false, voices: {}, spoken: [],
};

function log(msg) {
  const line = `${new Date().toLocaleTimeString('vi-VN')}  ${msg}`;
  $('log').textContent = line + '\n' + $('log').textContent;
}

function check(key, ok, text) {
  T.checks[key] = { ok, text };
  const td = document.querySelector(`#checks tr[data-k="${key}"] td`);
  td.textContent = text;
  td.className = ok == null ? '' : (ok ? 'ok' : 'fail');
}

// Style của bảng nhỏ dùng chung cho trang và cửa sổ PiP
function addBoardCss(doc) {
  const st = doc.createElement('style');
  st.textContent = BOARD_CSS;
  doc.head.appendChild(st);
}
addBoardCss(document);

// ── Dữ liệu ─────────────────────────────────────────────────────────────
let symbols = [];
let hist = {};
let preview = null, pip = null, pipBoard = null;
let lastRows = null, lastMeta = '';
let busy = false;

function parseSymbols(text) {
  return [...new Set(text.toUpperCase().split(/[^A-Z0-9]+/).filter(Boolean))].slice(0, 30);
}

function boards() { return [preview, pipBoard].filter(Boolean); }

function vnClock() {
  return new Date().toLocaleTimeString('vi-VN', { timeZone: 'Asia/Ho_Chi_Minh', hour12: false });
}

async function loadHistory() {
  const t0 = performance.now();
  const res = await Promise.allSettled(symbols.map(fetchHistory));
  const ok = [];
  res.forEach((r, i) => {
    if (r.status === 'fulfilled' && r.value) { hist[symbols[i]] = r.value; ok.push(symbols[i]); }
  });
  const ms = Math.round(performance.now() - t0);
  const err = res.find((r) => r.status === 'rejected');
  const s = hist[ok[0]];
  if (ok.length) {
    check('vndirect', true, `${ok.length}/${symbols.length} mã có nến ngày (${ms} ms). ` +
      `Vd ${ok[0]}: ${s.bars} nến, đóng cửa gần nhất ${s.lastClose}, KL TB45 ${formatVolume(s.avgVol)}`);
  } else {
    check('vndirect', false, `Không lấy được: ${err ? err.reason : 'không có dữ liệu'}`);
  }
}

async function refresh(source) {
  if (busy || !symbols.length) return;
  busy = true;
  const t0 = performance.now();
  try {
    const quotes = await fetchQuotes(symbols);
    const ms = Math.round(performance.now() - t0);
    const bySym = new Map(quotes.map((q) => [q.Symbol, q]));
    lastRows = symbols.filter((s) => bySym.has(s)).map((s) => transformQuote(bySym.get(s), hist[s]));
    lastMeta = `${vnClock()} · ${T.timerMode === 'alarms' ? 'alarms' : 'interval'} 30 s`;
    boards().forEach((b) => b.update(lastRows, lastMeta, false));
    T.refreshes++;
    check('fireant', true, `${quotes.length}/${symbols.length} mã (${ms} ms), gọi thẳng từ extension, không vướng CORS`);
    if (source === 'timer') {
      const now = Date.now(), prev = T.timerTicks.at(-1);
      T.timerTicks.push(now);
      if (prev) T.intervals.push(Math.round((now - prev) / 100) / 10);
      const last = T.intervals.slice(-8).join(' · ');
      const ref = pipBoard || preview;
      check('timer', true, `${T.timerTicks.length} lần tự cập nhật (${T.timerMode}); khoảng cách (s): ${last || '—'}; ` +
        `bảng dựng ${ref.builds} lần, đã đổi ${ref.cellWrites} ô`);
    }
  } catch (e) {
    check('fireant', false, String(e.message || e));
    boards().forEach((b) => b.update([], `${vnClock()} · lỗi mạng`, true));
    log('refresh lỗi: ' + e);
  } finally {
    busy = false;
  }
}

function applySymbols() {
  symbols = parseSymbols($('symbols').value);
  $('symbols').value = symbols.join(' ');
  hist = {};
  preview = new MiniBoard(document, symbols);
  $('preview').replaceChildren(preview.root);
  if (pipBoard) mountPip();
  refresh('manual');
  loadHistory().then(() => refresh('manual'));
}

// ── 2. Cửa sổ nổi Document Picture-in-Picture ───────────────────────────
function mountPip() {
  const d = pip.document;
  pipBoard = new MiniBoard(d, symbols, { foot: true });
  d.body.replaceChildren(pipBoard.root);
  if (lastRows) pipBoard.update(lastRows, lastMeta);
}

async function openPip() {
  if (!('documentPictureInPicture' in window)) {
    check('pip', false, `Không có window.documentPictureInPicture trong ${T.mode}`);
    return;
  }
  try {
    // Chrome tự đặt PiP ở góc dưới-phải màn hình; người dùng kéo cỡ thì lần sau Chrome nhớ cỡ đó
    const w = await documentPictureInPicture.requestWindow({ width: 340, height: 64 + symbols.length * 22 });
    w.document.title = 'Bee.vn';
    addBoardCss(w.document);
    pip = w;
    mountPip();
    T.pipOpen = true;
    check('pip', true, `Đã mở từ ${T.mode} (${w.innerWidth}×${w.innerHeight}). Đóng tab/panel này thì cửa sổ nổi đóng theo.`);
    log('PiP mở');
    const opened = Date.now();
    w.addEventListener('pagehide', () => {
      // Mở PiP mới khi cái cũ còn → Chrome đóng cái cũ; đừng để nó xoá tham chiếu tới cái mới
      if (pip !== w) return;
      pip = null; pipBoard = null; T.pipOpen = false;
      T.pipClosedAfterMs = Date.now() - opened;
      check('pip', null, 'Cửa sổ nổi đã đóng — bấm nút để mở lại');
      log('PiP đóng');
    });
  } catch (e) {
    check('pip', false, `Mở từ ${T.mode} thất bại: ${e.name}: ${e.message}`);
    log('PiP lỗi: ' + e);
  }
}

// ── 3. Hẹn giờ 30 s ─────────────────────────────────────────────────────
let intervalId = null;
function setTimerMode(mode) {
  T.timerMode = mode;
  try { localStorage.setItem('timer', mode); } catch {}
  clearInterval(intervalId);
  intervalId = mode === 'interval' ? setInterval(() => refresh('timer'), 30000) : null;
  T.timerTicks = []; T.intervals = [];
  check('timer', null, `đang chờ lần hẹn giờ đầu (${mode})…`);
}
chrome.runtime.onMessage.addListener((msg) => {
  if (msg && msg.type === 'tick' && T.timerMode === 'alarms') refresh('timer');
});

// ── 4. Giọng đọc ────────────────────────────────────────────────────────
const isVi = (lang) => /^vi\b/i.test(lang || '');

async function listVoices() {
  const ct = await chrome.tts.getVoices();
  const ws = speechSynthesis.getVoices();
  T.voices = {
    chromeTts: ct.map((v) => `${v.voiceName} [${v.lang || '?'}]${v.remote ? ' (online)' : ''}`),
    webSpeech: ws.map((v) => `${v.name} [${v.lang}]${v.localService ? '' : ' (online)'}`),
  };
  const viCt = ct.filter((v) => isVi(v.lang)).map((v) => v.voiceName);
  const viWs = ws.filter((v) => isVi(v.lang)).map((v) => v.name);
  T.voices.viChromeTts = viCt; T.voices.viWebSpeech = viWs;
  const ok = viCt.length > 0 || viWs.length > 0;
  check('tts', ok, `chrome.tts: ${ct.length} giọng, giọng Việt: ${viCt.join(', ') || 'KHÔNG CÓ'} · ` +
    `Web Speech: ${ws.length} giọng, giọng Việt: ${viWs.join(', ') || 'KHÔNG CÓ'}`);
  log('Giọng chrome.tts: ' + T.voices.chromeTts.join('; '));
  log('Giọng Web Speech: ' + T.voices.webSpeech.join('; '));
}

function sayChromeTts(text) {
  const vi = (T.voices.viChromeTts || [])[0];
  chrome.tts.speak(text, {
    lang: 'vi-VN', ...(vi ? { voiceName: vi } : {}),
    onEvent: (e) => {
      if (['start', 'end', 'error'].includes(e.type)) {
        T.spoken.push({ via: 'chrome.tts', type: e.type, voice: vi || '(mặc định)', msg: e.errorMessage });
        log(`chrome.tts ${e.type}${vi ? ' — ' + vi : ' — giọng mặc định (không có giọng Việt)'}${e.errorMessage ? ': ' + e.errorMessage : ''}`);
      }
    },
  });
}

function sayWebSpeech(text) {
  const u = new SpeechSynthesisUtterance(text);
  u.lang = 'vi-VN';
  const v = speechSynthesis.getVoices().find((x) => isVi(x.lang));
  if (v) u.voice = v;
  const name = v ? v.name : '(mặc định)';
  u.onstart = () => { T.spoken.push({ via: 'webSpeech', type: 'start', voice: name }); log('Web Speech bắt đầu — ' + name); };
  u.onend = () => { T.spoken.push({ via: 'webSpeech', type: 'end', voice: name }); log('Web Speech xong'); };
  u.onerror = (e) => { T.spoken.push({ via: 'webSpeech', type: 'error', msg: e.error }); log('Web Speech lỗi: ' + e.error); };
  speechSynthesis.speak(u);
}

function sayGoogle(text) {
  const url = 'https://translate.google.com/translate_tts?ie=UTF-8&client=tw-ob&tl=vi&q=' + encodeURIComponent(text);
  const a = new Audio(url);
  a.onplaying = () => { T.spoken.push({ via: 'google', type: 'start' }); log('Google Dịch đang đọc'); };
  a.onerror = () => { T.spoken.push({ via: 'google', type: 'error' }); log('Google Dịch lỗi tải âm thanh'); };
  a.play().catch((e) => log('Google Dịch: ' + e));
}

// ── Nút bấm ─────────────────────────────────────────────────────────────
let windowId = null;
chrome.windows.getCurrent().then((w) => { windowId = w.id; });

$('apply').onclick = applySymbols;
$('symbols').onkeydown = (e) => { if (e.key === 'Enter') applySymbols(); };
$('pip').onclick = openPip;
$('now').onclick = () => refresh('manual');
$('timer').onchange = (e) => setTimerMode(e.target.value);
// sidePanel.open phải gọi ngay trong cú bấm (cần user gesture) → windowId lấy sẵn từ trước
$('panel').onclick = () => {
  chrome.sidePanel.open({ windowId }).then(() => log('Side panel đã mở'), (e) => log('Side panel lỗi: ' + e.message));
};
$('tts').onclick = () => sayChromeTts($('say').value);
$('speech').onclick = () => sayWebSpeech($('say').value);
$('gtts').onclick = () => sayGoogle($('say').value);

// Tab bảng giá phải sống thì cửa sổ nổi mới sống → xin Chrome đừng tự giải phóng tab khi thiếu RAM
if (!PANEL) {
  chrome.tabs.getCurrent().then((tab) => tab && chrome.tabs.update(tab.id, { autoDiscardable: false }));
}

let saved = 'alarms';
try { saved = localStorage.getItem('timer') || 'alarms'; } catch {}
$('timer').value = saved;
setTimerMode(saved);
applySymbols();
// Chrome nạp danh sách giọng dần dần (giọng Windows OneCore như "Microsoft An" đến sau) → liệt kê lại mỗi lần đổi
speechSynthesis.onvoiceschanged = listVoices;
listVoices();
