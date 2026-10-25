@echo off
rem Elevated runner for the packet sniffer's staged live pass — the SEND WRAPPER half only.
rem
rem This places an entry hook on the function every outbound packet goes through, so it is run on its
rem own: if the client dies here, nothing else in the suite is a suspect, and the block address in the
rem log is what maps a fault address to this project's own memory.
set LOG=C:\Users\Apo\Py4GW_Stealth\tests\live_reports\live_ctos.log
echo starting elevated run >> "%LOG%"
echo cwd=%CD% >> "%LOG%"
set PY4GW_LIVE_CTOS=1
cd /d "C:\Users\Apo\Py4GW_Stealth"
"C:\Users\Apo\AppData\Local\Programs\Python\Python313-32\python.exe" -m unittest tests.test_live_packet_sniffer.LivePacketSnifferTests.test_an_outbound_packet_is_captured -v >> "%LOG%" 2>&1
echo exit=%ERRORLEVEL% >> "%LOG%"
