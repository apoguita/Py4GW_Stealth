@echo off
cd /d C:\Users\Apo\Py4GW_Stealth
for /d %%D in (pytest-cache-files-*) do rmdir /s /q "%%D"
echo remaining: > tests\live_reports\_cleanup.txt
dir /b /ad pytest-cache-files-* >> tests\live_reports\_cleanup.txt 2>&1
