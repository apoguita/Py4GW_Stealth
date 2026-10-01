@echo off
rem Elevated run: drive the three travel actions and record what the client does.
rem ACTIVE - sends UI messages, so the client will change maps (hall -> out -> Lion's Arch).
rem -u keeps stdout unbuffered, so if the run is killed the log still shows where it stopped.
set PY=C:\Users\Apo\AppData\Local\Programs\Python\Python313-32\python.exe
cd /d C:\Users\Apo\Py4GW_Stealth
echo === travel actions: started %DATE% %TIME% === > live_reports\travel_actions_test.log
"%PY%" -u live_reports\_travel_actions_test.py --lions-arch 55 --settle 30 >> live_reports\travel_actions_test.log 2>&1
echo === travel actions: exit=%ERRORLEVEL% === >> live_reports\travel_actions_test.log
