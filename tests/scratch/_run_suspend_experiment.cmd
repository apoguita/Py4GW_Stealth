@echo off
rem Phase-by-phase attribution of the client's device-lost counters. Elevated. Patches nothing.
cd /d C:\Users\Apo\Py4GW_Stealth
set PY=C:\Users\Apo\AppData\Local\Programs\Python\Python313-32\python.exe
"%PY%" tests/scratch\1_suspend_experiment.py > tests/live_reports\suspend_experiment.txt 2>&1
echo EXITCODE=%ERRORLEVEL%>> tests/live_reports\suspend_experiment.txt
