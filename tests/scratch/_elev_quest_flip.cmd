@echo off
cd /d C:\Users\Apo\Py4GW_Stealth
set PY=C:\Users\Apo\AppData\Local\Programs\Python\Python313-32\python.exe
echo === quest flip: start %DATE% %TIME% === > tests\live_reports\quest_flip_live.log
"%PY%" tests\probe_quest_live.py act tests\live_reports\quest_flip_live.json --quest 1098 --set-active 167 --restore-active 1098 >> tests\live_reports\quest_flip_live.log 2>&1
echo flip_exit=%ERRORLEVEL% >> tests\live_reports\quest_flip_live.log
echo === done %DATE% %TIME% === >> tests\live_reports\quest_flip_live.log
