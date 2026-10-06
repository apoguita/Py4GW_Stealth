@echo off
rem Elevated run #8: put a hero and a henchman in the party, pause, then press leave once and watch.
rem Spaced out on purpose: the client processes one command at a time, and the leave press is a UI
rem button — it gets the client to itself.
set PY=C:\Users\Apo\AppData\Local\Programs\Python\Python313-32\python.exe
cd /d C:\Users\Apo\Py4GW_Stealth
echo === add: started %DATE% %TIME% === > tests/live_reports\party_leave_run.txt
"%PY%" tests\probe_party_live.py act tests/live_reports\party_act_add3_live.json --allow party-add --hero Norgu --henchman 10 >> tests/live_reports\party_leave_run.txt 2>&1
echo === add: exit=%ERRORLEVEL% === >> tests/live_reports\party_leave_run.txt
timeout /t 8 /nobreak >nul
"%PY%" tests\probe_party_leave.py >> tests/live_reports\party_leave_run.txt 2>&1
echo === leave: exit=%ERRORLEVEL% === >> tests/live_reports\party_leave_run.txt
