@echo off
cd /d C:\Users\Apo\Py4GW_Stealth
set PY=C:\Users\Apo\AppData\Local\Programs\Python\Python313-32\python.exe
echo === quest act: start %DATE% %TIME% === > tests\live_reports\quest_act_live.log
"%PY%" tests\probe_quest_live.py act tests\live_reports\quest_act_live.json >> tests\live_reports\quest_act_live.log 2>&1
echo act_exit=%ERRORLEVEL% >> tests\live_reports\quest_act_live.log
echo === done %DATE% %TIME% === >> tests\live_reports\quest_act_live.log
