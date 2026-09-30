@echo off
rem Elevated run #9: the deliberate leave retry, with the party window opened first. One press, watched
rem for six seconds. The client is pid 45536 (restarted after the first attempt asserted).
set PY=C:\Users\Apo\AppData\Local\Programs\Python\Python313-32\python.exe
cd /d C:\Users\Apo\Py4GW_Stealth
echo === leave retry: started %DATE% %TIME% === > live_reports\party_leave_retry.txt
"%PY%" tests\probe_party_leave.py >> live_reports\party_leave_retry.txt 2>&1
echo === leave retry: exit=%ERRORLEVEL% === >> live_reports\party_leave_retry.txt
