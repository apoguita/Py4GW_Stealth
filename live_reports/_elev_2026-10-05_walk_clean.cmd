@echo off
REM Elevated: the owner's pathing test against the CLEAN client (no injected runtime), so the only
REM extra variable left is this project's own connection. Take the player's position, ask for a path
REM 500 units in front, walk the result one waypoint at a time, waiting for each arrival.
REM This MOVES the character.
cd /d C:\Users\Apo\Py4GW_Stealth
set PY=C:\Users\Apo\AppData\Local\Programs\Python\Python313-32\python.exe
echo === pathing walk (clean client): start %DATE% %TIME% === > live_reports\pathing_walk_clean.log
"%PY%" tests\probe_pathing_walk.py live_reports\pathing_walk_clean.json --pid 8456 >> live_reports\pathing_walk_clean.log 2>&1
echo walk_exit=%ERRORLEVEL% >> live_reports\pathing_walk_clean.log
echo === done %DATE% %TIME% === >> live_reports\pathing_walk_clean.log
