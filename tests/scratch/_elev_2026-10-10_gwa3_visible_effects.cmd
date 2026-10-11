@echo off
rem Elevated, READ-ONLY: what the agent visible-effect list holds, and whether its first dword is the
rem effect type GwAu3 calls EffectType. Evidence for `UAI_AgentHasVisibleEffect` in
rem `py4gw/gwa3/uai_effects.py`.
set PY=C:\Users\Apo\AppData\Local\Programs\Python\Python313-32\python.exe
cd /d C:\Users\Apo\Py4GW_Stealth
echo === visible effects probe: started %DATE% %TIME% === > tests\live_reports\gwa3_visible_effects.log
"%PY%" -u tests\probe_gwa3_visible_effects_live.py >> tests\live_reports\gwa3_visible_effects.log 2>&1
echo === exit=%ERRORLEVEL% === >> tests\live_reports\gwa3_visible_effects.log
