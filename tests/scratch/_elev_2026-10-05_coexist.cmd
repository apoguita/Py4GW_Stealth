@echo off
REM Elevated: the committed coexistence test, against a client that already has Reforged injected.
REM This is the arrangement the probe guards were refusing. Nothing else is run here.
cd /d C:\Users\Apo\Py4GW_Stealth
set PY=C:\Users\Apo\AppData\Local\Programs\Python\Python313-32\python.exe
echo === coexistence: start %DATE% %TIME% === > tests/live_reports\live_coexistence_2026-10-05.txt
"%PY%" -m unittest tests.test_live_coexistence -v >> tests/live_reports\live_coexistence_2026-10-05.txt 2>&1
echo coexist_exit=%ERRORLEVEL% >> tests/live_reports\live_coexistence_2026-10-05.txt
echo === done %DATE% %TIME% === >> tests/live_reports\live_coexistence_2026-10-05.txt
