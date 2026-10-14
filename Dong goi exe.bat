@echo off
rem Dong goi lai file BeeVnMini.exe (sau khi sua code). Ket qua: thu muc dist\BeeVnMini.exe
cd /d "%~dp0"
python -m unittest discover -s tests -t . || (echo Test loi - khong dong goi. & pause & exit /b 1)
python -m PyInstaller --noconfirm --onefile --windowed --name BeeVnMini --icon beevn.ico --add-data "beevn.ico;." --add-data "speak.ps1;." --distpath dist --workpath build beevn_mini.pyw
echo.
echo Xong: %~dp0dist\BeeVnMini.exe
pause
