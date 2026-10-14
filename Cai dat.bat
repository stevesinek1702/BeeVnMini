@echo off
rem Bam dup file nay: tao bieu tuong "Bee.vn mini" ngoai Desktop + tu chay khi bat may, roi mo chuong trinh.
set "PYW="
for /f "delims=" %%P in ('where pythonw 2^>nul') do if not defined PYW set "PYW=%%P"
if not defined PYW (
  echo Khong tim thay Python tren may. Cai Python tu https://www.python.org/downloads/ roi bam lai file nay.
  pause
  exit /b 1
)
start "" "%PYW%" "%~dp0beevn_mini.pyw" --install
