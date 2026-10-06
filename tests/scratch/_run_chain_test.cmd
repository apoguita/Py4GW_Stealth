@echo off
rem Live coexistence run, direction B (the arrangement that happens in practice): Reforged is already
rem injected, and this project connects on top of its four entry jumps.
cd /d C:\Users\Apo\Py4GW_Stealth
set PY=C:\Users\Apo\AppData\Local\Programs\Python\Python313-32\python.exe
"%PY%" -m unittest tests.test_live_coexistence.ReforgedFirstTests -v > tests/live_reports\live_coexistence_chain.txt 2>&1
echo EXITCODE=%ERRORLEVEL%>> tests/live_reports\live_coexistence_chain.txt
