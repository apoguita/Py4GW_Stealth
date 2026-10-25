@echo off
rem Elevated runner for the packet sniffer's staged live pass (inbound only).
rem
rem Connecting is a write (the shared block, the hook, the dispatcher), and a process cannot raise its
rem own token, so the shell has to be elevated before python starts. Absolute paths throughout: an
rem elevated cmd starts in system32, and a redirect into a directory that is not there writes nothing.
set LOG=C:\Users\Apo\Py4GW_Stealth\tests\live_reports\live_sniffer.log
echo starting elevated run > "%LOG%"
echo cwd=%CD% >> "%LOG%"
set PY4GW_LIVE_CTOS=
cd /d "C:\Users\Apo\Py4GW_Stealth"
"C:\Users\Apo\AppData\Local\Programs\Python\Python313-32\python.exe" -m unittest tests.test_live_packet_sniffer -v >> "%LOG%" 2>&1
echo exit=%ERRORLEVEL% >> "%LOG%"
