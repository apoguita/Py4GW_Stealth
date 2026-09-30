@echo off
rem Elevated run #2: the five reversible acting steps, each with its own report. Every one changes
rem something and puts it back in the same step (the flags are cleared, the behaviour word returns,
rem the skill slot's bit returns, the mode returns, the advertisement is cancelled), and each run
rem compares the client's own state before and after.
set PY=C:\Users\Apo\AppData\Local\Programs\Python\Python313-32\python.exe
cd /d C:\Users\Apo\Py4GW_Stealth
for %%S in (flags behaviour skill-ai difficulty search) do (
  echo === act --allow %%S: started %DATE% %TIME% === >> live_reports\party_act_live.txt
  "%PY%" tests\probe_party_live.py act live_reports\party_act_%%S_live.json --allow %%S >> live_reports\party_act_live.txt 2>&1
  echo === act --allow %%S: exit=%ERRORLEVEL% === >> live_reports\party_act_live.txt
)
