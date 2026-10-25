@echo off
rem Elevated runner: the WHOLE packet sniffer suite, both capture halves.
rem
rem Inbound replaces the client's handler entry for every header; outbound hooks the send wrapper.
rem Both are now verified on their own, and this run proves them together plus the combined
rem initialize()/terminate() pair. Set PY4GW_LIVE_CTOS=0 (or use run_live_sniffer.cmd) for the
rem inbound-only pass.
set LOG=C:\Users\Apo\Py4GW_Stealth\tests\live_reports\live_all.log
echo starting elevated run > "%LOG%"
echo cwd=%CD% >> "%LOG%"
set PY4GW_LIVE_CTOS=1
cd /d "C:\Users\Apo\Py4GW_Stealth"
"C:\Users\Apo\AppData\Local\Programs\Python\Python313-32\python.exe" -m unittest tests.test_live_packet_sniffer -v >> "%LOG%" 2>&1
echo exit=%ERRORLEVEL% >> "%LOG%"
