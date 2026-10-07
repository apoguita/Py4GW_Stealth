@echo off
cd /d C:\Users\Apo\Py4GW_Stealth
set PY=C:\Users\Apo\AppData\Local\Programs\Python\Python313-32\python.exe
echo === quest member flip + log names: start %DATE% %TIME% === > tests\live_reports\quest_member_live.log
"%PY%" tests\probe_quest_live.py act tests\live_reports\quest_member_live.json --names --set-active 1098 >> tests\live_reports\quest_member_live.log 2>&1
echo member_exit=%ERRORLEVEL% >> tests\live_reports\quest_member_live.log
