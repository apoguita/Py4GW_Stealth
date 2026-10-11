@echo off
rem Elevated, READ-ONLY probe: where the client lays a skillbar's slots out, measured.
rem Answers the one-slot shift the live suite found in the layer's SkillID column.
set PY=C:\Users\Apo\AppData\Local\Programs\Python\Python313-32\python.exe
cd /d C:\Users\Apo\Py4GW_Stealth
echo === skillbar slots: started %DATE% %TIME% === > tests/live_reports\skillbar_slots.log
"%PY%" -u tests/scratch\1_probe_skillbar_slots.py >> tests/live_reports\skillbar_slots.log 2>&1
echo === exit=%ERRORLEVEL% === >> tests/live_reports\skillbar_slots.log
