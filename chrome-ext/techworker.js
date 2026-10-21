// Luồng phụ (Web Worker): tải nến ~600 ngày cả thị trường và tính chỉ báo kỹ thuật + trendline (kể cả quét lùi
// phiên vượt trendline giảm, ~vài chục giây CPU) — để trang bảng giá không bị đơ trong lúc tính.
import { statsFromBars } from './lib/tech.js';
import { vnDate } from './lib/core.js';
import { pool, fetchBars } from './data.js';

const TECH_DAYS = 600;      // ~410 phiên: đủ cho SMA/EMA 200 và EMA kịp 'quên' giá mồi đầu chuỗi
const TECH_WORKERS = 8;

self.onmessage = async (e) => {
  const { job, symbols, today, history } = e.data;
  const done = { ...(e.data.done || {}) };
  const todo = symbols.filter((s) => !(s in done));
  let i = 0;
  const one = async (sym) => {
    try {
      done[sym] = statsFromBars(await fetchBars(sym, TECH_DAYS), today, vnDate, history) || {};
    } catch { /* lỗi mạng: thử lại 1 lượt ngay, còn lỗi thì để lần sau */ }
    if (++i % 50 === 0) self.postMessage({ job, progress: Object.keys(done).length / symbols.length });
  };
  await pool(todo, TECH_WORKERS, one);
  await pool(todo.filter((s) => !(s in done)), 4, one);
  self.postMessage({ job, data: done });
};
