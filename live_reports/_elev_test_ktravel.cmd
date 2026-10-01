@echo off
rem Elevated: ONE test, ONE send - does literal 0x10000186 (kTravel) travel to map 55?
set PY=C:\Users\Apo\AppData\Local\Programs\Python\Python313-32\python.exe
cd /d C:\Users\Apo\Py4GW_Stealth
echo === kTravel test: started %DATE% %TIME% === > live_reports\test_ktravel.log
"%PY%" -u live_reports\_test_ktravel.py --target 55 >> live_reports\test_ktravel.log 2>&1
echo === exit=%ERRORLEVEL% === >> live_reports\test_ktravel.log
