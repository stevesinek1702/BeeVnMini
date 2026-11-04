// Lấy dữ liệu: giá FireAnt (cần host_permissions — FireAnt không mở CORS), nến ngày VNDirect (máy chủ trả
// Access-Control-Allow-Origin: * nên gọi thẳng được, khỏi khai báo quyền → không hiện trong mục Site access).
import { histStats } from './lib/core.js';
import { INTRA_FEED_DAYS, INTRA_TFS, intradayCutoff, intradayStats } from './lib/tech.js';

export const QUOTES_URL = 'https://www.fireant.vn/api/Data/Markets/Quotes?symbols=';
export const HISTORY_URL = 'https://dchart-api.vndirect.com.vn/dchart/history?resolution=D';
export const INTRA_URL = 'https://dchart-api.vndirect.com.vn/dchart/history?resolution=';     // + 15 / 60 (phút)
// FireAnt cắt bớt kết quả khi hỏi quá nhiều mã một lần (400 mã chỉ về ~60%) → 100 mã/lượt.
const QUOTE_BATCH = 100, QUOTE_WORKERS = 4, HIST_WORKERS = 8;
// Chỉ giữ các trường bảng giá cần (cho nhẹ bộ nhớ)
const QUOTE_FIELDS = ['Symbol', 'Name', 'Exchange', 'PriceCurrent', 'PriceChange', 'PricePercentChange', 'TotalVolume',
  'TotalValue', 'TotalActiveBuyVolume', 'PriceAverage', 'Date', 'PriceHigh', 'PriceLow', 'PriceCeiling', 'PriceFloor',
  'BuyForeignQuantity', 'SellForeignQuantity', 'BuyForeignValue', 'SellForeignValue'];

async function getJson(url, accept = 'application/json', timeoutMs = 20000) {
  const ctl = new AbortController();
  const timer = setTimeout(() => ctl.abort(), timeoutMs);
  try {
    const res = await fetch(url, { headers: { Accept: accept }, cache: 'no-store', signal: ctl.signal });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const text = await res.text();
    try { return JSON.parse(text); } catch { return null; }
  } finally {
    clearTimeout(timer);
  }
}

// Chạy fn trên từng phần tử, tối đa `workers` việc cùng lúc
export async function pool(items, workers, fn) {
  const out = new Array(items.length);
  let next = 0;
  async function run() {
    while (next < items.length) {
      const i = next++;
      out[i] = await fn(items[i], i);
    }
  }
  await Promise.all(Array.from({ length: Math.min(workers, items.length) }, run));
  return out;
}

export async function fetchQuotes(symbols) {
  const batches = [];
  for (let i = 0; i < symbols.length; i += QUOTE_BATCH) batches.push(symbols.slice(i, i + QUOTE_BATCH));
  const parts = await pool(batches, QUOTE_WORKERS, async (b) => {
    try {
      const data = await getJson(QUOTES_URL + b.join(','));
      return Array.isArray(data) ? data : [];
    } catch {
      return null;
    }
  });
  if (parts.every((p) => p === null)) throw new Error('Không lấy được giá');
  return parts.filter(Boolean).flat().map((q) => Object.fromEntries(QUOTE_FIELDS.map((k) => [k, q[k] ?? null])));
}

// dchart trả 406 nếu hỏi đích danh application/json → Accept */*
export function barsUrl(symbol, days) {
  const to = Math.floor(Date.now() / 1000);
  return `${HISTORY_URL}&symbol=${symbol}&from=${to - days * 86400}&to=${to}`;
}

export async function fetchBars(symbol, days) {
  return getJson(barsUrl(symbol, days), '*/*', 30000);
}

// MA10/20/45 + KL trung bình 45 phiên cho các mã còn thiếu (~70 phiên gần nhất).
// Mã không có dữ liệu → {} để khỏi thử lại mãi; lỗi mạng → bỏ trống, lần sau thử lại.
export async function fetchAllHistory(symbols, today, done, onProgress) {
  done = { ...(done || {}) };
  const todo = symbols.filter((s) => !(s in done));
  let i = 0;
  const one = async (sym) => {
    try {
      done[sym] = histStats(await fetchBars(sym, 100), today) || {};
    } catch { /* lỗi mạng: thử lại 1 lượt ngay, còn lỗi thì để lần sau */ }
    if (++i % 50 === 0 && onProgress) onProgress(Object.keys(done).length / symbols.length);
  };
  await pool(todo, HIST_WORKERS, one);
  await pool(todo.filter((s) => !(s in done)), 4, one);
  return done;
}

// {mã: {khung: thống kê}} nến trong phiên cho các mã còn thiếu (~40 s cả thị trường): tải nến `feed` phút (15 / 60) rồi
// tính các khung `tfs` gộp từ loại nến đó, mỗi khung chỉ lấy nến đã chốt tới lúc nowMs. Mã ít nến → khung đó null;
// lỗi mạng → bỏ trống, lần sau thử lại. Xem fetch_all_intraday của core.py.
export async function fetchAllIntraday(symbols, nowMs, feed, tfs, done, onProgress) {
  done = { ...(done || {}) };
  const todo = symbols.filter((s) => !(s in done));
  const to = Math.floor(nowMs / 1000);
  const cuts = tfs.map((tf) => [tf, INTRA_TFS[tf][1], intradayCutoff(nowMs, INTRA_TFS[tf][1])]);
  let i = 0;
  const one = async (sym) => {
    try {
      const bars = await getJson(`${INTRA_URL}${feed}&symbol=${sym}&from=${to - INTRA_FEED_DAYS[feed] * 86400}&to=${to}`,
        '*/*', 30000);
      done[sym] = Object.fromEntries(cuts.map(([tf, minutes, cut]) =>
        [tf, intradayStats(bars, cut, minutes !== feed ? minutes : null)]));
    } catch { /* lỗi mạng: thử lại 1 lượt ngay, còn lỗi thì để lần sau */ }
    if (++i % 50 === 0 && onProgress) onProgress(Object.keys(done).length / symbols.length);
  };
  await pool(todo, HIST_WORKERS, one);
  await pool(todo.filter((s) => !(s in done)), 4, one);
  return done;
}
