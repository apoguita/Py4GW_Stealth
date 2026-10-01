@echo off
rem Elevated: ONE action, ONE send. Pass the action through as arguments.
rem   %1 = action (leave_gh | travel_gh | travel | send)
rem   %2.. = extra args, e.g. --require-map 5   or  --target 5
set PY=C:\Users\Apo\AppData\Local\Programs\Python\Python313-32\python.exe
cd /d C:\Users\Apo\Py4GW_Stealth
echo === single action %1: started %DATE% %TIME% === > live_reports\single_action.log
"%PY%" -u live_reports\_single_action.py --action %1 %2 %3 %4 %5 %6 >> live_reports\single_action.log 2>&1
echo === single action: exit=%ERRORLEVEL% === >> live_reports\single_action.log
