"""
Bee.vn mini — cửa sổ bảng giá nhỏ, LUÔN NỔI trên mọi cửa sổ (kể cả khi chuyển app / tab).

  1 mã = 1 hàng; nhiều mã thì cửa sổ dài thêm lên trên, neo góc dưới-phải như chồng thông báo.
  Thu gọn: Mã CP + các cột đang lọc. Bấm vào bảng → đủ 11 cột như bảng giá Bee.vn.
  Kéo thanh trên cùng để dời chỗ. Chuột phải để mở menu.

Chạy bằng pythonw (không hiện cửa sổ đen). Tham số:
  --install    tạo biểu tượng ngoài Desktop + tự chạy khi bật máy, rồi mở chương trình
  --uninstall  xoá hai biểu tượng đó
"""
import ctypes
import json
import os
import queue
import socket
import subprocess
import sys
import threading
import time
import traceback
import tkinter as tk
from tkinter import messagebox, ttk

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import core  # noqa: E402
from symbols import SYMBOLS  # noqa: E402

APP_NAME = 'Bee.vn mini'
# BEEVN_DATA_DIR: chỉ để chạy thử mà không đụng cài đặt thật
DATA_DIR = os.environ.get('BEEVN_DATA_DIR') or os.path.join(os.environ.get('APPDATA', HERE), 'BeeVnMini')
CONFIG_PATH = os.path.join(DATA_DIR, 'config.json')
HIST_PATH = os.path.join(DATA_DIR, 'hist.json')
LOG_PATH = os.path.join(DATA_DIR, 'log.txt')
ICON_PATH = os.path.join(HERE, 'beevn.ico')
SINGLE_INSTANCE_PORT = 47651

ON_HOURS_SEC = 30
OFF_HOURS_SEC = 600
HIST_CHECK_SEC = 600
STALE_SEC = 120
MAX_ROWS = 25            # quá số này thì lăn chuột để xem tiếp
NEW_HIGHLIGHT_SEC = 6

DEFAULT_CONFIG = {
    'exchange': 'HSX',
    'filters': {},
    'sortColumn': 'value',
    'sortDirection': 'desc',
    'mode': 'compact',
    'anchor': None,       # [phải, dưới] của cửa sổ, tính bằng pixel màn hình
    'sound': True,
    'opacity': 1.0,
}

# Màu giống cửa sổ extension / web Bee.vn
BG, HEAD, LINE = '#141428', '#1c1c38', '#2a2a4a'
ALT, NEW_BG = '#191934', '#4a3b10'
TEXT, MUTED, ACCENT, GOLD = '#e6e6f0', '#8a8aa8', '#38bdf8', '#fbbf24'
TONE = {'up': '#22c55e', 'down': '#ef4444', 'flat': '#eab308', 'muted': MUTED, 'sym': ACCENT, '': TEXT}
FILTERED = '#f87171'

EXCHANGE_LABEL = {'HSX': 'HSX', 'HNX': 'HNX', 'UPCOM': 'UpCom', 'ALL': 'Cả 3 sàn'}
OP_LABEL = [('gt', 'Lớn hơn (>)'), ('lt', 'Nhỏ hơn (<)'), ('eq', 'Bằng (=)')]

FONT = ('Segoe UI', 10)
FONT_BOLD = ('Segoe UI', 10, 'bold')
FONT_SMALL = ('Segoe UI', 8)
FONT_HEAD = ('Segoe UI', 8, 'bold')


def log(msg):
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(LOG_PATH, 'a', encoding='utf-8') as f:
            f.write(time.strftime('[%Y-%m-%d %H:%M:%S] ') + msg + '\n')
    except OSError:
        pass


def load_json(path, default):
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def save_json(path, data):
    os.makedirs(DATA_DIR, exist_ok=True)
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)
    os.replace(tmp, path)


# ── Biểu tượng Desktop / tự chạy khi bật máy ────────────────────────────

def _pythonw():
    exe = sys.executable
    if exe.lower().endswith('python.exe'):
        exe = exe[:-10] + 'pythonw.exe'
    return exe


def _ps(script):
    return subprocess.run(['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', script],
                          capture_output=True, text=True, creationflags=0x08000000)


def shortcut_path(folder):
    r = _ps(f"[Environment]::GetFolderPath('{folder}')")
    return os.path.join(r.stdout.strip(), APP_NAME + '.lnk')


def make_shortcut(folder):
    lnk = shortcut_path(folder)
    script = (
        "$s=(New-Object -ComObject WScript.Shell).CreateShortcut('%s');"
        "$s.TargetPath='%s';$s.Arguments='\"%s\"';$s.WorkingDirectory='%s';"
        "$s.IconLocation='%s';$s.Description='Bảng giá mini Bee.vn';$s.Save()"
    ) % (lnk, _pythonw(), os.path.abspath(__file__), HERE, ICON_PATH)
    return _ps(script).returncode == 0


def remove_shortcut(folder):
    try:
        os.remove(shortcut_path(folder))
    except OSError:
        pass


def has_startup():
    return os.path.exists(shortcut_path('Startup'))


# ── Màn hình ────────────────────────────────────────────────────────────

def work_area():
    """Vùng màn hình chính trừ thanh taskbar: (trái, trên, phải, dưới)."""
    class RECT(ctypes.Structure):
        _fields_ = [('l', ctypes.c_long), ('t', ctypes.c_long), ('r', ctypes.c_long), ('b', ctypes.c_long)]
    rc = RECT()
    ctypes.windll.user32.SystemParametersInfoW(0x30, 0, ctypes.byref(rc), 0)
    return rc.l, rc.t, rc.r, rc.b


def virtual_screen():
    """Khung bao tất cả màn hình (nhiều màn hình): (trái, trên, phải, dưới)."""
    gm = ctypes.windll.user32.GetSystemMetrics
    x, y = gm(76), gm(77)
    return x, y, x + gm(78), y + gm(79)


# ── Ứng dụng ────────────────────────────────────────────────────────────

class App:
    def __init__(self, root):
        self.root = root
        self.cfg = {**DEFAULT_CONFIG, **load_json(CONFIG_PATH, {})}
        self.hist = load_json(HIST_PATH, {})
        self.quotes = None
        self.fetched_at = None
        self.error = None
        self.hist_progress = 1.0 if self.hist.get('day') == core.vn_date(time.time()) else 0.0
        self.stat_note = None   # lý do không dùng được FireAnt cho cột MA (vd cookie hết hạn)
        self.prev_symbols = None
        self.prev_key = None
        self.new_until = {}
        self.matches = []
        self.offset = 0
        self.q = queue.Queue()
        self.wake = threading.Event()
        self.drag = None
        self.settings_win = None

        root.overrideredirect(True)            # không viền, không nút taskbar — như một thông báo
        root.attributes('-topmost', True)       # luôn nổi trên mọi cửa sổ
        root.attributes('-alpha', self.cfg.get('opacity', 1.0))
        root.configure(bg=LINE)

        self.frame = tk.Frame(root, bg=BG)
        self.frame.pack(padx=1, pady=1)          # viền 1px màu LINE
        self._build_header()
        self.filters_lbl = tk.Label(self.frame, bg=BG, fg=MUTED, font=FONT_SMALL, anchor='w')
        self.table = tk.Frame(self.frame, bg=BG)
        self.table.pack(fill='x')
        self.msg = tk.Label(self.frame, bg=BG, fg=MUTED, font=('Segoe UI', 9), justify='left',
                            anchor='w', wraplength=300)
        self.msg.pack(fill='x', padx=8, pady=(0, 6))
        self.more_lbl = tk.Label(self.frame, bg=BG, fg=MUTED, font=FONT_SMALL)

        self._build_menu()
        for w in (self.frame, self.table):
            w.bind('<MouseWheel>', self.on_wheel)
            w.bind('<Button-3>', self.show_menu)

        self.hide_from_taskbar()
        self.render()
        threading.Thread(target=self.quote_loop, daemon=True).start()
        threading.Thread(target=self.hist_loop, daemon=True).start()
        root.after(200, self.poll_queue)
        root.after(5000, self.keep_on_top)
        root.after(15000, self.tick)

    # ── Giao diện ──
    def _build_header(self):
        h = tk.Frame(self.frame, bg=HEAD)
        h.pack(fill='x')
        title = tk.Frame(h, bg=HEAD)
        title.pack(side='left', padx=(8, 4), pady=3)
        tk.Label(title, text='Bee', bg=HEAD, fg=GOLD, font=FONT_BOLD, bd=0, padx=0).pack(side='left')
        tk.Label(title, text='.vn', bg=HEAD, fg=TEXT, font=FONT, bd=0, padx=0).pack(side='left')
        self.meta = tk.Label(h, bg=HEAD, fg=MUTED, font=('Segoe UI', 9))
        self.meta.pack(side='left', padx=(4, 10))

        buttons = [('✕', 'Tắt chương trình', self.quit),
                   ('⚙', 'Cài đặt bộ lọc', self.open_settings),
                   ('⤢', 'Thu gọn / đầy đủ', self.toggle_mode),
                   ('↻', 'Tải lại ngay', self.refresh_now)]
        for text, tip, cmd in buttons:
            b = tk.Label(h, text=text, bg=HEAD, fg=MUTED, font=('Segoe UI Symbol', 10), cursor='hand2', padx=4)
            b.pack(side='right')
            b.bind('<Button-1>', lambda e, c=cmd: c())
            b.bind('<Enter>', lambda e, w=b: w.config(fg=TEXT))
            b.bind('<Leave>', lambda e, w=b: w.config(fg=MUTED))

        # Kéo thanh trên cùng để dời cửa sổ
        for w in (h, title, self.meta) + tuple(title.winfo_children()):
            w.bind('<ButtonPress-1>', self.drag_start)
            w.bind('<B1-Motion>', self.drag_move)
            w.bind('<ButtonRelease-1>', self.drag_end)
            w.bind('<Button-3>', self.show_menu)
            w.config(cursor='fleur')

    def _build_menu(self):
        m = tk.Menu(self.root, tearoff=0)
        m.add_command(label='Thu gọn / đầy đủ', command=self.toggle_mode)
        m.add_command(label='Tải lại ngay', command=self.refresh_now)
        m.add_command(label='Cài đặt bộ lọc…', command=self.open_settings)
        m.add_command(label='Về góc dưới-phải màn hình', command=self.reset_position)
        m.add_separator()
        # Đổi sàn nhanh, khỏi mở Cài đặt
        self.exchange_var = tk.StringVar(value=self.cfg['exchange'])
        for key in ('HSX', 'HNX', 'UPCOM', 'ALL'):
            m.add_radiobutton(label='Sàn: ' + EXCHANGE_LABEL[key], value=key, variable=self.exchange_var,
                              command=lambda k=key: self.apply_settings({'exchange': k}))
        m.add_separator()
        m.add_command(label='Tắt chương trình', command=self.quit)
        self.menu = m

    def hide_from_taskbar(self):
        """Kiểu cửa sổ công cụ: không có nút dưới taskbar, không hiện trong Alt+Tab."""
        try:
            self.root.update_idletasks()
            u = ctypes.windll.user32
            hwnd = u.GetParent(self.root.winfo_id()) or self.root.winfo_id()
            style = u.GetWindowLongW(hwnd, -20)                       # GWL_EXSTYLE
            u.SetWindowLongW(hwnd, -20, (style | 0x80) & ~0x40000)     # +TOOLWINDOW, -APPWINDOW
        except Exception:
            log('taskbar: ' + traceback.format_exc())

    def show_menu(self, e):
        self.menu.tk_popup(e.x_root, e.y_root)

    def config_key(self):
        c = self.cfg
        return json.dumps([c['exchange'], c['filters'], c['sortColumn'], c['sortDirection']], sort_keys=True)

    def compute(self):
        """Lọc lại từ giá mới nhất + lịch sử; đánh dấu mã mới lọt lọc."""
        if self.quotes is None:
            return
        data = self.hist.get('data', {})
        rows = [core.transform_quote(q, data.get(q.get('Symbol'))) for q in self.quotes]
        all_stocks = core.group_by_exchange(rows)
        has_filter = bool(core.active_filter_keys(self.cfg['filters']))
        self.matches = core.select_matches(all_stocks, self.cfg) if has_filter else []

        key = self.config_key()
        syms = {s['symbol'] for s in self.matches}
        if has_filter and self.prev_symbols is not None and self.prev_key == key:
            fresh = syms - self.prev_symbols
            if fresh:
                until = time.time() + NEW_HIGHLIGHT_SEC
                for s in fresh:
                    self.new_until[s] = until
                if self.cfg.get('sound'):
                    try:
                        import winsound
                        winsound.MessageBeep(0x40)
                    except Exception:
                        pass
                self.root.after(int(NEW_HIGHLIGHT_SEC * 1000) + 100, self.render)
        self.prev_symbols, self.prev_key = syms, key

    def render(self):
        cfg = self.cfg
        filters = cfg['filters']
        has_filter = bool(core.active_filter_keys(filters))
        full = cfg['mode'] == 'full'

        # Dòng trạng thái: sàn · số mã · giờ cập nhật
        parts = [EXCHANGE_LABEL.get(cfg['exchange'], cfg['exchange'])]
        if has_filter and self.quotes is not None:
            parts.append(f'{len(self.matches)} mã')
        if self.fetched_at:
            parts.append(time.strftime('%H:%M:%S', time.localtime(self.fetched_at)))
        stale = self.error or (self.fetched_at and core.is_trading_time()
                               and time.time() - self.fetched_at > STALE_SEC)
        self.meta.config(text=' · '.join(parts), fg='#eab308' if stale else MUTED)

        # Dòng bộ lọc (chỉ ở chế độ đầy đủ)
        if full and has_filter:
            if self.hist_progress < 1:
                src = f'đang tính MA {int(self.hist_progress * 100)}%'
            elif self.hist.get('source') == 'fireant':
                src = 'MA: FireAnt'
            else:
                src = 'MA: tự tính từ VNDirect' + (f' ({self.stat_note})' if self.stat_note else '')
            self.filters_lbl.config(text=core.describe_filters(filters) + '   ·   ' + src)
            self.filters_lbl.pack(fill='x', padx=8, pady=(3, 1), after=self.frame.winfo_children()[0])
        else:
            self.filters_lbl.pack_forget()

        # Bảng
        for w in self.table.winfo_children():
            w.destroy()
        rows = self.matches if has_filter else []
        self.offset = max(0, min(self.offset, max(0, len(rows) - MAX_ROWS)))
        visible = rows[self.offset:self.offset + MAX_ROWS]
        if visible:
            cols = core.table_columns(cfg, full)
            active = set(core.active_filter_keys(filters))
            for ci, (key, label) in enumerate(cols):
                txt = label.upper() + (' •' if key in active else '')
                lbl = tk.Label(self.table, text=txt, bg=BG, fg=FILTERED if key in active else MUTED,
                               font=FONT_HEAD, anchor='w' if ci == 0 else 'e', padx=8)
                lbl.grid(row=0, column=ci, sticky='ew', pady=(3, 2))
                self._bind_table(lbl)
            now = time.time()
            for ri, s in enumerate(visible, 1):
                bg = NEW_BG if self.new_until.get(s['symbol'], 0) > now else (ALT if ri % 2 == 0 else BG)
                for ci, (key, _) in enumerate(cols):
                    text, tone = core.format_cell(s, key)
                    lbl = tk.Label(self.table, text=text, bg=bg, fg=TONE.get(tone, TEXT),
                                   font=FONT_BOLD if key == 'symbol' else FONT,
                                   anchor='w' if ci == 0 else 'e', padx=8)
                    lbl.grid(row=ri, column=ci, sticky='ew')
                    self._bind_table(lbl)
            tk.Frame(self.table, bg=BG, height=4).grid(row=len(visible) + 1, column=0)
            # Cột cuối giãn ra cho kín bề ngang khi thanh tiêu đề rộng hơn bảng
            for ci in range(len(core.COLUMNS)):
                self.table.grid_columnconfigure(ci, weight=1 if ci == len(cols) - 1 else 0)
        hidden = len(rows) - len(visible)
        if hidden > 0:
            self.more_lbl.config(text=f'lăn chuột để xem thêm {hidden} mã')
            self.more_lbl.pack(after=self.table, pady=(0, 3))
        else:
            self.more_lbl.pack_forget()

        # Thông điệp
        if self.quotes is None and not self.error:
            msg, color = 'Đang tải giá…', MUTED
        elif self.error and self.quotes is None:
            msg, color = f'{self.error}. Sẽ tự thử lại — kiểm tra mạng Internet.', '#fca5a5'
        elif not has_filter:
            msg, color = 'Chưa có bộ lọc. Bấm ⚙ để đặt lọc\n(vd Giá < 20, % Thay đổi > 2).', MUTED
        elif not rows:
            msg, color = 'Chưa có mã nào khớp bộ lọc.', MUTED
        else:
            msg, color = '', MUTED
        self.msg.config(text=msg, fg=color)
        if msg:
            self.msg.pack(fill='x', padx=8, pady=(4, 6))
        else:
            self.msg.pack_forget()

        self.fit()

    def _bind_table(self, w):
        w.bind('<Button-1>', lambda e: self.toggle_mode())
        w.bind('<MouseWheel>', self.on_wheel)
        w.bind('<Button-3>', self.show_menu)
        w.config(cursor='hand2')

    def fit(self):
        """Co giãn vừa nội dung, giữ nguyên góc dưới-phải (hàng mới mọc lên trên)."""
        self.root.update_idletasks()
        w = max(self.root.winfo_reqwidth(), 240)
        h = self.root.winfo_reqheight()
        anchor = self.cfg.get('anchor')
        vl, vt, vr, vb = virtual_screen()
        if anchor:
            right, bottom = anchor
        else:
            _, _, right, bottom = work_area()
            right, bottom = right - 12, bottom - 12
        right = min(max(right, vl + w), vr)
        bottom = min(max(bottom, vt + h), vb)
        self.root.geometry(f'{w}x{h}+{int(right - w)}+{int(bottom - h)}')

    # ── Tương tác ──
    def toggle_mode(self):
        self.cfg['mode'] = 'compact' if self.cfg['mode'] == 'full' else 'full'
        save_json(CONFIG_PATH, self.cfg)
        self.render()

    def on_wheel(self, e):
        if len(self.matches) <= MAX_ROWS:
            return
        self.offset += -3 if e.delta > 0 else 3
        self.render()

    def drag_start(self, e):
        self.drag = (e.x_root - self.root.winfo_x(), e.y_root - self.root.winfo_y())

    def drag_move(self, e):
        if self.drag:
            self.root.geometry(f'+{e.x_root - self.drag[0]}+{e.y_root - self.drag[1]}')

    def drag_end(self, e):
        if self.drag:
            self.drag = None
            self.cfg['anchor'] = [self.root.winfo_x() + self.root.winfo_width(),
                                  self.root.winfo_y() + self.root.winfo_height()]
            save_json(CONFIG_PATH, self.cfg)

    def reset_position(self):
        self.cfg['anchor'] = None
        save_json(CONFIG_PATH, self.cfg)
        self.fit()

    def refresh_now(self):
        self.meta.config(text='đang tải…')
        self.wake.set()

    def keep_on_top(self):
        # Vài thao tác của Windows (bấm taskbar, mở app toàn màn hình rồi thoát) làm cửa sổ tụt xuống.
        try:
            if not (self.settings_win and self.settings_win.winfo_exists()):   # đang mở Cài đặt thì nhường
                self.root.attributes('-topmost', True)
                self.root.lift()
        finally:
            self.root.after(5000, self.keep_on_top)

    def tick(self):
        # Cập nhật màu "số cũ" khi lâu không có giá mới (vd mất mạng)
        self.render()
        self.root.after(15000, self.tick)

    def quit(self):
        if messagebox.askyesno(APP_NAME, 'Tắt bảng giá mini?\n\nMở lại bằng biểu tượng "Bee.vn mini" ngoài Desktop.',
                               parent=self.root):
            self.root.destroy()

    # ── Cài đặt ──
    def open_settings(self):
        if self.settings_win and self.settings_win.winfo_exists():
            self.settings_win.lift()
            return
        SettingsWindow(self)

    def apply_settings(self, new_cfg):
        self.cfg.update(new_cfg)
        self.exchange_var.set(self.cfg['exchange'])
        self.root.attributes('-alpha', self.cfg.get('opacity', 1.0))
        save_json(CONFIG_PATH, self.cfg)
        self.offset = 0
        self.compute()
        self.render()

    # ── Lấy dữ liệu (luồng nền) ──
    def quote_loop(self):
        while True:
            try:
                quotes = core.fetch_quotes(SYMBOLS)
                slim = [{k: q.get(k) for k in ('Symbol', 'Name', 'Exchange', 'PriceCurrent', 'PriceChange',
                                               'PricePercentChange', 'TotalVolume', 'TotalValue',
                                               'TotalActiveBuyVolume', 'PriceAverage')} for q in quotes]
                self.q.put(('quotes', time.time(), slim))
            except Exception as e:
                log('quotes: ' + repr(e))
                self.q.put(('error', str(e)))
            self.wake.wait(ON_HOURS_SEC if core.is_trading_time() else OFF_HOURS_SEC)
            self.wake.clear()

    def hist_loop(self):
        """MA + KL trung bình: ưu tiên FireAnt (cookie ô D2), hết hạn thì tự tính từ VNDirect."""
        while True:
            try:
                today = core.vn_date(time.time())
                hist = self.hist if self.hist.get('day') == today else {'day': today, 'data': {}}
                if hist.get('source') != 'fireant':
                    try:
                        cookie = core.fetch_fireant_cookie(self.cfg.get('cookieSheetId') or core.COOKIE_SHEET_ID)
                        if not cookie:
                            raise core.CookieExpired('ô D2 trống')
                        hist = {'day': today, 'data': core.fetch_trading_stats(cookie), 'source': 'fireant'}
                        save_json(HIST_PATH, hist)
                        self.q.put(('hist', hist, None))
                    except core.CookieExpired as e:
                        log('cookie FireAnt: ' + str(e))
                        self.q.put(('stat_note', 'cookie FireAnt hết hạn'))
                    except Exception as e:
                        log('cookie FireAnt: ' + repr(e))
                        self.q.put(('stat_note', 'không đọc được cookie FireAnt'))
                if hist.get('source') != 'fireant' and len(hist['data']) < len(SYMBOLS):
                    data = core.fetch_all_history(
                        SYMBOLS, today, hist['data'],
                        on_progress=lambda p: self.q.put(('hist_progress', p)))
                    hist = {'day': today, 'data': data, 'source': 'vndirect'}
                    save_json(HIST_PATH, hist)
                    self.q.put(('hist', hist, len(data) / len(SYMBOLS)))
            except Exception:
                log('hist: ' + traceback.format_exc())
            time.sleep(HIST_CHECK_SEC)

    def poll_queue(self):
        changed = False
        try:
            while True:
                kind, *payload = self.q.get_nowait()
                if kind == 'quotes':
                    self.fetched_at, self.quotes = payload
                    self.error = None
                    self.compute()
                elif kind == 'error':
                    self.error = payload[0]
                elif kind == 'hist':
                    self.hist, progress = payload
                    self.hist_progress = 1.0 if progress is None else progress
                    if self.hist.get('source') == 'fireant':
                        self.stat_note = None
                    self.compute()
                elif kind == 'stat_note':
                    self.stat_note = payload[0]
                elif kind == 'hist_progress':
                    self.hist_progress = payload[0]
                    if self.cfg['mode'] != 'full':
                        continue
                changed = True
        except queue.Empty:
            pass
        if changed:
            self.render()
        self.root.after(300, self.poll_queue)


class SettingsWindow:
    def __init__(self, app):
        self.app = app
        cfg = app.cfg
        w = self.win = tk.Toplevel(app.root)
        app.settings_win = w
        w.title('Bee.vn mini — Cài đặt')
        w.transient(app.root)     # cửa sổ con: Windows luôn đặt nó TRÊN bảng giá mini
        w.attributes('-topmost', True)
        w.resizable(False, False)
        try:
            w.iconbitmap(ICON_PATH)
        except tk.TclError:
            pass
        body = ttk.Frame(w, padding=14)
        body.pack(fill='both')

        ttk.Label(body, text='Bộ lọc', font=('Segoe UI', 11, 'bold')).grid(row=0, column=0, columnspan=3, sticky='w')
        ttk.Label(body, text='Để trống ô giá trị = không lọc cột đó. Giá tính bằng nghìn đồng (14.2 = 14.200đ),\n'
                             'KLGD bằng cổ phiếu (1000000 = 1 triệu CP), GTGD bằng tỷ đồng.',
                  foreground='#666').grid(row=1, column=0, columnspan=3, sticky='w', pady=(2, 8))

        ttk.Label(body, text='Sàn').grid(row=2, column=0, sticky='w', pady=2)
        self.exchange = ttk.Combobox(body, state='readonly', width=16,
                                     values=[EXCHANGE_LABEL[k] for k in ('HSX', 'HNX', 'UPCOM', 'ALL')])
        self.exchange.set(EXCHANGE_LABEL.get(cfg['exchange'], 'HSX'))
        self.exchange.grid(row=2, column=1, sticky='w', pady=2)

        self.rows = {}
        op_names = [n for _, n in OP_LABEL]
        for i, (key, label) in enumerate(core.FILTERABLE, start=3):
            f = cfg['filters'].get(key) or {}
            ttk.Label(body, text=label).grid(row=i, column=0, sticky='w', pady=2)
            op = ttk.Combobox(body, state='readonly', width=16, values=op_names)
            op.set(dict(OP_LABEL).get(f.get('operator', 'gt'), op_names[0]))
            op.grid(row=i, column=1, sticky='w', padx=(0, 8), pady=2)
            val = ttk.Entry(body, width=14)
            if f.get('value') not in (None, ''):
                val.insert(0, core.js_num(f['value']))
            val.grid(row=i, column=2, sticky='w', pady=2)
            self.rows[key] = (op, val)

        r = 3 + len(core.FILTERABLE)
        ttk.Separator(body).grid(row=r, column=0, columnspan=3, sticky='ew', pady=10)
        ttk.Label(body, text='Sắp xếp theo').grid(row=r + 1, column=0, sticky='w', pady=2)
        self.sort_col = ttk.Combobox(body, state='readonly', width=16, values=[l for _, l in core.COLUMNS])
        self.sort_col.set(core.LABEL.get(cfg['sortColumn'], 'GTGD'))
        self.sort_col.grid(row=r + 1, column=1, sticky='w', pady=2)
        self.sort_dir = ttk.Combobox(body, state='readonly', width=12, values=['Giảm dần', 'Tăng dần'])
        self.sort_dir.set('Tăng dần' if cfg['sortDirection'] == 'asc' else 'Giảm dần')
        self.sort_dir.grid(row=r + 1, column=2, sticky='w', pady=2)

        ttk.Label(body, text='Độ trong suốt').grid(row=r + 2, column=0, sticky='w', pady=2)
        self.opacity = tk.DoubleVar(value=cfg.get('opacity', 1.0))
        ttk.Scale(body, from_=0.5, to=1.0, variable=self.opacity, length=150).grid(row=r + 2, column=1, sticky='w')

        self.sound = tk.BooleanVar(value=cfg.get('sound', True))
        ttk.Checkbutton(body, text='Kêu "ting" khi có mã mới lọt vào bộ lọc', variable=self.sound) \
            .grid(row=r + 3, column=0, columnspan=3, sticky='w', pady=(8, 2))
        self.startup = tk.BooleanVar(value=has_startup())
        ttk.Checkbutton(body, text='Tự mở khi bật máy', variable=self.startup) \
            .grid(row=r + 4, column=0, columnspan=3, sticky='w', pady=2)

        btns = ttk.Frame(body)
        btns.grid(row=r + 5, column=0, columnspan=3, sticky='e', pady=(12, 0))
        ttk.Button(btns, text='Đóng', command=w.destroy).pack(side='right')
        ttk.Button(btns, text='Lưu', command=self.save).pack(side='right', padx=6)
        self.saved = ttk.Label(btns, text='', foreground='#16a34a')
        self.saved.pack(side='right', padx=8)

        # Giữa màn hình chính, nổi trên cả bảng giá mini
        w.update_idletasks()
        l, t, r, b = work_area()
        w.geometry(f'+{l + (r - l - w.winfo_width()) // 2}+{t + max(0, (b - t - w.winfo_height()) // 2 - 20)}')
        # Hai cửa sổ cùng "luôn nổi" thì Windows không chắc để cái nào trên → tạm hạ bảng giá mini
        # xuống trong lúc mở Cài đặt, đóng Cài đặt thì nổi lại.
        app.root.attributes('-topmost', False)
        w.bind('<Destroy>', lambda e: e.widget is w and app.root.attributes('-topmost', True))
        w.after(100, lambda: (w.lift(), w.focus_force()))

    def save(self):
        name_to_op = {n: k for k, n in OP_LABEL}
        filters, bad = {}, []
        for key, (op, val) in self.rows.items():
            raw = val.get().strip().replace(',', '.')
            if not raw:
                continue
            try:
                filters[key] = {'operator': name_to_op[op.get()], 'value': float(raw)}
            except ValueError:
                bad.append(core.LABEL[key])
        if bad:
            messagebox.showwarning(APP_NAME, 'Giá trị không phải số: ' + ', '.join(bad), parent=self.win)
            return
        label_to_ex = {v: k for k, v in EXCHANGE_LABEL.items()}
        label_to_col = {l: k for k, l in core.COLUMNS}
        self.app.apply_settings({
            'exchange': label_to_ex.get(self.exchange.get(), 'HSX'),
            'filters': filters,
            'sortColumn': label_to_col.get(self.sort_col.get(), 'value'),
            'sortDirection': 'asc' if self.sort_dir.get() == 'Tăng dần' else 'desc',
            'sound': self.sound.get(),
            'opacity': round(self.opacity.get(), 2),
        })
        if self.startup.get() != has_startup():
            if self.startup.get():
                make_shortcut('Startup')
            else:
                remove_shortcut('Startup')
        self.saved.config(text='✓ Đã lưu')
        self.win.after(1500, lambda: self.saved.winfo_exists() and self.saved.config(text=''))


def main():
    # Chữ nét trên màn hình độ phân giải cao
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    if '--uninstall' in sys.argv:
        remove_shortcut('Desktop')
        remove_shortcut('Startup')
        r = tk.Tk()
        r.withdraw()
        messagebox.showinfo(APP_NAME, 'Đã xoá biểu tượng ngoài Desktop và tự chạy khi bật máy.\n'
                                      'Nếu bảng giá mini đang mở, bấm ✕ trên nó để tắt.')
        return

    if '--install' in sys.argv:
        ok = make_shortcut('Desktop') & make_shortcut('Startup')
        r = tk.Tk()
        r.withdraw()
        messagebox.showinfo(APP_NAME, 'Đã cài xong.\n\n• Biểu tượng "Bee.vn mini" ở ngoài Desktop.\n'
                                      '• Tự mở mỗi khi bật máy.\n\nBảng giá mini sẽ hiện ở góc dưới-phải màn hình.'
                            if ok else 'Không tạo được biểu tượng — xem log ở ' + LOG_PATH)
        r.destroy()

    # Chỉ chạy một bản: bản thứ hai (bấm biểu tượng lần nữa) tự thoát.
    lock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        lock.bind(('127.0.0.1', SINGLE_INSTANCE_PORT))
    except OSError:
        return

    root = tk.Tk()
    root.title(APP_NAME)
    try:
        root.iconbitmap(ICON_PATH)
    except tk.TclError:
        pass
    root.report_callback_exception = lambda *a: log('ui: ' + ''.join(traceback.format_exception(*a)))
    App(root)
    root.mainloop()


if __name__ == '__main__':
    try:
        main()
    except Exception:
        log('fatal: ' + traceback.format_exc())
        raise
