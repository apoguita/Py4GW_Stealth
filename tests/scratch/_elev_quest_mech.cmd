@echo off
cd /d C:\Users\Apo\Py4GW_Stealth
set PY=C:\Users\Apo\AppData\Local\Programs\Python\Python313-32\python.exe
echo === quest mechanism diagnostic: start %DATE% %TIME% === > tests\live_reports\quest_mechanism_live.log
"%PY%" tests\probe_quest_live.py act tests\live_reports\quest_mechanism_live.json --quest 1098 --set-active-via-call 167 --restore-active 1098 >> tests\live_reports\quest_mechanism_live.log 2>&1
echo diag_exit=%ERRORLEVEL% >> tests\live_reports\quest_mechanism_live.log
