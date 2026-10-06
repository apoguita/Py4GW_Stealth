@echo off
REM Elevated: the owner's pathing test -- take the player's position, ask for a path 500 units in
REM front, and walk the resulting path. This MOVES the character. One connection, bounded walk.
cd /d C:\Users\Apo\Py4GW_Stealth
set PY=C:\Users\Apo\AppData\Local\Programs\Python\Python313-32\python.exe
echo === pathing walk: start %DATE% %TIME% === > tests/live_reports\pathing_walk.log
"%PY%" tests\probe_pathing_walk.py tests/live_reports\pathing_walk.json >> tests/live_reports\pathing_walk.log 2>&1
echo walk_exit=%ERRORLEVEL% >> tests/live_reports\pathing_walk.log
echo === done %DATE% %TIME% === >> tests/live_reports\pathing_walk.log
