"""
Phát hành bản mới cho các máy khác tự cập nhật (nút ⬆ Cập nhật).

  python tools/release.py "Ghi chú có gì mới"

Làm lần lượt:
  1. chạy test — đỏ thì dừng;
  2. đóng gói dist/BeeVnMini.exe (PyInstaller);
  3. đẩy mã nguồn nhánh main lên GitHub;
  4. ghi đè nhánh "release" chỉ gồm BeeVnMini.exe + latest.json (số phiên bản, mã kiểm tra sha256).
     Ghi đè (force) để kho không phình thêm 11 MB mỗi lần phát hành.

Trước khi chạy: tăng APP_VERSION trong beevn_mini.pyw — cùng số với bản đang có thì máy khác
không thấy gì mới.
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REMOTE = 'git@github.com:stevesinek1702/BeeVnMini.git'
RAW = 'https://raw.githubusercontent.com/stevesinek1702/BeeVnMini/release/'
EXE = os.path.join(ROOT, 'dist', 'BeeVnMini.exe')


def run(cmd, cwd=ROOT):
    print('>', ' '.join(cmd))
    subprocess.run(cmd, cwd=cwd, check=True)


def main():
    notes = ' '.join(sys.argv[1:]).strip()
    src = open(os.path.join(ROOT, 'beevn_mini.pyw'), encoding='utf-8').read()
    version = re.search(r"APP_VERSION = os\.environ\.get\('BEEVN_FAKE_VERSION'\) or '([\d.]+)'", src).group(1)
    print(f'Phát hành v{version}')

    run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-t', '.'])
    run([sys.executable, '-m', 'PyInstaller', '--noconfirm', '--onefile', '--windowed', '--name', 'BeeVnMini',
         '--icon', 'beevn.ico', '--add-data', 'beevn.ico;.', '--add-data', 'speak.ps1;.',
         '--distpath', 'dist', '--workpath', 'build', '--log-level', 'WARN', 'beevn_mini.pyw'])

    data = open(EXE, 'rb').read()
    latest = {'version': version, 'url': RAW + 'BeeVnMini.exe', 'size': len(data),
              'sha256': hashlib.sha256(data).hexdigest(), 'notes': notes}

    run(['git', 'push', REMOTE, 'main'])

    tmp = tempfile.mkdtemp(prefix='beevn-release-')
    try:
        shutil.copy2(EXE, os.path.join(tmp, 'BeeVnMini.exe'))
        with open(os.path.join(tmp, 'latest.json'), 'w', encoding='utf-8') as f:
            json.dump(latest, f, ensure_ascii=False, indent=2)
        with open(os.path.join(tmp, 'README.md'), 'w', encoding='utf-8') as f:
            f.write(f'# Bee.vn mini v{version}\n\nTải [BeeVnMini.exe]({RAW}BeeVnMini.exe), bấm đúp để cài.\n\n'
                    f'{notes}\n')
        run(['git', 'init', '-q', '-b', 'release'], cwd=tmp)
        run(['git', 'add', '-A'], cwd=tmp)
        run(['git', '-c', 'user.name=stevesinek1702', '-c', 'user.email=noreply@users.noreply.github.com',
             'commit', '-q', '-m', f'Bee.vn mini v{version}'], cwd=tmp)
        run(['git', 'push', '--force', REMOTE, 'release'], cwd=tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print(f'\nXong v{version}: {RAW}latest.json')


if __name__ == '__main__':
    main()
