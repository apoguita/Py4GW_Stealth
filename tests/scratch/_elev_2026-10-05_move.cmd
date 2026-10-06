@echo off
cd /d C:\Users\Apo\Py4GW_Stealth
set PY=C:\Users\Apo\AppData\Local\Programs\Python\Python313-32\python.exe
echo === move call: start %DATE% %TIME% === > tests/live_reports\move_call.log
"%PY%" tests\probe_move_call.py tests/live_reports\move_call.json --pid 8456 --distance 500 --watch 6 >> tests/live_reports\move_call.log 2>&1
echo move_exit=%ERRORLEVEL% >> tests/live_reports\move_call.log
echo === done %DATE% %TIME% === >> tests/live_reports\move_call.log
