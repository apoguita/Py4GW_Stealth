@echo off
rem Elevated run #3: repair the two fields the first act run left changed (from the recorded original
rem state), then prove the fixed probe by re-running the two flip-and-restore steps.
set PY=C:\Users\Apo\AppData\Local\Programs\Python\Python313-32\python.exe
cd /d C:\Users\Apo\Py4GW_Stealth
echo === repair: started %DATE% %TIME% === > live_reports\party_repair_and_proof.txt
"%PY%" tests\probe_party_restore.py >> live_reports\party_repair_and_proof.txt 2>&1
echo === repair: exit=%ERRORLEVEL% === >> live_reports\party_repair_and_proof.txt
"%PY%" tests\probe_party_live.py act live_reports\party_act_behaviour_live.json --allow behaviour >> live_reports\party_repair_and_proof.txt 2>&1
echo === behaviour: exit=%ERRORLEVEL% === >> live_reports\party_repair_and_proof.txt
"%PY%" tests\probe_party_live.py act live_reports\party_act_skillai_live.json --allow skill-ai >> live_reports\party_repair_and_proof.txt 2>&1
echo === skill-ai: exit=%ERRORLEVEL% === >> live_reports\party_repair_and_proof.txt
"%PY%" tests\probe_party_live.py act live_reports\party_act_difficulty_live.json --allow difficulty >> live_reports\party_repair_and_proof.txt 2>&1
echo === difficulty: exit=%ERRORLEVEL% === >> live_reports\party_repair_and_proof.txt
