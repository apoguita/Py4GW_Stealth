@echo off
rem Elevated run #7: add a hero and a henchman, pause, then kick both — one pair, in one invocation, so
rem nothing can intervene between them. The probe spaces its own calls (0.5 s) and waits for the client
rem to show each change before reporting; the pauses here are between the two stages.
set PY=C:\Users\Apo\AppData\Local\Programs\Python\Python313-32\python.exe
cd /d C:\Users\Apo\Py4GW_Stealth
echo === add: started %DATE% %TIME% === > tests/live_reports\party_add_kick_pair.txt
"%PY%" tests\probe_party_live.py act tests/live_reports\party_act_add2_live.json --allow party-add --hero Norgu --henchman 10 >> tests/live_reports\party_add_kick_pair.txt 2>&1
echo === add: exit=%ERRORLEVEL% === >> tests/live_reports\party_add_kick_pair.txt
timeout /t 6 /nobreak >nul
"%PY%" tests\probe_party_live.py act tests/live_reports\party_act_kick2_live.json --allow party-kick --hero Norgu --henchman 10 >> tests/live_reports\party_add_kick_pair.txt 2>&1
echo === kick: exit=%ERRORLEVEL% === >> tests/live_reports\party_add_kick_pair.txt
