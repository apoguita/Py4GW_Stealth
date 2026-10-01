@echo off
rem One elevated run: the chaining live test, then a read-only probe of the four entries afterwards, so a
rem single UAC approval answers both "does the chain work" and "is Reforged exactly as it was".
cd /d C:\Users\Apo\Py4GW_Stealth
set PY=C:\Users\Apo\AppData\Local\Programs\Python\Python313-32\python.exe
set OUT=live_reports\live_coexistence_chain.txt
"%PY%" -m unittest tests.test_live_coexistence.ReforgedFirstTests -v > "%OUT%" 2>&1
echo EXITCODE=%ERRORLEVEL%>> "%OUT%"
echo.>> "%OUT%"
echo === probe of the four entries after the run ===>> "%OUT%"
"%PY%" tests\probe_two_runtimes_live.py live_reports\two_runtimes_after_chain.json >> "%OUT%" 2>&1
