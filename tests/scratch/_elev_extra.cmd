@echo off
rem Elevated run #4: the skill press (the control action, one key), and the difficulty step again —
rem which must now refuse with the reason, because this account has no hard mode unlocked.
set PY=C:\Users\Apo\AppData\Local\Programs\Python\Python313-32\python.exe
cd /d C:\Users\Apo\Py4GW_Stealth
echo === use-skill: started %DATE% %TIME% === > tests/live_reports\party_act_extra_live.txt
"%PY%" tests\probe_party_live.py act tests/live_reports\party_act_useskill_live.json --allow use-skill --hero-number 1 --slot 1 >> tests/live_reports\party_act_extra_live.txt 2>&1
echo === use-skill: exit=%ERRORLEVEL% === >> tests/live_reports\party_act_extra_live.txt
"%PY%" tests\probe_party_live.py act tests/live_reports\party_act_difficulty2_live.json --allow difficulty >> tests/live_reports\party_act_extra_live.txt 2>&1
echo === difficulty: exit=%ERRORLEVEL% === >> tests/live_reports\party_act_extra_live.txt
