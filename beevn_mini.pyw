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
import urllib.request
import tkinter as tk
from tkinter import messagebox, ttk

# Chạy dạng .exe (PyInstaller) thì file đi kèm (icon) nằm trong thư mục giải nén tạm _MEIPASS
FROZEN = getattr(sys, 'frozen', False)
HERE = os.path.dirname(sys.executable if FROZEN else os.path.abspath(__file__))
RES_DIR = getattr(sys, '_MEIPASS', HERE)
sys.path.insert(0, HERE)

import core  # noqa: E402
from symbols import SYMBOLS  # noqa: E402

APP_NAME = 'Bee.vn mini'
# Tăng số này mỗi lần phát hành bản mới (tools/release.py đọc nó). BEEVN_FAKE_VERSION chỉ để thử cập nhật.
APP_VERSION = os.environ.get('BEEVN_FAKE_VERSION') or '1.2.0'
# Bản mới nhất: nhánh "release" của kho GitHub công khai stevesinek1702/BeeVnMini
UPDATE_URL = (os.environ.get('BEEVN_UPDATE_URL')     # chỉ để chạy thử
              or 'https://raw.githubusercontent.com/stevesinek1702/BeeVnMini/release/latest.json')
UPDATE_CHECK_SEC = 6 * 3600
# BEEVN_DATA_DIR: chỉ để chạy thử mà không đụng cài đặt thật
DATA_DIR = os.environ.get('BEEVN_DATA_DIR') or os.path.join(os.environ.get('APPDATA', HERE), 'BeeVnMini')
CONFIG_PATH = os.path.join(DATA_DIR, 'config.json')
HIST_PATH = os.path.join(DATA_DIR, 'hist.json')
LOG_PATH = os.path.join(DATA_DIR, 'log.txt')
ICON_PATH = os.path.join(RES_DIR, 'beevn.ico')
SPEAK_PS = os.path.join(RES_DIR, 'speak.ps1')
# Bản .exe cài vào đây (copy từ file người dùng tải về); biểu tượng Desktop / tự chạy trỏ vào đây
INSTALL_DIR = os.path.join(os.environ.get('LOCALAPPDATA', HERE), 'BeeVnMini')
INSTALLED_EXE = os.path.join(INSTALL_DIR, 'BeeVnMini.exe')
SINGLE_INSTANCE_PORT = 47651

ALERT_LABEL = [('speak', 'Đọc tên mã'), ('beep', 'Kêu "ting"'), ('off', 'Im lặng')]

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
    'alert': 'speak',     # có mã mới lọt lọc: 'speak' đọc tên mã | 'beep' kêu ting | 'off' im lặng
    'opacity': 1.0,
    # Google Sheet có cookie FireAnt ở ô D2 sheet Dashboard. Anh Si cho mọi người dùng chung sheet này
    # (14/10/2026); xoá trống trong Cài đặt thì máy đó thôi dùng FireAnt, tự tính MA từ VNDirect.
    'cookieSheetId': '1IaSyUm5opJttxGgJa_4ucDSWEzEJQYaTFVTwYtBiH9c',
    'askedInstall': False,
}

# Màu giống cửa sổ extension / web Bee.vn
BG, HEAD, LINE = '#141428', '#1c1c38', '#2a2a4a'
ALT, NEW_BG = '#191934', '#4a3b10'
TEXT, MUTED, ACCENT, GOLD = '#e6e6f0', '#8a8aa8', '#38bdf8', '#fbbf24'
TONE = {'up': '#22c55e', 'down': '#ef4444', 'flat': '#eab308', 'muted': MUTED, 'sym': ACCENT, '': TEXT}
FILTERED = '#f87171'
SECTION = '#22224a'     # nền dòng tên tiêu chí

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
    if os.environ.get('BEEVN_SHORTCUT_DIR'):      # chỉ để chạy thử, khỏi đụng Desktop thật
        return os.path.join(os.environ['BEEVN_SHORTCUT_DIR'], folder, APP_NAME + '.lnk')
    r = _ps(f"[Environment]::GetFolderPath('{folder}')")
    return os.path.join(r.stdout.strip(), APP_NAME + '.lnk')


def launch_target():
    """(chương trình, tham số, thư mục, icon) cho biểu tượng Desktop / tự chạy."""
    if FROZEN:
        exe = INSTALLED_EXE if os.path.exists(INSTALLED_EXE) else sys.executable
        return exe, '', os.path.dirname(exe), exe
    return _pythonw(), '"%s"' % os.path.abspath(__file__), HERE, ICON_PATH


def make_shortcut(folder):
    lnk = shortcut_path(folder)
    target, args, workdir, icon = launch_target()

    def q(v):
        return v.replace("'", "''")
    script = (
        "$s=(New-Object -ComObject WScript.Shell).CreateShortcut('%s');"
        "$s.TargetPath='%s';$s.Arguments='%s';$s.WorkingDirectory='%s';"
        "$s.IconLocation='%s';$s.Description='Bảng giá mini Bee.vn';$s.Save()"
    ) % (q(lnk), q(target), q(args), q(workdir), q(icon))
    r = _ps(script)
    if r.returncode != 0:
        log('shortcut: ' + r.stderr)
    return r.returncode == 0


def remove_shortcut(folder):
    try:
        os.remove(shortcut_path(folder))
    except OSError:
        pass


SHORTCUT_FOLDERS = ('Desktop', 'Startup', 'Programs')   # Programs = menu Start


def make_all_shortcuts():
    ok = True
    for f in SHORTCUT_FOLDERS:
        ok &= make_shortcut(f)
    return ok


def remove_all_shortcuts():
    for f in SHORTCUT_FOLDERS:
        remove_shortcut(f)


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
    def __init__(self, root, lock=None):
        self.root = root
        saved = load_json(CONFIG_PATH, {})
        self.cfg = {**DEFAULT_CONFIG, **saved}
        if 'alert' not in saved and saved.get('sound') is False:   # cài đặt cũ: đã tắt tiếng
            self.cfg['alert'] = 'off'
        # Nhiều tiêu chí lọc; cài đặt cũ (1 bộ lọc) tự thành "Tiêu chí 1"
        self.cfg['criteria'] = core.criteria_from_config(self.cfg)
        self.speaker = None          # tiến trình đang đọc to
        self.pending_say = []        # mã mới đến lúc đang đọc dở → đọc tiếp sau
        self.hist = load_json(HIST_PATH, {})
        self.quotes = None
        self.fetched_at = None
        self.error = None
        self.hist_progress = 1.0 if self.hist.get('day') == core.vn_date(time.time()) else 0.0
        self.stat_note = None   # lý do không dùng được FireAnt cho cột MA (vd cookie hết hạn)
        self.prev_by_key = None      # {khoá tiêu chí: tập mã lượt trước} — để biết mã nào MỚI lọt lọc
        self.new_until = {}
        self.sections = []           # [(tiêu chí, [mã khớp])] — chỉ tiêu chí đã có điều kiện
        self.matches = []            # gộp mọi khối, không trùng mã
        self.offset = 0
        self.q = queue.Queue()
        self.wake = threading.Event()
        self.wake_hist = threading.Event()
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
        self.update_info = None
        if FROZEN:            # chỉ bản .exe tự cập nhật; bản chạy từ mã nguồn thì cập nhật bằng git
            threading.Thread(target=self.update_loop, daemon=True).start()
        if lock is not None:
            threading.Thread(target=self.listen_loop, args=(lock,), daemon=True).start()
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
            if text == '↻':
                self.refresh_btn = b
            b.pack(side='right')
            b.bind('<Button-1>', lambda e, c=cmd: c())
            b.bind('<Enter>', lambda e, w=b: w.config(fg=TEXT))
            b.bind('<Leave>', lambda e, w=b: w.config(fg=MUTED))

        # Có bản mới → hiện nút ⬆ vàng bên trái các nút
        self.update_btn = tk.Label(h, text='⬆ Cập nhật', bg=GOLD, fg=HEAD, font=('Segoe UI', 8, 'bold'),
                                   cursor='hand2', padx=5)
        self.update_btn.bind('<Button-1>', lambda e: self.do_update())

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
        crits = self.cfg['criteria']
        if len(crits) == 1:
            # Đổi sàn nhanh, khỏi mở Cài đặt (nhiều tiêu chí thì mỗi cái một sàn → đổi trong Cài đặt)
            self.exchange_var = tk.StringVar(value=crits[0]['exchange'])
            for key in ('HSX', 'HNX', 'UPCOM', 'ALL'):
                m.add_radiobutton(label='Sàn: ' + EXCHANGE_LABEL[key], value=key, variable=self.exchange_var,
                                  command=lambda k=key: self.set_exchange(k))
            m.add_separator()
        if FROZEN:
            m.add_command(label=f'Kiểm tra cập nhật (đang dùng v{APP_VERSION})', command=self.check_update_now)
            m.add_command(label='Gỡ khỏi máy…', command=self.uninstall)
        m.add_command(label='Tắt chương trình', command=self.quit)
        self.menu = m

    def set_exchange(self, key):
        crits = [dict(c) for c in self.cfg['criteria']]
        crits[0]['exchange'] = key
        self.apply_settings({'criteria': crits})

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

    def compute(self):
        """Lọc lại từ giá mới nhất + lịch sử cho từng tiêu chí; đánh dấu mã mới lọt lọc."""
        if self.quotes is None:
            return
        data = self.hist.get('data', {})
        rows = [core.transform_quote(q, data.get(q.get('Symbol'))) for q in self.quotes]
        all_stocks = core.group_by_exchange(rows)
        sort = {'sortColumn': self.cfg.get('sortColumn'), 'sortDirection': self.cfg.get('sortDirection')}

        self.sections, seen, flat = [], set(), []
        for c in self.cfg['criteria']:
            if not core.active_filter_keys(c['filters']):
                continue
            m = core.select_matches(all_stocks, {**c, **sort})
            self.sections.append((c, m))
            for st in m:
                if st['symbol'] not in seen:
                    seen.add(st['symbol'])
                    flat.append(st)
        self.matches = flat

        now_by_key = {core.criterion_key(c): {st['symbol'] for st in m} for c, m in self.sections}
        if self.prev_by_key is not None:
            groups = []
            for c, m in self.sections:
                before = self.prev_by_key.get(core.criterion_key(c))
                if before is None:          # tiêu chí vừa thêm / vừa sửa → chưa có gì để so
                    continue
                fresh = [st['symbol'] for st in m if st['symbol'] not in before]
                if fresh:
                    groups.append((c['name'], fresh))
            if groups:
                until = time.time() + NEW_HIGHLIGHT_SEC
                for _, syms in groups:
                    for sym in syms:
                        self.new_until[sym] = until
                self.alert(groups)
                self.root.after(int(NEW_HIGHLIGHT_SEC * 1000) + 100, self.render)
        self.prev_by_key = now_by_key

    def alert(self, groups, mode=None):
        """groups = [(tên tiêu chí, [mã mới…])]."""
        mode = mode or self.cfg.get('alert', 'speak')
        groups = [(n, list(syms)) for n, syms in groups if syms]
        if mode == 'off' or not groups:
            return
        if mode == 'speak':
            if self.speaker and self.speaker.poll() is None:
                self.pending_say += groups
                return
            vi, en = core.alert_text_groups(groups)
            try:
                self.speaker = subprocess.Popen(
                    ['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', SPEAK_PS],
                    env={**os.environ, 'BEEVN_SAY': vi, 'BEEVN_SAY_EN': en},
                    creationflags=0x08000000)
                return
            except OSError as e:
                log('speak: ' + repr(e))   # không đọc được → kêu ting thay
        try:
            import winsound
            winsound.MessageBeep(0x40)
        except Exception:
            pass

    def say_pending(self):
        """Đọc nốt những mã mới đến trong lúc đang đọc dở (gộp theo tiêu chí, bỏ mã trùng)."""
        if self.pending_say and not (self.speaker and self.speaker.poll() is None):
            merged = {}
            for name, syms in self.pending_say:
                lst = merged.setdefault(name, [])
                lst += [x for x in syms if x not in lst]
            self.pending_say = []
            self.alert(list(merged.items()))

    def ma_source_note(self):
        if self.hist_progress < 1:
            return f'đang tính MA {int(self.hist_progress * 100)}%'
        if self.hist.get('source') == 'fireant':
            return 'MA: FireAnt'
        return 'MA: tự tính từ VNDirect' + (f' ({self.stat_note})' if self.stat_note else '')

    def render(self):
        cfg = self.cfg
        full = cfg['mode'] == 'full'
        crits = cfg['criteria']
        sections = self.sections if self.quotes is not None else []
        multi = len([c for c in crits if core.active_filter_keys(c['filters'])]) > 1
        has_filter = any(core.active_filter_keys(c['filters']) for c in crits)

        # Dòng trạng thái: sàn (hoặc số tiêu chí) · số mã · giờ cập nhật
        if multi:
            parts = [f'{len(sections) or len(crits)} tiêu chí']
        else:
            first = next((c for c in crits if core.active_filter_keys(c['filters'])), crits[0])
            parts = [EXCHANGE_LABEL.get(first['exchange'], first['exchange'])]
        if has_filter and self.quotes is not None:
            parts.append(f'{len(self.matches)} mã')
        if self.fetched_at:
            parts.append(time.strftime('%H:%M:%S', time.localtime(self.fetched_at)))
        stale = self.error or (self.fetched_at and core.is_trading_time()
                               and time.time() - self.fetched_at > STALE_SEC)
        self.meta.config(text=' · '.join(parts), fg='#eab308' if stale else MUTED)

        # Dòng dưới thanh tiêu đề (chế độ đầy đủ): 1 tiêu chí → mô tả lọc + nguồn MA; nhiều → chỉ nguồn MA
        if full and has_filter:
            text = self.ma_source_note()
            if not multi and sections:
                text = core.describe_filters(sections[0][0]['filters']) + '   ·   ' + text
            self.filters_lbl.config(text=text)
            self.filters_lbl.pack(fill='x', padx=8, pady=(3, 1), after=self.frame.winfo_children()[0])
        else:
            self.filters_lbl.pack_forget()

        # Bảng: mỗi tiêu chí một khối
        for w in self.table.winfo_children():
            w.destroy()
        total = sum(len(m) for _, m in sections)
        self.total_rows = total
        self.offset = max(0, min(self.offset, max(0, total - MAX_ROWS)))
        lo, hi = self.offset, self.offset + MAX_ROWS
        idx = 0
        shown = 0
        for c, m in sections:
            vis = [st for i, st in enumerate(m, idx) if lo <= i < hi]
            idx += len(m)
            if m and not vis:
                continue                    # khối đã lăn qua hết
            self._render_section(c, m, vis, full, multi)
            shown += len(vis)
        hidden = total - shown
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
        elif not multi and total == 0:
            msg, color = 'Chưa có mã nào khớp bộ lọc.', MUTED
        else:
            msg, color = '', MUTED
        self.msg.config(text=msg, fg=color)
        if msg:
            self.msg.pack(fill='x', padx=8, pady=(4, 6))
        else:
            self.msg.pack_forget()

        self.fit()

    def _render_section(self, c, matches, visible, full, multi):
        box = tk.Frame(self.table, bg=BG)
        box.pack(fill='x')
        for w in (box,):
            w.bind('<MouseWheel>', self.on_wheel)
            w.bind('<Button-3>', self.show_menu)
        if multi:
            ex = EXCHANGE_LABEL.get(c['exchange'], c['exchange'])
            title = tk.Label(box, text=f'{c["name"]}  ·  {ex}  ·  {len(matches)} mã', bg=SECTION, fg=GOLD,
                             font=('Segoe UI', 8, 'bold'), anchor='w', padx=8)
            title.pack(fill='x', pady=(2, 0))
            self._bind_table(title)
            if full:
                d = tk.Label(box, text=core.describe_filters(c['filters']), bg=BG, fg=MUTED, font=FONT_SMALL,
                             anchor='w', padx=8)
                d.pack(fill='x')
                self._bind_table(d)
        if not matches:
            e = tk.Label(box, text='chưa có mã nào khớp', bg=BG, fg=MUTED, font=FONT_SMALL, anchor='w', padx=8)
            e.pack(fill='x', pady=(1, 3))
            self._bind_table(e)
            return
        grid = tk.Frame(box, bg=BG)
        grid.pack(fill='x')
        grid.bind('<MouseWheel>', self.on_wheel)
        cols = core.table_columns(c, full)
        active = set(core.active_filter_keys(c['filters']))
        sort_col, sort_dir = self.cfg.get('sortColumn'), self.cfg.get('sortDirection')
        for ci, (key, label) in enumerate(cols):
            arrow = (' ▲' if sort_dir == 'asc' else ' ▼') if key == sort_col else ''
            txt = core.HEAD_LABEL.get(key, label).upper() + (' •' if key in active else '') + arrow
            fg = FILTERED if key in active else (TEXT if key == sort_col else MUTED)
            lbl = tk.Label(grid, text=txt, bg=BG, fg=fg,
                           font=FONT_HEAD, anchor='w' if ci == 0 else 'e', padx=8, cursor='hand2')
            lbl.grid(row=0, column=ci, sticky='ew', pady=(3, 2))
            # Bấm tiêu đề cột = sắp xếp theo cột đó (bấm vào hàng mới là thu gọn / đầy đủ)
            lbl.bind('<Button-1>', lambda e, k=key: self.sort_by(k))
            lbl.bind('<MouseWheel>', self.on_wheel)
            lbl.bind('<Button-3>', self.show_menu)
        now = time.time()
        for ri, st in enumerate(visible, 1):
            bg = NEW_BG if self.new_until.get(st['symbol'], 0) > now else (ALT if ri % 2 == 0 else BG)
            for ci, (key, _) in enumerate(cols):
                text, tone = core.format_cell(st, key)
                lbl = tk.Label(grid, text=text, bg=bg, fg=TONE.get(tone, TEXT),
                               font=FONT_BOLD if key == 'symbol' else FONT,
                               anchor='w' if ci == 0 else 'e', padx=8)
                lbl.grid(row=ri, column=ci, sticky='ew')
                self._bind_table(lbl)
        tk.Frame(grid, bg=BG, height=4).grid(row=len(visible) + 1, column=0)
        # Cột cuối giãn ra cho kín bề ngang khi khối khác / thanh tiêu đề rộng hơn
        for ci in range(len(cols)):
            grid.grid_columnconfigure(ci, weight=1 if ci == len(cols) - 1 else 0)

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
    def sort_by(self, key):
        col, direction = core.next_sort(self.cfg.get('sortColumn'), self.cfg.get('sortDirection'), key)
        self.cfg['sortColumn'], self.cfg['sortDirection'] = col, direction
        save_json(CONFIG_PATH, self.cfg)
        self.offset = 0
        self.compute()
        self.render()

    def toggle_mode(self):
        self.cfg['mode'] = 'compact' if self.cfg['mode'] == 'full' else 'full'
        save_json(CONFIG_PATH, self.cfg)
        self.render()

    def on_wheel(self, e):
        if getattr(self, 'total_rows', 0) <= MAX_ROWS:
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

    def uninstall(self):
        if not messagebox.askyesno(APP_NAME, 'Gỡ Bee.vn mini khỏi máy?\n\nXoá biểu tượng ngoài Desktop, '
                                             'bỏ tự mở khi bật máy và tắt chương trình.', parent=self.root):
            return
        remove_all_shortcuts()
        if os.path.normcase(sys.executable) == os.path.normcase(INSTALLED_EXE):
            # File đang chạy không tự xoá được → nhờ cmd xoá sau khi chương trình tắt
            subprocess.Popen(f'cmd /c ping -n 4 127.0.0.1 >nul & rmdir /s /q "{INSTALL_DIR}"',
                             creationflags=0x08000000)
        self.root.destroy()

    # ── Cài đặt ──
    def open_settings(self):
        if self.settings_win and self.settings_win.winfo_exists():
            self.settings_win.lift()
            return
        SettingsWindow(self)

    def apply_settings(self, new_cfg):
        self.cfg.update(new_cfg)
        self.cfg['criteria'] = core.criteria_from_config(self.cfg)
        self._build_menu()            # số tiêu chí đổi → menu đổi sàn nhanh có/không
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
                sheet = self.cfg.get('cookieSheetId')
                if not sheet:
                    self.q.put(('stat_note', None))
                if sheet and hist.get('source') != 'fireant':
                    try:
                        cookie = core.fetch_fireant_cookie(sheet)
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
            self.wake_hist.wait(HIST_CHECK_SEC)
            self.wake_hist.clear()

    def listen_loop(self, lock):
        """Nghe bản thứ hai (người dùng bấm biểu tượng khi đang chạy) nhắn "show"."""
        while True:
            try:
                conn, _ = lock.accept()
                with conn:
                    conn.settimeout(2)
                    msg = conn.recv(16)
                    if msg.startswith(b'show'):
                        self.q.put(('show',))
                    elif msg.startswith(b'update') and self.update_info:   # chạy thử: cập nhật không hỏi
                        threading.Thread(target=self.download_update, args=(self.update_info,), daemon=True).start()
            except OSError:
                time.sleep(1)

    # ── Tự cập nhật (bản .exe) ──
    def fetch_update(self):
        req = urllib.request.Request(f'{UPDATE_URL}?t={int(time.time())}', headers={'User-Agent': core.UA})
        with urllib.request.urlopen(req, timeout=20) as res:
            return core.parse_update(json.loads(res.read().decode('utf-8')), APP_VERSION)

    def update_loop(self):
        time.sleep(20)
        while True:
            try:
                info = self.fetch_update()
                if info:
                    self.q.put(('update', info))
            except Exception as e:
                log('update check: ' + repr(e))
            time.sleep(UPDATE_CHECK_SEC)

    def check_update_now(self):
        def run():
            try:
                info = self.fetch_update()
                self.q.put(('update', info) if info else ('update_none',))
            except Exception as e:
                log('update check: ' + repr(e))
                self.q.put(('update_fail', 'Không kiểm tra được bản mới (mất mạng?).'))
        threading.Thread(target=run, daemon=True).start()

    def show_update(self, info):
        self.update_info = info
        self.update_btn.pack(side='right', padx=(0, 4), after=self.refresh_btn)
        self.fit()

    def do_update(self):
        info = self.update_info
        if not info:
            return
        notes = ('\n\nCó gì mới:\n' + info['notes']) if info['notes'] else ''
        if not messagebox.askyesno(APP_NAME, f'Có bản mới v{info["version"]} (đang dùng v{APP_VERSION}).'
                                             f'{notes}\n\nCập nhật ngay? Bảng giá tắt vài giây rồi tự mở lại.',
                                   parent=self.root):
            return
        self.update_btn.config(text='đang tải…')
        threading.Thread(target=self.download_update, args=(info,), daemon=True).start()

    def download_update(self, info):
        import hashlib
        target = sys.executable
        new = target + '.new'
        try:
            req = urllib.request.Request(info['url'], headers={'User-Agent': core.UA})
            h = hashlib.sha256()
            got = 0
            with urllib.request.urlopen(req, timeout=60) as res, open(new, 'wb') as f:
                while True:
                    chunk = res.read(256 * 1024)
                    if not chunk:
                        break
                    f.write(chunk)
                    h.update(chunk)
                    got += len(chunk)
                    if info['size']:
                        self.q.put(('update_progress', got / info['size']))
            if h.hexdigest() != info['sha256']:
                raise ValueError('file tải về không khớp mã kiểm tra')
        except Exception as e:
            log('update download: ' + repr(e))
            try:
                os.remove(new)
            except OSError:
                pass
            self.q.put(('update_fail', f'Tải bản mới không được: {e}'))
            return
        # File .exe đang chạy không ghi đè được → nhờ cmd đợi chương trình tắt hẳn rồi thay và mở lại.
        bat = os.path.join(os.path.dirname(target), 'beevn_update.cmd')
        with open(bat, 'w', encoding='mbcs', errors='replace', newline='') as f:
            # ping thay cho timeout: timeout của Windows báo lỗi khi chạy không có cửa sổ
            cmd_lines = ['@echo off', 'set n=0', ':retry',
                         f'move /y "{new}" "{target}" >nul 2>&1',
                         'if not errorlevel 1 goto done', 'set /a n+=1', 'if %n% geq 60 goto done',
                         'ping -n 2 127.0.0.1 >nul', 'goto retry', ':done',
                         f'start "" "{target}"', 'del "%~f0"']
            f.write('\r\n'.join(cmd_lines) + '\r\n')
        subprocess.Popen(['cmd', '/c', bat], creationflags=0x08000000)   # không hiện cửa sổ
        self.q.put(('update_restart',))

    def bring_front(self):
        """Hiện bảng giá lên trước mặt, kéo về trong màn hình nếu đang lạc ra ngoài, nháy viền vàng."""
        self.root.deiconify()
        self.root.attributes('-topmost', True)
        self.root.lift()
        self.fit()
        self.root.configure(bg=GOLD)
        self.root.after(1200, lambda: self.root.configure(bg=LINE))

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
                elif kind == 'update':
                    self.show_update(payload[0])
                    continue
                elif kind == 'update_none':
                    messagebox.showinfo(APP_NAME, f'Đang dùng bản mới nhất (v{APP_VERSION}).', parent=self.root)
                    continue
                elif kind == 'update_progress':
                    self.update_btn.config(text=f'đang tải {int(payload[0] * 100)}%')
                    continue
                elif kind == 'update_fail':
                    self.update_btn.config(text='⬆ Cập nhật')
                    messagebox.showwarning(APP_NAME, payload[0], parent=self.root)
                    continue
                elif kind == 'update_restart':
                    self.root.destroy()
                    return
                elif kind == 'show':
                    self.bring_front()
                    continue
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
        self.say_pending()
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

        # Bản nháp các tiêu chí — sửa thoải mái, bấm Lưu mới áp dụng
        self.crits = [dict(c, filters=dict(c['filters'])) for c in cfg['criteria']]
        self.cur = 0

        ttk.Label(body, text='Bộ lọc', font=('Segoe UI', 11, 'bold')).grid(row=0, column=0, columnspan=3, sticky='w')
        ttk.Label(body, text='Mỗi tiêu chí gồm nhiều điều kiện (phải thoả TẤT CẢ). Có nhiều tiêu chí thì bảng giá\n'
                             'hiện mỗi tiêu chí một khối. Để trống ô giá trị = không lọc cột đó.\n'
                             'Giá bằng nghìn đồng (14.2 = 14.200đ), KLGD bằng cổ phiếu, GTGD bằng tỷ đồng.',
                  foreground='#666').grid(row=1, column=0, columnspan=3, sticky='w', pady=(2, 8))

        pick = ttk.Frame(body)
        pick.grid(row=2, column=0, columnspan=3, sticky='w', pady=(0, 6))
        ttk.Label(pick, text='Tiêu chí').pack(side='left')
        self.crit_box = ttk.Combobox(pick, state='readonly', width=22)
        self.crit_box.pack(side='left', padx=6)
        self.crit_box.bind('<<ComboboxSelected>>', lambda e: self.switch(self.crit_box.current()))
        ttk.Button(pick, text='＋ Thêm tiêu chí', command=self.add_criterion).pack(side='left', padx=(4, 0))
        ttk.Button(pick, text='Xoá', command=self.delete_criterion).pack(side='left', padx=4)

        ttk.Label(body, text='Tên').grid(row=3, column=0, sticky='w', pady=2)
        self.crit_name = ttk.Entry(body, width=30)
        self.crit_name.grid(row=3, column=1, columnspan=2, sticky='w', pady=2)

        ttk.Label(body, text='Sàn').grid(row=4, column=0, sticky='w', pady=2)
        self.exchange = ttk.Combobox(body, state='readonly', width=16,
                                     values=[EXCHANGE_LABEL[k] for k in ('HSX', 'HNX', 'UPCOM', 'ALL')])
        self.exchange.grid(row=4, column=1, sticky='w', pady=2)

        self.rows = {}
        op_names = [n for _, n in OP_LABEL]
        for i, (key, label) in enumerate(core.FILTERABLE, start=5):
            ttk.Label(body, text=label).grid(row=i, column=0, sticky='w', pady=2)
            op = ttk.Combobox(body, state='readonly', width=16, values=op_names)
            op.grid(row=i, column=1, sticky='w', padx=(0, 8), pady=2)
            val = ttk.Entry(body, width=14)
            val.grid(row=i, column=2, sticky='w', pady=2)
            self.rows[key] = (op, val)
        self.load_form()

        r = 5 + len(core.FILTERABLE)
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

        ttk.Label(body, text='Khi có mã mới').grid(row=r + 3, column=0, sticky='w', pady=(8, 2))
        self.alert = ttk.Combobox(body, state='readonly', width=16, values=[n for _, n in ALERT_LABEL])
        self.alert.set(dict(ALERT_LABEL).get(cfg.get('alert', 'speak'), ALERT_LABEL[0][1]))
        self.alert.grid(row=r + 3, column=1, sticky='w', pady=(8, 2))
        ttk.Button(body, text='Nghe thử', command=self.test_alert).grid(row=r + 3, column=2, sticky='w', pady=(8, 2))
        self.startup = tk.BooleanVar(value=has_startup())
        ttk.Checkbutton(body, text='Tự mở khi bật máy', variable=self.startup) \
            .grid(row=r + 4, column=0, columnspan=3, sticky='w', pady=2)

        ttk.Separator(body).grid(row=r + 5, column=0, columnspan=3, sticky='ew', pady=10)
        ttk.Label(body, text='Sheet cookie FireAnt (tuỳ chọn)', font=('Segoe UI', 9, 'bold')) \
            .grid(row=r + 6, column=0, columnspan=3, sticky='w')
        ttk.Label(body, text='Dán link Google Sheet có cookie FireAnt ở ô D2 sheet "Dashboard" → cột MA lấy '
                             'thẳng FireAnt.\nĐể trống → MA tự tính từ VNDirect.', foreground='#666') \
            .grid(row=r + 7, column=0, columnspan=3, sticky='w', pady=(2, 4))
        self.sheet = ttk.Entry(body, width=70)
        self.sheet.insert(0, cfg.get('cookieSheetId') or '')
        self.sheet.grid(row=r + 8, column=0, columnspan=3, sticky='ew')

        btns = ttk.Frame(body)
        btns.grid(row=r + 9, column=0, columnspan=3, sticky='e', pady=(12, 0))
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

    def alert_mode(self):
        return {n: k for k, n in ALERT_LABEL}.get(self.alert.get(), 'speak')

    def test_alert(self):
        # Đọc thử vài mã đầu đang khớp ở từng khối, chưa có thì lấy mã mẫu
        groups = [(c['name'], [st['symbol'] for st in m[:2]]) for c, m in self.app.sections]
        groups = [g for g in groups if g[1]] or [('Tiêu chí 1', ['VIB', 'MBB'])]
        self.app.alert(groups, mode=self.alert_mode())

    # ── Bản nháp tiêu chí ──
    def load_form(self):
        c = self.crits[self.cur]
        self.crit_box['values'] = [x['name'] for x in self.crits]
        self.crit_box.current(self.cur)
        self.crit_name.delete(0, 'end')
        self.crit_name.insert(0, c['name'])
        self.exchange.set(EXCHANGE_LABEL.get(c['exchange'], 'HSX'))
        op_label = dict(OP_LABEL)
        for key, (op, val) in self.rows.items():
            f = c['filters'].get(key) or {}
            op.set(op_label.get(f.get('operator', 'gt'), OP_LABEL[0][1]))
            val.delete(0, 'end')
            if f.get('value') not in (None, ''):
                val.insert(0, core.js_num(f['value']))

    def store_form(self):
        """Ghi ô đang sửa vào bản nháp. Trả False (và báo) nếu có ô không phải số."""
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
            return False
        label_to_ex = {v: k for k, v in EXCHANGE_LABEL.items()}
        self.crits[self.cur] = {'name': self.crit_name.get().strip() or f'Tiêu chí {self.cur + 1}',
                                'exchange': label_to_ex.get(self.exchange.get(), 'HSX'),
                                'filters': filters}
        return True

    def switch(self, i):
        if i == self.cur:
            return
        if not self.store_form():
            self.crit_box.current(self.cur)
            return
        self.cur = i
        self.load_form()

    def add_criterion(self):
        if not self.store_form():
            return
        n = len(self.crits) + 1
        self.crits.append({'name': f'Tiêu chí {n}', 'exchange': self.crits[self.cur]['exchange'], 'filters': {}})
        self.cur = len(self.crits) - 1
        self.load_form()
        self.crit_name.focus_set()
        self.crit_name.select_range(0, 'end')

    def delete_criterion(self):
        if len(self.crits) == 1:
            messagebox.showinfo(APP_NAME, 'Phải còn ít nhất 1 tiêu chí. Muốn tắt lọc thì xoá trống các ô giá trị.',
                                parent=self.win)
            return
        name = self.crits[self.cur]['name']
        if not messagebox.askyesno(APP_NAME, f'Xoá tiêu chí "{name}"?', parent=self.win):
            return
        del self.crits[self.cur]
        self.cur = max(0, self.cur - 1)
        self.load_form()

    def save(self):
        if not self.store_form():
            return
        self.load_form()                 # cập nhật tên mới trong ô chọn
        sheet_raw = self.sheet.get().strip()
        sheet = core.sheet_id_from(sheet_raw)
        if sheet_raw and not sheet:
            messagebox.showwarning(APP_NAME, 'Không nhận ra link Google Sheet.', parent=self.win)
            return
        label_to_col = {l: k for k, l in core.COLUMNS}
        self.app.apply_settings({
            'criteria': [dict(c, filters=dict(c['filters'])) for c in self.crits],
            'sortColumn': label_to_col.get(self.sort_col.get(), 'value'),
            'sortDirection': 'asc' if self.sort_dir.get() == 'Tăng dần' else 'desc',
            'alert': self.alert_mode(),
            'opacity': round(self.opacity.get(), 2),
            'cookieSheetId': sheet,
        })
        self.app.hist['source'] = None   # đổi sheet → thử lại FireAnt ngay
        self.app.wake_hist.set()
        if self.startup.get() != has_startup():
            if self.startup.get():
                make_shortcut('Startup')
            else:
                remove_shortcut('Startup')
        self.saved.config(text='✓ Đã lưu')
        self.win.after(1500, lambda: self.saved.winfo_exists() and self.saved.config(text=''))


def offer_install(lock):
    """Chạy file .exe vừa tải về (chưa nằm trong máy): hỏi cài. Trả True nếu đã chuyển sang bản cài."""
    cfg = {**DEFAULT_CONFIG, **load_json(CONFIG_PATH, {})}
    updating = os.path.exists(INSTALLED_EXE)
    if not updating and cfg.get('askedInstall'):
        return False          # đã từ chối cài lần trước → chạy luôn từ chỗ này
    r = tk.Tk()
    r.withdraw()
    ask = ('Cập nhật Bee.vn mini lên bản này?' if updating else
           'Cài Bee.vn mini vào máy?\n\n• Tạo biểu tượng "Bee.vn mini" ngoài Desktop\n'
           '• Tự mở mỗi khi bật máy\n\nChọn "No" để chỉ chạy thử lần này.')
    yes = messagebox.askyesno(APP_NAME, ask)
    if not yes:
        r.destroy()
        cfg['askedInstall'] = True
        save_json(CONFIG_PATH, cfg)
        return False
    try:
        import shutil
        os.makedirs(INSTALL_DIR, exist_ok=True)
        shutil.copy2(sys.executable, INSTALLED_EXE)
        ok = make_all_shortcuts()
    except OSError as e:
        log('install: ' + repr(e))
        messagebox.showerror(APP_NAME, 'Không cài được: ' + str(e))
        r.destroy()
        return False
    messagebox.showinfo(APP_NAME, ('Đã cập nhật.' if updating else 'Đã cài xong.') +
                        '\n\nBảng giá mini sẽ hiện ở góc dưới-phải màn hình.' +
                        ('' if ok else '\n(Không tạo được biểu tượng Desktop — xem ' + LOG_PATH + ')'))
    r.destroy()
    lock.close()             # nhả khoá để bản cài mở lên được
    subprocess.Popen([INSTALLED_EXE], cwd=INSTALL_DIR)
    return True


def main():
    # Chữ nét trên màn hình độ phân giải cao
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    if '--uninstall' in sys.argv:
        remove_all_shortcuts()
        r = tk.Tk()
        r.withdraw()
        messagebox.showinfo(APP_NAME, 'Đã xoá biểu tượng ngoài Desktop và tự chạy khi bật máy.\n'
                                      'Nếu bảng giá mini đang mở, bấm ✕ trên nó để tắt.')
        return

    if '--install' in sys.argv:
        ok = make_all_shortcuts()
        r = tk.Tk()
        r.withdraw()
        messagebox.showinfo(APP_NAME, 'Đã cài xong.\n\n• Biểu tượng "Bee.vn mini" ở ngoài Desktop và trong menu Start.\n'
                                      '• Tự mở mỗi khi bật máy.\n\nBảng giá mini sẽ hiện ở góc dưới-phải màn hình.'
                            if ok else 'Không tạo được biểu tượng — xem log ở ' + LOG_PATH)
        r.destroy()

    # Chỉ chạy một bản. Bấm biểu tượng lần nữa → bản thứ hai nhắn bản đang chạy "hiện lên" rồi tự thoát.
    lock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        lock.bind(('127.0.0.1', SINGLE_INSTANCE_PORT))
        lock.listen(2)
    except OSError:
        try:
            with socket.create_connection(('127.0.0.1', SINGLE_INSTANCE_PORT), timeout=2) as c:
                c.sendall(b'show')
        except OSError:
            pass
        if FROZEN and os.path.normcase(sys.executable) != os.path.normcase(INSTALLED_EXE):
            r = tk.Tk()
            r.withdraw()
            messagebox.showinfo(APP_NAME, 'Bee.vn mini đang chạy rồi.\n\nMuốn cài bản mới: bấm ✕ trên bảng giá '
                                          'mini để tắt, rồi mở lại file này.')
        return

    if FROZEN and os.path.normcase(sys.executable) != os.path.normcase(INSTALLED_EXE):
        if offer_install(lock):
            return

    root = tk.Tk()
    root.title(APP_NAME)
    try:
        root.iconbitmap(ICON_PATH)
    except tk.TclError:
        pass
    root.report_callback_exception = lambda *a: log('ui: ' + ''.join(traceback.format_exception(*a)))
    App(root, lock)
    root.mainloop()


if __name__ == '__main__':
    try:
        main()
    except Exception:
        log('fatal: ' + traceback.format_exc())
        raise
