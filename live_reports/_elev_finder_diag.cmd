@echo off
rem Elevated run: the finder diagnostic. Four calls to the client's own path finder, each with the
rem count word pre-filled with a sentinel and the answer array filled with 0xCC, so the report says
rem whether the client wrote anything at all — and whether zplane or a real portal goal changes it.
set PY=C:\Users\Apo\AppData\Local\Programs\Python\Python313-32\python.exe
cd /d C:\Users\Apo\Py4GW_Stealth
echo === finder diagnostic: started %DATE% %TIME% === > live_reports\pathing_finder_diag.txt
"%PY%" tests\probe_pathing_finder.py live_reports\pathing_finder_diagnostic.json >> live_reports\pathing_finder_diag.txt 2>&1
echo === finder diagnostic: exit=%ERRORLEVEL% === >> live_reports\pathing_finder_diag.txt
