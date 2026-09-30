@echo off
rem Elevated run #1: the value-preserving hold stage. Every call it makes carries the value the
rem client already reports, so the sources' own guards refuse the write; a reading that moves is a
rem defect, not an expected write. Output goes to a file because an elevated process's stdout is not
rem the launching shell's.
set PY=C:\Users\Apo\AppData\Local\Programs\Python\Python313-32\python.exe
cd /d C:\Users\Apo\Py4GW_Stealth
echo === hold: started %DATE% %TIME% === > live_reports\party_hold_live.txt
"%PY%" tests\probe_party_live.py hold live_reports\party_hold_live.json >> live_reports\party_hold_live.txt 2>&1
echo === hold: exit=%ERRORLEVEL% === >> live_reports\party_hold_live.txt
