@echo off
rem Live coexistence run, direction A: the client already has Reforged injected.
rem This project must refuse to connect and write nothing at all.
cd /d C:\Users\Apo\Py4GW_Stealth
set PY=C:\Users\Apo\AppData\Local\Programs\Python\Python313-32\python.exe
"%PY%" -m unittest tests.test_live_coexistence.ReforgedFirstTests -v > live_reports\live_coexistence_reforged_first.txt 2>&1
echo EXITCODE=%ERRORLEVEL%>> live_reports\live_coexistence_reforged_first.txt
