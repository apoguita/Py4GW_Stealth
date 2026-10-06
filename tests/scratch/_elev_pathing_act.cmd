@echo off
rem Elevated run: the pathing act stage — the port's PathPlanner and AutoPathing.get_path calling the
rem client's own find_path_func. Bounded: a path is computed, never walked.
set PY=C:\Users\Apo\AppData\Local\Programs\Python\Python313-32\python.exe
cd /d C:\Users\Apo\Py4GW_Stealth
echo === pathing act: started %DATE% %TIME% === > tests/live_reports\pathing_act_run.txt
"%PY%" tests\probe_pathing_live.py act tests/live_reports\pathing_act_live.json >> tests/live_reports\pathing_act_run.txt 2>&1
echo === pathing act: exit=%ERRORLEVEL% === >> tests/live_reports\pathing_act_run.txt
