// Service worker: hẹn giờ 30 s bằng chrome.alarms (tối thiểu Chrome cho phép là 30 s)
// rồi báo cho trang bảng giá đang mở. Trang tự lấy dữ liệu và đổi chữ trong ô.
const BOARD = chrome.runtime.getURL('board.html');

async function ensureAlarm() {
  if (!(await chrome.alarms.get('tick'))) {
    await chrome.alarms.create('tick', { periodInMinutes: 0.5 });
  }
}
ensureAlarm();
chrome.runtime.onInstalled.addListener(ensureAlarm);
chrome.runtime.onStartup.addListener(ensureAlarm);

chrome.alarms.onAlarm.addListener((a) => {
  if (a.name !== 'tick') return;
  // Không có trang nào mở thì sendMessage báo lỗi "Receiving end does not exist" — bỏ qua
  chrome.runtime.sendMessage({ type: 'tick', at: Date.now() }).catch(() => {});
});

// Bấm biểu tượng extension → mở (hoặc chuyển tới) tab bảng giá.
// getContexts thấy được tab của chính extension mà không cần quyền "tabs".
async function openBoard() {
  const [ctx] = await chrome.runtime.getContexts({ contextTypes: ['TAB'], documentUrls: [BOARD] });
  if (ctx) {
    await chrome.tabs.update(ctx.tabId, { active: true });
    await chrome.windows.update(ctx.windowId, { focused: true });
  } else {
    await chrome.tabs.create({ url: BOARD, pinned: true });
  }
}
chrome.action.onClicked.addListener(openBoard);
