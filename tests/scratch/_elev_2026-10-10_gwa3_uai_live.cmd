@echo off
rem Elevated: (1) the READ-ONLY gwAu3 live suite, including the UtilityAI targeting queries, and
rem (2) the control-action probe, which is the one WRITE in this pair.
rem
rem (1) Read-only means no hook, no patch and no call into the client; the suite itself hashes the
rem     client's code section before and after and fails if either changes.
rem (2) The probe opens the write connection (game_thread=True), presses the client's own weapon-set
rem     control action once through `Item_SwitchWeaponSet` and once through `UAI_ChangeWeaponSet`, reads
rem     the client's own `active_weapon_set` back for the effect, and restores the original set. It
rem     asserts nothing about the cancel or the bundle drop beyond the press not raising.
rem -u keeps stdout unbuffered, so if a run is killed the log still shows where it stopped.
set PY=C:\Users\Apo\AppData\Local\Programs\Python\Python313-32\python.exe
cd /d C:\Users\Apo\Py4GW_Stealth
echo === gwa3 live suite (with UAI targeting): started %DATE% %TIME% === > tests/live_reports\gwa3_live_uai.log
"%PY%" -u -m unittest tests.test_gwa3_live -v >> tests/live_reports\gwa3_live_uai.log 2>&1
echo === exit=%ERRORLEVEL% === >> tests/live_reports\gwa3_live_uai.log
echo === gwa3 control-action probe: started %DATE% %TIME% === > tests/live_reports\gwa3_control_action.log
"%PY%" -u tests\probe_gwa3_control_action_live.py >> tests/live_reports\gwa3_control_action.log 2>&1
echo === exit=%ERRORLEVEL% === >> tests/live_reports\gwa3_control_action.log
