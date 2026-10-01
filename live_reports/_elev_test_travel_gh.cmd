@echo off
rem Elevated: ONE test, ONE send - does literal 0x10000183 travel to the guild hall?
set PY=C:\Users\Apo\AppData\Local\Programs\Python\Python313-32\python.exe
cd /d C:\Users\Apo\Py4GW_Stealth
echo === travel-to-GH test: started %DATE% %TIME% === > live_reports\test_travel_gh.log
"%PY%" -u live_reports\_test_travel_gh.py >> live_reports\test_travel_gh.log 2>&1
echo === exit=%ERRORLEVEL% === >> live_reports\test_travel_gh.log
