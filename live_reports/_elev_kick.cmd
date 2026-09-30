@echo off
rem Elevated run #6: kick the hero and the henchman that #5 added. One step, one invocation — the
rem client processes one command at a time, and the probe spaces its own calls out as well.
set PY=C:\Users\Apo\AppData\Local\Programs\Python\Python313-32\python.exe
cd /d C:\Users\Apo\Py4GW_Stealth
echo === party-kick: started %DATE% %TIME% === > live_reports\party_act_kick_live.txt
"%PY%" tests\probe_party_live.py act live_reports\party_act_kick_live.json --allow party-kick --hero Norgu --henchman 10 >> live_reports\party_act_kick_live.txt 2>&1
echo === party-kick: exit=%ERRORLEVEL% === >> live_reports\party_act_kick_live.txt
