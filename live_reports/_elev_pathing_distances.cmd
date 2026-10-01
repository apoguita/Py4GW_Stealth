@echo off
rem Elevated run: ask the client's own finder at three distances, to tell "the call is wrong" from
rem "the client has nothing to say about a goal inside the trapezoid the player already stands in".
rem One invocation per distance, spaced out: the client answers one call at a time.
set PY=C:\Users\Apo\AppData\Local\Programs\Python\Python313-32\python.exe
cd /d C:\Users\Apo\Py4GW_Stealth
echo === planner distances: started %DATE% %TIME% === > live_reports\pathing_distances.txt
"%PY%" tests\probe_pathing_live.py act live_reports\pathing_act_1500.json --goal-distance 1500 >> live_reports\pathing_distances.txt 2>&1
timeout /t 4 /nobreak >nul
"%PY%" tests\probe_pathing_live.py act live_reports\pathing_act_4000.json --goal-distance 4000 >> live_reports\pathing_distances.txt 2>&1
timeout /t 4 /nobreak >nul
"%PY%" tests\probe_pathing_live.py act live_reports\pathing_act_8000.json --goal-distance 8000 >> live_reports\pathing_distances.txt 2>&1
echo === planner distances: done %DATE% %TIME% === >> live_reports\pathing_distances.txt
