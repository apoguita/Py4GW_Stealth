@echo off
rem Elevated, READ-ONLY: resolve the observer target live and compare with Gw.exe on disk.
set PY=C:\Users\Apo\AppData\Local\Programs\Python\Python313-32\python.exe
cd /d C:\Users\Apo\Py4GW_Stealth
echo === resolve check: started %DATE% %TIME% === > tests/live_reports\resolve_check.log
"%PY%" -u tests/scratch\1_observer_resolve_check.py >> tests/live_reports\resolve_check.log 2>&1
echo === resolve check: exit=%ERRORLEVEL% === >> tests/live_reports\resolve_check.log
