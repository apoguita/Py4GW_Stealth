@echo off
rem Elevated run #5: add a henchman and a hero to the party (the owner asked for this step). The
rem henchman's id is a live agent id, taken from the read-only finder's nearest candidate.
set PY=C:\Users\Apo\AppData\Local\Programs\Python\Python313-32\python.exe
cd /d C:\Users\Apo\Py4GW_Stealth
echo === party-add: started %DATE% %TIME% === > tests/live_reports\party_act_add_live.txt
"%PY%" tests\probe_party_live.py act tests/live_reports\party_act_add_live.json --allow party-add --hero Norgu --henchman 10 >> tests/live_reports\party_act_add_live.txt 2>&1
echo === party-add: exit=%ERRORLEVEL% === >> tests/live_reports\party_act_add_live.txt
