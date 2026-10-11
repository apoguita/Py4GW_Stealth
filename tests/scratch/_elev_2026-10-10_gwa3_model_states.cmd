@echo off
rem Elevated, READ-ONLY: the model states the live client puts agents in, and whether the two GwAu3
rem definitions of IsAttacking/IsIdle/IsMoving would answer differently about them.
set PY=C:\Users\Apo\AppData\Local\Programs\Python\Python313-32\python.exe
cd /d C:\Users\Apo\Py4GW_Stealth
echo === model-state probe: started %DATE% %TIME% === > tests\live_reports\gwa3_model_states.log
"%PY%" -u tests\probe_gwa3_model_state_live.py >> tests\live_reports\gwa3_model_states.log 2>&1
echo === exit=%ERRORLEVEL% === >> tests\live_reports\gwa3_model_states.log
