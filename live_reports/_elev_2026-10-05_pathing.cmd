@echo off
REM Elevated: the two pathing live stages that have no post-update evidence.
REM   1. tests/probe_pathing_finder.py  -- written 2026-10-01, never run.
REM   2. tests/probe_pathing_live.py act -- last run 2026-09-30, before the client update.
REM Both connect (which chains on Reforged's entry jumps), call, and remove their hooks.
cd /d C:\Users\Apo\Py4GW_Stealth
set PY=C:\Users\Apo\AppData\Local\Programs\Python\Python313-32\python.exe

echo === finder diagnostic: start %DATE% %TIME% === > live_reports\pathing_finder_diagnostic.log
"%PY%" tests\probe_pathing_finder.py live_reports\pathing_finder_diagnostic.json >> live_reports\pathing_finder_diagnostic.log 2>&1
echo finder_exit=%ERRORLEVEL% >> live_reports\pathing_finder_diagnostic.log

echo === pathing act: start %DATE% %TIME% === > live_reports\pathing_act_2026-10-05.log
"%PY%" tests\probe_pathing_live.py act live_reports\pathing_act_2026-10-05.json >> live_reports\pathing_act_2026-10-05.log 2>&1
echo act_exit=%ERRORLEVEL% >> live_reports\pathing_act_2026-10-05.log

echo === done %DATE% %TIME% === >> live_reports\pathing_act_2026-10-05.log
