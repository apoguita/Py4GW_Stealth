@echo off
cd /d C:\Users\Apo\Py4GW_Stealth
set PY=C:\Users\Apo\AppData\Local\Programs\Python\Python313-32\python.exe
echo === quest abandon (single permitted run): start %DATE% %TIME% === > tests\live_reports\quest_abandon_live.log
"%PY%" tests\probe_quest_live.py act tests\live_reports\quest_abandon_live.json --abandon 1432 >> tests\live_reports\quest_abandon_live.log 2>&1
echo abandon_exit=%ERRORLEVEL% >> tests\live_reports\quest_abandon_live.log
