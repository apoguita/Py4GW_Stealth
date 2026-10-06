@echo off
rem Elevated run: read-only MapContext / CharContext layout probe.
rem Answers one question the 2026-09-30 update left open: where does MapContext REALLY keep
rem sub1 (pathing), props, terrain, zones and the map id on this client build.
rem Read-only: opens the client PROCESS_VM_READ, resolves context.base_ptr with the project's own
rem engine, and dumps. Writes nothing, hooks nothing, calls no client function.
set PY=C:\Users\Apo\AppData\Local\Programs\Python\Python313-32\python.exe
cd /d C:\Users\Apo\Py4GW_Stealth
echo === map layout probe: started %DATE% %TIME% === > tests/live_reports\map_layout_probe.log
"%PY%" tests/scratch\1_map_layout_probe.py --out tests/live_reports\map_layout_probe.json >> tests/live_reports\map_layout_probe.log 2>&1
echo === map layout probe: exit=%ERRORLEVEL% === >> tests/live_reports\map_layout_probe.log
