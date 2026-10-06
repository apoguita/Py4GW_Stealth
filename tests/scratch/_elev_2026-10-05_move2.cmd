@echo off
cd /d C:\Users\Apo\Py4GW_Stealth
set PY=C:\Users\Apo\AppData\Local\Programs\Python\Python313-32\python.exe
echo === move call (fixed reads): start %DATE% %TIME% === > tests/live_reports\move_call2.log
"%PY%" tests\probe_move_call.py tests/live_reports\move_call2.json --pid 8456 --distance 500 --watch 6 >> tests/live_reports\move_call2.log 2>&1
echo move_exit=%ERRORLEVEL% >> tests/live_reports\move_call2.log
