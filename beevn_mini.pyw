"""
Bee.vn mini — cửa sổ bảng giá nhỏ, LUÔN NỔI trên mọi cửa sổ (kể cả khi chuyển app / tab).

  1 mã = 1 hàng; nhiều mã thì cửa sổ dài thêm lên trên, neo góc dưới-phải như chồng thông báo.
  Thu gọn: Mã CP + các cột đang lọc. Bấm vào bảng → đủ 11 cột như bảng giá Bee.vn.
  Kéo thanh trên cùng để dời chỗ. Chuột phải để mở menu.

Chạy bằng pythonw (không hiện cửa sổ đen). Tham số:
  --install    tạo biểu tượng ngoài Desktop + tự chạy khi bật máy, rồi mở chương trình
  --uninstall  xoá hai biểu tượng đó
"""
import copy
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

import conditions  # noqa: E402
import core  # noqa: E402
from symbols import SYMBOLS  # noqa: E402

APP_NAME = 'Bee.vn mini'
# Tăng số này mỗi lần phát hành bản mới (tools/release.py đọc nó). BEEVN_FAKE_VERSION chỉ để thử cập nhật.
APP_VERSION = os.environ.get('BEEVN_FAKE_VERSION') or '1.5.1'
# Bản mới nhất: nhánh "release" của kho GitHub công khai stevesinek1702/BeeVnMini
UPDATE_URL = (os.environ.get('BEEVN_UPDATE_URL')     # chỉ để chạy thử
              or 'https://raw.githubusercontent.com/stevesinek1702/BeeVnMini/release/latest.json')
UPDATE_CHECK_SEC = 6 * 3600
# BEEVN_DATA_DIR: chỉ để chạy thử mà không đụng cài đặt thật
DATA_DIR = os.environ.get('BEEVN_DATA_DIR') or os.path.join(os.environ.get('APPDATA', HERE), 'BeeVnMini')
CONFIG_PATH = os.path.join(DATA_DIR, 'config.json')
HIST_PATH = os.path.join(DATA_DIR, 'hist.json')
TECH_PATH = os.path.join(DATA_DIR, 'tech.json')      # thống kê kỹ thuật từ nến ngày, mỗi ngày tải 1 lần
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
MAX_ROWS = 25            # 1 tiêu chí: quá số hàng này thì lăn chuột để xem tiếp
SECTION_ROWS = 8         # nhiều tiêu chí: mỗi khối mặc định hiện chừng này hàng (＋/－ để đổi)
WHEEL_ROWS = 2           # mỗi nấc lăn chuột trượt 2 hàng
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
TONE = {'up': '#22c55e', 'down': '#ef4444', 'flat': '#eab308', 'ceil': '#c084fc', 'floor': '#22d3ee',
        'muted': MUTED, 'sym': ACCENT, '': TEXT}
FILTERED = '#f87171'
SECTION = '#22224a'     # nền dòng tên tiêu chí

EXCHANGE_LABEL = {'HSX': 'HSX', 'HNX': 'HNX', 'UPCOM': 'UpCom', 'ALL': 'Cả 3 sàn'}
OP_LABEL = [('gt', 'Lớn hơn (>)'), ('lt', 'Nhỏ hơn (<)'), ('eq', 'Bằng (=)')]
# Điều kiện thêm kiểu FireAnt: "từ / đến / trong khoảng" (FireAnt tính cả mốc)
METRIC_OP_LABEL = [('ge', 'Từ (≥)'), ('le', 'Đến (≤)'), ('bt', 'Trong khoảng')]
METRIC_UNIT = {'pct': '%', 'pct0': '%', 'int': 'phiên', 'vol': 'cổ phiếu', 'svol': 'cổ phiếu', 'sbil': 'tỷ đồng'}
# Cột có thể chọn để xếp trong Cài đặt (đủ cột bảng giá + cột kiểu FireAnt)
SORT_COLUMNS = list(core.COLUMNS) + [(k, conditions.METRIC_LABEL[k]) for k in conditions.METRIC_KEYS]

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
        self.tech = load_json(TECH_PATH, {})     # thống kê kỹ thuật (RSI, MACD, SMA, đỉnh đáy…) — chỉ tải khi có tiêu chí cần
        self.tech_progress = 1.0 if self.tech.get('day') == core.vn_date(time.time()) else 0.0
        self.stat_note = None   # lý do không dùng được FireAnt cho cột MA (vd cookie hết hạn)
        self.prev_by_key = None      # {khoá tiêu chí: tập mã lượt trước} — để biết mã nào MỚI lọt lọc
        self.new_until = {}
        self.sections = []           # [(tiêu chí, [mã khớp])] — chỉ tiêu chí đã có điều kiện
        self.matches = []            # gộp mọi khối, không trùng mã
        self.scroll_pos = {}          # {tên tiêu chí: vị trí cuộn 0..1} — giữ nguyên khi giá cập nhật
        self.q = queue.Queue()
        self.wake = threading.Event()
        self.wake_hist = threading.Event()
        self.wake_tech = threading.Event()
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
        self.table_body = None        # khung bảng hiện tại; vẽ khung mới xong mới thay → không nháy
        self.msg = tk.Label(self.frame, bg=BG, fg=MUTED, font=('Segoe UI', 9), justify='left',
                            anchor='w', wraplength=300)
        self.msg.pack(fill='x', padx=8, pady=(0, 6))

        self._build_menu()
        for w in (self.frame, self.table):
            w.bind('<MouseWheel>', self.on_wheel)
            w.bind('<Button-3>', self.show_menu)

        self.hide_from_taskbar()
        self.render()
        threading.Thread(target=self.quote_loop, daemon=True).start()
        threading.Thread(target=self.hist_loop, daemon=True).start()
        threading.Thread(target=self.tech_loop, daemon=True).start()
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
        tech = self.tech_data()
        rows = [core.transform_quote(q, data.get(q.get('Symbol')), tech.get(q.get('Symbol'))) for q in self.quotes]
        all_stocks = core.group_by_exchange(rows)
        sort = {'sortColumn': self.cfg.get('sortColumn'), 'sortDirection': self.cfg.get('sortDirection')}

        self.sections, seen, flat = [], set(), []
        for c in self.cfg['criteria']:
            if not core.has_conditions(c):
                continue
            m = core.select_matches(all_stocks, {**sort, **c})     # kiểu xếp riêng của tiêu chí đè lên kiểu chung
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
                    groups.append((c['name'], fresh, c.get('alert', 'speak')))
            if groups:
                until = time.time() + NEW_HIGHLIGHT_SEC
                for _, syms, _ in groups:
                    for sym in syms:
                        self.new_until[sym] = until      # hàng mới vẫn sáng vàng kể cả khi im lặng
                self.alert(groups)
                self.root.after(int(NEW_HIGHLIGHT_SEC * 1000) + 100, self.render)
        self.prev_by_key = now_by_key

    def alert(self, groups, names=None):
        """groups = [(tên tiêu chí, [mã mới…], kiểu báo của tiêu chí đó)].
        Các tiêu chí "đọc tên mã" được đọc gộp một câu; có tiêu chí "kêu ting" thì kêu một tiếng."""
        groups = [(n, list(syms), mode) for n, syms, mode in groups if syms]
        speak = [(n, syms) for n, syms, mode in groups if mode == 'speak']
        beep = any(mode == 'beep' for _, _, mode in groups)
        if speak:
            if self.speaker and self.speaker.poll() is None:
                self.pending_say += speak
                speak = []
            elif not self.say(speak, names):
                beep = True                # không đọc được → kêu ting thay
        if beep:
            try:
                import winsound
                winsound.MessageBeep(0x40)
            except Exception:
                pass

    def say(self, groups, names=None):
        """Đọc to [(tên tiêu chí, [mã…])]. Có nhiều tiêu chí thì đọc kèm tên tiêu chí. False = không đọc được."""
        if names is None:
            names = len(self.cfg['criteria']) > 1
        vi, en = core.alert_text_groups(groups, names=names)
        try:
            self.speaker = subprocess.Popen(
                ['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', SPEAK_PS],
                env={**os.environ, 'BEEVN_SAY': vi, 'BEEVN_SAY_EN': en},
                creationflags=0x08000000)
            return True
        except OSError as e:
            log('speak: ' + repr(e))
            return False

    def say_pending(self):
        """Đọc nốt những mã mới đến trong lúc đang đọc dở (gộp theo tiêu chí, bỏ mã trùng)."""
        if self.pending_say and not (self.speaker and self.speaker.poll() is None):
            merged = {}
            for name, syms in self.pending_say:
                lst = merged.setdefault(name, [])
                lst += [x for x in syms if x not in lst]
            self.pending_say = []
            self.alert([(n, syms, 'speak') for n, syms in merged.items()])

    def tech_data(self):
        """Thống kê kỹ thuật của hôm nay (số của hôm qua trở về trước đã cũ: tín hiệu "cắt" sẽ sai → bỏ)."""
        return self.tech.get('data', {}) if self.tech.get('day') == core.vn_date(time.time()) else {}

    def tech_pending(self):
        """Có tiêu chí cần chỉ báo kỹ thuật mà số liệu chưa tải xong."""
        return self.tech_progress < 1 and any(core.needs_tech(c) for c in self.cfg['criteria'])

    def tech_note(self):
        return f'đang tính chỉ báo kỹ thuật {int(self.tech_progress * 100)}%'

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
        multi = len([c for c in crits if core.has_conditions(c)]) > 1
        has_filter = any(core.has_conditions(c) for c in crits)

        # Dòng trạng thái: sàn (hoặc số tiêu chí) · số mã · giờ cập nhật
        if multi:
            parts = [f'{len(sections) or len(crits)} tiêu chí']
        else:
            first = next((c for c in crits if core.has_conditions(c)), crits[0])
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
            if self.tech_pending():
                text += '   ·   ' + self.tech_note()
            if not multi and sections:
                text = core.describe_filters(sections[0][0]['filters'], sections[0][0].get('signals')) + '   ·   ' + text
            self.filters_lbl.config(text=text)
            self.filters_lbl.pack(fill='x', padx=8, pady=(3, 1), after=self.frame.winfo_children()[0])
        else:
            self.filters_lbl.pack_forget()

        # Bảng: mỗi tiêu chí một khối. Dựng khung mới (chưa hiện) rồi mới tháo khung cũ → một lần vẽ, không nháy.
        total = sum(len(m) for _, m in sections)
        body = tk.Frame(self.table, bg=BG)
        built = [self._build_section(body, c, m, full, multi) for c, m in sections]
        self._align_sections(built)
        if self.table_body is not None:
            self.table_body.destroy()
        body.pack(fill='x')
        self.table_body = body
        for b in built:
            if b.get('canvas') is not None:
                b['canvas'].yview_moveto(self.scroll_pos.get(b['name'], 0.0))

        # Thông điệp
        if self.quotes is None and not self.error:
            msg, color = 'Đang tải giá…', MUTED
        elif self.error and self.quotes is None:
            msg, color = f'{self.error}. Sẽ tự thử lại — kiểm tra mạng Internet.', '#fca5a5'
        elif not has_filter:
            msg, color = 'Chưa có bộ lọc. Bấm ⚙ để đặt lọc\n(vd Giá < 20, % Thay đổi > 2).', MUTED
        elif total == 0 and self.tech_pending():
            msg, color = self.tech_note().capitalize() + '…', MUTED
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

    def section_rows(self, name, multi):
        return int(self.cfg.get('sectionRows', {}).get(name, SECTION_ROWS if multi else MAX_ROWS))

    def _build_section(self, parent, c, matches, full, multi):
        """Dựng 1 khối: dòng tên (gập/mở, －/＋) → tiêu đề cột (đứng yên) → danh sách mã (cuộn riêng)."""
        name = c['name']
        info = {'name': name, 'grids': [], 'canvas': None, 'widths': None}
        box = tk.Frame(parent, bg=BG)
        box.pack(fill='x')
        collapsed = multi and name in self.cfg.get('collapsed', [])
        limit = self.section_rows(name, multi)

        if multi:
            bar = tk.Frame(box, bg=SECTION)
            bar.pack(fill='x', pady=(2, 0))
            ex = EXCHANGE_LABEL.get(c['exchange'], c['exchange'])
            more = f'  ·  lăn ↕ xem đủ' if (not collapsed and len(matches) > limit) else ''
            title = tk.Label(bar, text=f'{"▸" if collapsed else "▾"} {name}  ·  {ex}  ·  {len(matches)} mã{more}',
                             bg=SECTION, fg=GOLD, font=('Segoe UI', 8, 'bold'), anchor='w', padx=8, cursor='hand2')
            title.pack(side='left', fill='x', expand=True)
            title.bind('<Button-1>', lambda e: self.toggle_section(name))
            title.bind('<Button-3>', self.show_menu)
            if not collapsed:
                for txt, d in (('＋', +3), ('－', -3)):
                    b = tk.Label(bar, text=txt, bg=SECTION, fg=MUTED, font=('Segoe UI', 9, 'bold'),
                                 padx=5, cursor='hand2')
                    b.pack(side='right')
                    b.bind('<Button-1>', lambda e, d=d: self.resize_section(name, d, len(matches)))
                    b.bind('<Enter>', lambda e, w=b: w.config(fg=TEXT))
                    b.bind('<Leave>', lambda e, w=b: w.config(fg=MUTED))
            if collapsed:
                return info
            if full:
                d = tk.Label(box, text=core.describe_filters(c['filters'], c.get('signals')), bg=BG, fg=MUTED,
                             font=FONT_SMALL, anchor='w', padx=8, wraplength=420, justify='left')
                d.pack(fill='x')
                self._bind_table(d)
        if not matches:
            if multi:
                e = tk.Label(box, text='chưa có mã nào khớp', bg=BG, fg=MUTED, font=FONT_SMALL, anchor='w', padx=8)
                e.pack(fill='x', pady=(1, 3))
                self._bind_table(e)
            return info

        cols = core.table_columns(c, full)
        active = set(core.active_filter_keys(c['filters']))
        sort_col, sort_dir = self.sort_of(c)

        # Tiêu đề cột — nằm ngoài vùng cuộn nên luôn thấy
        head = tk.Frame(box, bg=BG)
        head.pack(fill='x')
        head_cells = []
        for ci, (key, label) in enumerate(cols):
            arrow = (' ▲' if sort_dir == 'asc' else ' ▼') if key == sort_col else ''
            txt = core.HEAD_LABEL.get(key, label).upper() + (' •' if key in active else '') + arrow
            fg = FILTERED if key in active else (TEXT if key == sort_col else MUTED)
            lbl = tk.Label(head, text=txt, bg=BG, fg=fg,
                           font=FONT_HEAD, anchor='w' if ci == 0 else 'e', padx=8, cursor='hand2')
            lbl.grid(row=0, column=ci, sticky='ew', pady=(3, 2))
            # Bấm tiêu đề cột = sắp xếp theo cột đó (bấm vào hàng mới là thu gọn / đầy đủ)
            lbl.bind('<Button-1>', lambda e, k=key, crit=c: self.sort_by(k, crit))
            lbl.bind('<Button-3>', self.show_menu)
            head_cells.append(lbl)

        # Danh sách mã: dài hơn giới hạn thì nằm trong vùng cuộn riêng của khối
        scroll = len(matches) > limit
        if scroll:
            canvas = tk.Canvas(box, bg=BG, highlightthickness=0, bd=0)
            canvas.pack(fill='x')
            rows_frame = tk.Frame(canvas, bg=BG)
            win_id = canvas.create_window(0, 0, window=rows_frame, anchor='nw')
            # Cửa sổ rộng hơn bảng → kéo khung hàng theo cho nền hàng phủ kín
            canvas.bind('<Configure>', lambda e, cv=canvas, i=win_id: cv.itemconfig(i, width=e.width))
            info['canvas'] = canvas
        else:
            canvas = None
            rows_frame = tk.Frame(box, bg=BG)
            rows_frame.pack(fill='x')
        wheel = (lambda e, cv=canvas, n=name: self.on_wheel(e, cv, n)) if scroll else None
        if wheel:
            for w in (canvas, rows_frame, head) + tuple(head_cells):
                w.bind('<MouseWheel>', wheel)

        now = time.time()
        row_cells = []
        for ri, st in enumerate(matches):
            bg = NEW_BG if self.new_until.get(st['symbol'], 0) > now else (ALT if ri % 2 == 1 else BG)
            for ci, (key, _) in enumerate(cols):
                text, tone = core.format_cell(st, key)
                lbl = tk.Label(rows_frame, text=text, bg=bg, fg=TONE.get(tone, TEXT),
                               font=FONT_BOLD if key == 'symbol' else FONT,
                               anchor='w' if ci == 0 else 'e', padx=8)
                lbl.grid(row=ri, column=ci, sticky='ew')
                self._bind_table(lbl)
                if wheel:
                    lbl.bind('<MouseWheel>', wheel)
                row_cells.append((ci, lbl))
        tk.Frame(box, bg=BG, height=4).pack(fill='x')

        # Đo bề ngang từng cột (lấy max của tiêu đề + mọi hàng) để tiêu đề và hàng thẳng cột với nhau
        widths = [lbl.winfo_reqwidth() for lbl in head_cells]
        row_h = 0
        for ci, lbl in row_cells:
            widths[ci] = max(widths[ci], lbl.winfo_reqwidth())
            row_h = max(row_h, lbl.winfo_reqheight())
        info.update(widths=widths, grids=[head, rows_frame], row_h=row_h, n=len(matches), limit=limit)
        return info

    def _align_sections(self, built):
        """Đặt bề ngang cột cho từng khối; khối hẹp được kéo cột cuối cho bằng khối rộng nhất."""
        widest = max([sum(b['widths']) for b in built if b.get('widths')] + [0])
        for b in built:
            if not b.get('widths'):
                continue
            widths = list(b['widths'])
            widths[-1] += widest - sum(widths)
            for g in b['grids']:
                for ci, w in enumerate(widths):
                    g.grid_columnconfigure(ci, minsize=w, weight=1 if ci == len(widths) - 1 else 0)
            rows_frame = b['grids'][1]
            for ri in range(b['n']):
                rows_frame.grid_rowconfigure(ri, minsize=b['row_h'])
            cv = b.get('canvas')
            if cv is not None:
                cv.config(width=widest, height=b['row_h'] * b['limit'], yscrollincrement=b['row_h'],
                          scrollregion=(0, 0, widest, b['row_h'] * b['n']))

    def toggle_section(self, name):
        col = list(self.cfg.get('collapsed', []))
        if name in col:
            col.remove(name)
        else:
            col.append(name)
        self.cfg['collapsed'] = col
        save_json(CONFIG_PATH, self.cfg)
        self.render()

    def resize_section(self, name, delta, n):
        rows = dict(self.cfg.get('sectionRows', {}))
        cur = self.section_rows(name, True)
        rows[name] = max(2, min(cur + delta, max(n, 2), 40))
        self.cfg['sectionRows'] = rows
        save_json(CONFIG_PATH, self.cfg)
        self.render()

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
        geo = f'{w}x{h}+{int(right - w)}+{int(bottom - h)}'
        if geo != getattr(self, '_last_geo', None):
            self.root.geometry(geo)
            self._last_geo = geo

    # ── Tương tác ──
    def sort_of(self, crit):
        """(cột, chiều) đang xếp của 1 tiêu chí; chưa có kiểu riêng thì theo kiểu chung."""
        return (crit.get('sortColumn') or self.cfg.get('sortColumn'),
                crit.get('sortDirection') or self.cfg.get('sortDirection'))

    def sort_by(self, key, crit):
        """Bấm tiêu đề cột: chỉ đổi cách xếp của tiêu chí đó, các tiêu chí khác giữ nguyên."""
        crit['sortColumn'], crit['sortDirection'] = core.next_sort(*self.sort_of(crit), key)
        save_json(CONFIG_PATH, self.cfg)           # crit chính là phần tử trong cfg['criteria']
        self.scroll_pos.pop(crit['name'], None)    # xếp lại thì khối đó về đầu; khối khác giữ vị trí cuộn
        self.compute()
        self.render()

    def toggle_mode(self):
        self.cfg['mode'] = 'compact' if self.cfg['mode'] == 'full' else 'full'
        save_json(CONFIG_PATH, self.cfg)
        self.render()

    def on_wheel(self, e, canvas=None, name=None):
        """Lăn chuột trên khối nào chỉ cuộn danh sách của khối đó — không vẽ lại gì nên không nháy."""
        if canvas is None:
            return
        canvas.yview_scroll(-WHEEL_ROWS if e.delta > 0 else WHEEL_ROWS, 'units')
        self.scroll_pos[name] = canvas.yview()[0]
        return 'break'

    def drag_start(self, e):
        self.drag = (e.x_root - self.root.winfo_x(), e.y_root - self.root.winfo_y())

    def drag_move(self, e):
        if self.drag:
            self.root.geometry(f'+{e.x_root - self.drag[0]}+{e.y_root - self.drag[1]}')
            self._last_geo = None

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
        self.scroll_pos = {}
        self.compute()
        self.render()

    # ── Lấy dữ liệu (luồng nền) ──
    def quote_loop(self):
        while True:
            try:
                quotes = core.fetch_quotes(SYMBOLS)
                slim = [{k: q.get(k) for k in ('Symbol', 'Name', 'Exchange', 'PriceCurrent', 'PriceChange',
                                               'PricePercentChange', 'TotalVolume', 'TotalValue',
                                               'TotalActiveBuyVolume', 'PriceAverage', 'Date', 'PriceHigh', 'PriceLow',
                                               'PriceCeiling', 'PriceFloor',
                                               'BuyForeignQuantity', 'SellForeignQuantity',
                                               'BuyForeignValue', 'SellForeignValue')} for q in quotes]
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

    def tech_loop(self):
        """Thống kê kỹ thuật từ nến ngày VNDirect (~1 phút cho cả thị trường). Chỉ tải khi có tiêu chí cần,
        mỗi ngày một lần; mã nào lỗi mạng thì 10 phút sau thử lại."""
        while True:
            try:
                if any(core.needs_tech(c) for c in self.cfg['criteria']):
                    today = core.vn_date(time.time())
                    cur = self.tech if self.tech.get('day') == today else {'day': today, 'data': {}}
                    if len(cur['data']) < len(SYMBOLS):
                        data = core.fetch_all_tech(SYMBOLS, today, cur['data'],
                                                   on_progress=lambda p: self.q.put(('tech_progress', p)))
                        cur = {'day': today, 'data': data}
                        save_json(TECH_PATH, cur)
                        self.q.put(('tech', cur, len(data) / len(SYMBOLS)))
            except Exception:
                log('tech: ' + traceback.format_exc())
            self.wake_tech.wait(HIST_CHECK_SEC)
            self.wake_tech.clear()

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
                    # MA / KL trung bình vừa có (hoặc đổi nguồn) → tiêu chí dùng % KL/TB, MA bỗng khớp thêm cả
                    # loạt mã; đó không phải "mã mới lọt lọc" → lấy lại mốc so, không báo.
                    self.prev_by_key = None
                    self.compute()
                elif kind == 'tech':
                    self.tech, self.tech_progress = payload
                    # Chỉ báo vừa có → cả loạt mã bỗng khớp; đó không phải "mã mới lọt lọc" → lấy lại mốc so, không báo
                    self.prev_by_key = None
                    self.compute()
                elif kind == 'tech_progress':
                    self.tech_progress = payload[0]
                    if not self.tech_pending():
                        continue
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
        outer = ttk.Frame(w, padding=14)
        outer.pack(fill='both')
        body = ttk.Frame(outer)                  # cột trái: các dòng lọc + điều kiện đã thêm
        body.grid(row=0, column=0, sticky='nw')
        side = ttk.Frame(outer)                  # cột phải: thêm điều kiện + cài đặt chung
        side.grid(row=0, column=1, sticky='nw', padx=(28, 0))

        # Bản nháp các tiêu chí — sửa thoải mái, bấm Lưu mới áp dụng
        self.crits = copy.deepcopy(cfg['criteria'])
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

        ttk.Label(body, text='Khi có mã mới').grid(row=5, column=0, sticky='w', pady=2)
        self.alert = ttk.Combobox(body, state='readonly', width=16, values=[n for _, n in ALERT_LABEL])
        self.alert.grid(row=5, column=1, sticky='w', pady=2)
        ttk.Button(body, text='Nghe thử', command=self.test_alert).grid(row=5, column=2, sticky='w', pady=2)

        # Kiểu xếp là của TỪNG tiêu chí (bấm tiêu đề cột trên bảng giá cũng chỉ đổi tiêu chí đó)
        ttk.Label(body, text='Sắp xếp theo').grid(row=6, column=0, sticky='w', pady=2)
        self.sort_col = ttk.Combobox(body, state='readonly', width=16, values=[l for _, l in SORT_COLUMNS])
        self.sort_col.grid(row=6, column=1, sticky='w', pady=2)
        self.sort_dir = ttk.Combobox(body, state='readonly', width=12, values=['Giảm dần', 'Tăng dần'])
        self.sort_dir.grid(row=6, column=2, sticky='w', pady=2)

        self.rows = {}
        op_names = [n for _, n in OP_LABEL]
        for i, (key, label) in enumerate(core.FILTERABLE, start=7):
            ttk.Label(body, text=label).grid(row=i, column=0, sticky='w', pady=2)
            op = ttk.Combobox(body, state='readonly', width=16, values=op_names)
            op.grid(row=i, column=1, sticky='w', padx=(0, 8), pady=2)
            val = ttk.Entry(body, width=14)
            val.grid(row=i, column=2, sticky='w', pady=2)
            self.rows[key] = (op, val)

        # Điều kiện thêm hiện ngay dưới các dòng lọc, cùng một danh sách (cột trái dài ra theo số điều kiện)
        r = 7 + len(core.FILTERABLE)
        ttk.Label(body, text='Điều kiện đã thêm', font=('Segoe UI', 9, 'bold')) \
            .grid(row=r, column=0, columnspan=3, sticky='w', pady=(10, 2))
        self.extra_list = ttk.Frame(body)
        self.extra_list.grid(row=r + 1, column=0, columnspan=3, sticky='ew')
        self.build_extra(side)
        self.load_form()

        # Cài đặt chung nằm cột phải, dưới bộ chọn → cửa sổ không cao thêm khi danh sách bên trái dài ra
        ttk.Separator(side).pack(fill='x', pady=12)
        gen = ttk.Frame(side)
        gen.pack(anchor='w', fill='x')
        ttk.Label(gen, text='Độ trong suốt').grid(row=0, column=0, sticky='w', pady=2)
        self.opacity = tk.DoubleVar(value=cfg.get('opacity', 1.0))
        ttk.Scale(gen, from_=0.5, to=1.0, variable=self.opacity, length=150).grid(row=0, column=1, sticky='w', padx=(8, 0))

        self.startup = tk.BooleanVar(value=has_startup())
        ttk.Checkbutton(gen, text='Tự mở khi bật máy', variable=self.startup) \
            .grid(row=1, column=0, columnspan=3, sticky='w', pady=2)

        ttk.Separator(side).pack(fill='x', pady=12)
        ttk.Label(side, text='Sheet cookie FireAnt (tuỳ chọn)', font=('Segoe UI', 9, 'bold')).pack(anchor='w')
        ttk.Label(side, text='Dán link Google Sheet có cookie FireAnt ở ô D2 sheet "Dashboard" → cột MA lấy '
                             'thẳng FireAnt. Để trống → MA tự tính từ VNDirect.', foreground='#666',
                  wraplength=390, justify='left').pack(anchor='w', pady=(2, 4))
        self.sheet = ttk.Entry(side, width=52)
        self.sheet.insert(0, cfg.get('cookieSheetId') or '')
        self.sheet.pack(fill='x')

        btns = ttk.Frame(outer)
        btns.grid(row=1, column=0, columnspan=2, sticky='e', pady=(12, 0))
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
        # Nghe thử đúng tiêu chí đang sửa: 2 mã đầu đang khớp tiêu chí đó, chưa có thì lấy mã mẫu
        name = self.crit_name.get().strip() or self.crits[self.cur]['name']
        orig = self.crits[self.cur]['name']
        syms = next(([st['symbol'] for st in m[:2]] for c, m in self.app.sections if c['name'] == orig), [])
        mode = self.alert_mode()
        if mode == 'off':
            messagebox.showinfo(APP_NAME, f'Tiêu chí "{name}" đang để Im lặng: có mã mới chỉ sáng vàng, không kêu.',
                                parent=self.win)
            return
        self.app.alert([(name, syms or ['VIB', 'MBB'], mode)], names=len(self.crits) > 1)

    # ── Điều kiện thêm (kiểu FireAnt): chọn nhóm → chọn điều kiện → đặt giá trị → ＋ Thêm ──
    def build_extra(self, p):
        """Bộ chọn trong cột phải: chọn nhóm → điều kiện → đặt giá trị → ＋ Thêm (điều kiện hiện ở danh sách bên trái)."""
        ttk.Label(p, text='Thêm điều kiện', font=('Segoe UI', 11, 'bold')).pack(anchor='w')
        ttk.Label(p, text='Chọn nhóm → điều kiện → đặt giá trị → ＋ Thêm.\nĐiều kiện sẽ hiện ở danh sách bên trái.\n'
                          'Cần lịch sử giá (RSI, MACD, SMA, đỉnh/đáy…): lần đầu dùng sẽ tải ~1 phút.',
                  foreground='#666', wraplength=390, justify='left').pack(anchor='w', pady=(2, 6))
        self.catalog = conditions.catalog()
        self.group_ids = [g for g, _ in conditions.GROUPS]
        self.grp_box = ttk.Combobox(p, state='readonly', width=44, values=[n for _, n in conditions.GROUPS])
        self.grp_box.pack(anchor='w', pady=(4, 3))
        self.grp_box.bind('<<ComboboxSelected>>', self.on_group)
        self.cond_box = ttk.Combobox(p, state='readonly', width=44)
        self.cond_box.pack(anchor='w')
        self.cond_box.bind('<<ComboboxSelected>>', self.on_cond)
        self.add_form = ttk.Frame(p)
        self.add_form.pack(anchor='w', pady=(8, 0))
        self.cond_items, self.form = [], None

    def on_group(self, _=None):
        self.cond_items = self.catalog[self.group_ids[self.grp_box.current()]]
        self.cond_box['values'] = [t for t, _, _ in self.cond_items]
        self.cond_box.set('')
        self.clear_form()

    def on_cond(self, _=None):
        i = self.cond_box.current()
        if i >= 0:
            _, kind, key = self.cond_items[i]
            self.build_form(kind, key)

    def clear_form(self):
        for w in self.add_form.winfo_children():
            w.destroy()
        self.form = None

    def build_form(self, kind, key):
        """Dựng ô nhập cho điều kiện vừa chọn: cột số → toán tử + giá trị (+ giá trị thứ hai); tín hiệu → các tham số."""
        self.clear_form()
        f = self.add_form
        widgets = {}
        n = 0                                   # số dòng ô nhập đã dựng
        if kind == 'metric':
            op = ttk.Combobox(f, state='readonly', width=14, values=[n_ for _, n_ in METRIC_OP_LABEL])
            op.current(0)
            op.grid(row=0, column=0, sticky='w', pady=2)
            v1 = ttk.Entry(f, width=12)
            v1.grid(row=0, column=1, sticky='w', padx=(6, 0))
            unit = METRIC_UNIT.get(conditions.METRIC_FMT[key])
            if unit:
                ttk.Label(f, text=unit, foreground='#666').grid(row=0, column=2, sticky='w', padx=6)
            to = ttk.Label(f, text='đến')
            v2 = ttk.Entry(f, width=12)

            def toggle(_=None):
                if METRIC_OP_LABEL[op.current()][0] == 'bt':
                    to.grid(row=1, column=0, sticky='e', pady=2)
                    v2.grid(row=1, column=1, sticky='w', padx=(6, 0))
                else:
                    to.grid_remove()
                    v2.grid_remove()
            op.bind('<<ComboboxSelected>>', toggle)
            widgets = (op, v1, v2)
            n = 2
        else:
            for p in conditions.SIGNALS[key].params:
                ttk.Label(f, text=p.name).grid(row=n, column=0, sticky='e', pady=2)
                cb = ttk.Combobox(f, state='normal' if p.free else 'readonly', width=12,
                                  values=[conditions.param_text(c) for c in p.choices])
                cb.set(conditions.param_text(p.default))
                cb.grid(row=n, column=1, sticky='w', padx=(6, 0))
                widgets[p.id] = cb
                n += 1
        ttk.Button(f, text='＋ Thêm', command=self.add_condition).grid(row=n, column=0, columnspan=2, sticky='w', pady=(6, 0))
        self.form = (kind, key, widgets)

    def add_condition(self):
        if not self.form:
            return
        kind, key, w = self.form
        c = self.crits[self.cur]
        if kind == 'metric':
            op, v1, v2 = w
            code = METRIC_OP_LABEL[op.current()][0]
            try:
                f = {'operator': code, 'value': float(v1.get().strip().replace(',', '.'))}
                if code == 'bt':
                    f['value2'] = float(v2.get().strip().replace(',', '.'))
            except ValueError:
                messagebox.showwarning(APP_NAME, 'Hãy nhập số vào ô giá trị.', parent=self.win)
                return
            c['filters'][key] = f                      # cùng một cột chỉ có 1 điều kiện — thêm lại là thay
        else:
            params = {}
            for p in conditions.SIGNALS[key].params:
                raw = w[p.id].get().strip()
                if p.free:
                    try:
                        v = float(raw.replace(',', '.'))
                    except ValueError:
                        messagebox.showwarning(APP_NAME, f'"{p.name}" phải là số.', parent=self.win)
                        return
                    if not p.lo <= v <= p.hi:
                        messagebox.showwarning(APP_NAME, f'"{p.name}" phải từ {conditions.param_text(p.lo)} '
                                                         f'đến {conditions.param_text(p.hi)}.', parent=self.win)
                        return
                else:
                    shown = [conditions.param_text(x) for x in p.choices]
                    v = p.choices[shown.index(raw)] if raw in shown else p.default
                params[p.id] = v
            s = conditions.normalize_signal({'id': key, 'params': params})
            if any(float(s['params'][k]) != float(v) for k, v in params.items() if not isinstance(v, str)):
                messagebox.showwarning(APP_NAME, 'SMA ngắn phải ngắn hơn SMA dài.', parent=self.win)
                return
            sigs = c.setdefault('signals', [])
            if s not in sigs:
                sigs.append(s)
        self.refresh_extra()
        self.cond_box.set('')            # thêm xong → bỏ chọn, thấy rõ điều kiện đã sang danh sách bên trái
        self.clear_form()

    def refresh_extra(self):
        for w in self.extra_list.winfo_children():
            w.destroy()
        c = self.crits[self.cur]
        items = [(core.describe_filters({k: c['filters'][k]}), lambda k=k: self.drop_filter(k))
                 for k in core.active_filter_keys(c['filters']) if k not in core.LEGACY_KEYS]
        items += [(conditions.describe_signal(s), lambda i=i: self.drop_signal(i))
                  for i, s in enumerate(c.get('signals') or [])]
        if not items:
            ttk.Label(self.extra_list, text='(chưa có — chọn ở cột bên phải)', foreground='#888').pack(anchor='w')
        for text, cmd in items:
            row = ttk.Frame(self.extra_list)
            row.pack(fill='x')
            x = ttk.Label(row, text='✕', foreground='#888', cursor='hand2', padding=(4, 1))
            x.pack(side='left')
            x.bind('<Button-1>', lambda e, c=cmd: c())
            x.bind('<Enter>', lambda e, w=x: w.config(foreground='#dc2626'))
            x.bind('<Leave>', lambda e, w=x: w.config(foreground='#888'))
            ttk.Label(row, text=text, wraplength=480, justify='left').pack(side='left', padx=(4, 0))

    def drop_filter(self, key):
        self.crits[self.cur]['filters'].pop(key, None)
        self.refresh_extra()

    def drop_signal(self, i):
        c = self.crits[self.cur]
        del c['signals'][i]
        if not c['signals']:
            del c['signals']
        self.refresh_extra()

    # ── Bản nháp tiêu chí ──
    def load_form(self):
        c = self.crits[self.cur]
        self.crit_box['values'] = [x['name'] for x in self.crits]
        self.crit_box.current(self.cur)
        self.crit_name.delete(0, 'end')
        self.crit_name.insert(0, c['name'])
        self.exchange.set(EXCHANGE_LABEL.get(c['exchange'], 'HSX'))
        self.alert.set(dict(ALERT_LABEL).get(c.get('alert', 'speak'), ALERT_LABEL[0][1]))
        self.sort_col.set(dict(SORT_COLUMNS).get(c.get('sortColumn'), core.LABEL['value']))
        self.sort_dir.set('Tăng dần' if c.get('sortDirection') == 'asc' else 'Giảm dần')
        op_label = dict(OP_LABEL)
        for key, (op, val) in self.rows.items():
            f = c['filters'].get(key) or {}
            op.set(op_label.get(f.get('operator', 'gt'), OP_LABEL[0][1]))
            val.delete(0, 'end')
            if f.get('value') not in (None, ''):
                val.insert(0, core.js_num(f['value']))
        self.refresh_extra()

    def store_form(self):
        """Ghi ô đang sửa vào bản nháp. Trả False (và báo) nếu có ô không phải số."""
        name_to_op = {n: k for k, n in OP_LABEL}
        cur = self.crits[self.cur]
        # Điều kiện thêm sửa thẳng trên bản nháp (không có ô cố định) → giữ nguyên
        filters = {k: v for k, v in cur['filters'].items() if k not in core.LEGACY_KEYS}
        bad = []
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
        label_to_col = {l: k for k, l in SORT_COLUMNS}
        new = {'name': self.crit_name.get().strip() or f'Tiêu chí {self.cur + 1}',
               'exchange': label_to_ex.get(self.exchange.get(), 'HSX'),
               'filters': filters,
               'alert': self.alert_mode(),
               'sortColumn': label_to_col.get(self.sort_col.get(), 'value'),
               'sortDirection': 'asc' if self.sort_dir.get() == 'Tăng dần' else 'desc'}
        if cur.get('signals'):
            new['signals'] = cur['signals']
        self.crits[self.cur] = new
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
        cur = self.crits[self.cur]
        self.crits.append({'name': f'Tiêu chí {n}', 'exchange': cur['exchange'], 'filters': {},
                           'alert': cur.get('alert', 'speak'),
                           'sortColumn': cur.get('sortColumn', 'value'), 'sortDirection': cur.get('sortDirection', 'desc')})
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
        self.app.apply_settings({
            'criteria': copy.deepcopy(self.crits),
            'opacity': round(self.opacity.get(), 2),
            'cookieSheetId': sheet,
        })
        self.app.hist['source'] = None   # đổi sheet → thử lại FireAnt ngay
        self.app.wake_hist.set()
        self.app.wake_tech.set()         # vừa thêm điều kiện cần chỉ báo kỹ thuật → bắt đầu tải ngay
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
