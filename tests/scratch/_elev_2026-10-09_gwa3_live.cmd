@echo off
REM Elevated: the FIRST live run of the GwAu3 compatibility layer (py4gw/gwa3).
REM Read-only connection (game_thread=False): no hook, no patch, no call into the client. The suite
REM hashes the client's code section before and after and asserts it is unchanged. It READS the game;
REM it does not act on it, and it moves nothing.
cd /d C:\Users\Apo\Py4GW_Stealth
set PY=C:\Users\Apo\AppData\Local\Programs\Python\Python313-32\python.exe
echo === gwa3 live reads: start %DATE% %TIME% === > tests/live_reports\gwa3_live.log
"%PY%" -u -m unittest tests.test_gwa3_live -v >> tests/live_reports\gwa3_live.log 2>&1
echo gwa3_live_exit=%ERRORLEVEL% >> tests/live_reports\gwa3_live.log
echo === done %DATE% %TIME% === >> tests/live_reports\gwa3_live.log
