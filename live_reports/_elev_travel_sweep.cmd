@echo off
rem Elevated, ACTIVE: try each candidate travel UIMessage id, one at a time, with real waits.
rem WATCH THE SCREEN and note which id shows "you cannot travel to this map".
set PY=C:\Users\Apo\AppData\Local\Programs\Python\Python313-32\python.exe
cd /d C:\Users\Apo\Py4GW_Stealth
echo === travel id sweep: started %DATE% %TIME% === > live_reports\travel_id_sweep.log
"%PY%" -u live_reports\_travel_id_sweep.py --target 55 >> live_reports\travel_id_sweep.log 2>&1
echo === travel id sweep: exit=%ERRORLEVEL% === >> live_reports\travel_id_sweep.log
