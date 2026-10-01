@echo off
rem Capture the exact live refusal text, elevated. Writes nothing to the client on the refusal path.
cd /d C:\Users\Apo\Py4GW_Stealth
set PY=C:\Users\Apo\AppData\Local\Programs\Python\Python313-32\python.exe
"%PY%" live_reports\_live_refusal_text.py > live_reports\live_refusal_text.txt 2>&1
echo EXITCODE=%ERRORLEVEL%>> live_reports\live_refusal_text.txt
