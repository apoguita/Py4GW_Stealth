@echo off
rem Elevated run: decide the UIMessage shift by watching the client's own messages.
rem Observes only - nothing is sent to the client. See _travel_ui_message_test.py.
rem -u matters: without it python buffers stdout, so if the run is killed (or the client is
rem restarted under it) every line - including where it stopped - is lost. Unbuffered, the log
rem fills as it goes and a hang is visible at the exact step.
rem While it runs, do these BY HAND in the game:
rem   1. add a hero to the party
rem   2. open the guild hall, then leave it
rem   3. travel to another map / outpost
set PY=C:\Users\Apo\AppData\Local\Programs\Python\Python313-32\python.exe
cd /d C:\Users\Apo\Py4GW_Stealth
echo === travel ui-message test: started %DATE% %TIME% === > tests/live_reports\travel_ui_message_test.log
"%PY%" -u tests/scratch\1_travel_ui_message_test.py --seconds 180 >> tests/live_reports\travel_ui_message_test.log 2>&1
echo === travel ui-message test: exit=%ERRORLEVEL% === >> tests/live_reports\travel_ui_message_test.log
