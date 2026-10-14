@echo off
rem Bam dup file nay: xoa bieu tuong ngoai Desktop + bo tu chay khi bat may.
set "PYW="
for /f "delims=" %%P in ('where pythonw 2^>nul') do if not defined PYW set "PYW=%%P"
if not defined PYW exit /b 1
start "" "%PYW%" "%~dp0beevn_mini.pyw" --uninstall
