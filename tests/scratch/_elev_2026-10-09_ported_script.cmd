@echo off
REM Elevated: a GwAu3-style AutoIt script running on the Stealth layer, against the live client.
REM It connects (Core_Initialize), logs through GwAu3's Log_* callback path, reads the seven families,
REM and checks that refused and unbuilt calls report themselves through @error.
REM
REM Elevated because Core_Initialize connects, and connecting is this project's write path.
cd /d C:\Users\Apo\Py4GW_Stealth
echo === ported GwAu3 script on the Stealth layer: start %DATE% %TIME% === > tests\live_reports\ported_script.log
"C:\Program Files (x86)\AutoIt3\AutoIt3.exe" /ErrorStdOut tools\autoit\test_ported_script.au3 >> tests\live_reports\ported_script.log 2>&1
echo ported_script_exit=%ERRORLEVEL% >> tests\live_reports\ported_script.log
echo === done %DATE% %TIME% === >> tests\live_reports\ported_script.log
