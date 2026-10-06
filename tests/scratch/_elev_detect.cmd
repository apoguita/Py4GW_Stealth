@echo off
rem Detection test: can a process launched *elevated from this session* see the game, even though the
rem agent's own sandboxed shell cannot? Prints what it finds; calls nothing.
set PY=C:\Users\Apo\AppData\Local\Programs\Python\Python313-32\python.exe
cd /d C:\Users\Apo\Py4GW_Stealth
echo === detect: started %DATE% %TIME% === > tests/live_reports\_detect.txt
"%PY%" -c "import sys; sys.path.insert(0, r'C:\Users\Apo\Py4GW_Stealth'); import psutil" >> tests/live_reports\_detect.txt 2>&1
"%PY%" -c "import sys; sys.path.insert(0, r'C:\Users\Apo\Py4GW_Stealth'); from py4gw.win32 import Win32; w=Win32(); print('elevated:', w.is_elevated()); c=w.find_guild_wars(); print('clients:', [(x['pid'], hex(int(x['base_address']))) for x in c])" >> tests/live_reports\_detect.txt 2>&1
tasklist /FI "IMAGENAME eq Gw.exe" >> tests/live_reports\_detect.txt 2>&1
echo === detect: exit=%ERRORLEVEL% === >> tests/live_reports\_detect.txt
