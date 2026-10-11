@echo off
rem Elevated, READ-ONLY probe: how much of the client's agent element each record view materializes,
rem and whether GwAu3's own offsets can be read from it (or through the record's remote reader).
set PY=C:\Users\Apo\AppData\Local\Programs\Python\Python313-32\python.exe
cd /d C:\Users\Apo\Py4GW_Stealth
echo === agent view sizes: started %DATE% %TIME% === > tests/live_reports\agent_view_sizes.log
"%PY%" -u tests/scratch\1_probe_agent_view_sizes.py >> tests/live_reports\agent_view_sizes.log 2>&1
echo === exit=%ERRORLEVEL% === >> tests/live_reports\agent_view_sizes.log
