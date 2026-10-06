@echo off
rem Elevated, ACTIVE: try each candidate travel UIMessage id, one at a time, with real waits.
rem WATCH THE SCREEN and note which id shows "you cannot travel to this map".
set PY=C:\Users\Apo\AppData\Local\Programs\Python\Python313-32\python.exe
cd /d C:\Users\Apo\Py4GW_Stealth
echo === travel id sweep: started %DATE% %TIME% === > tests/live_reports\travel_id_sweep.log
"%PY%" -u tests/scratch\1_travel_id_sweep.py --target 55 >> tests/live_reports\travel_id_sweep.log 2>&1
echo === travel id sweep: exit=%ERRORLEVEL% === >> tests/live_reports\travel_id_sweep.log
