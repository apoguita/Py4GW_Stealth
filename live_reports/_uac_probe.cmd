@echo off
rem A trivial elevated command: it exists so one UAC (secure-desktop) switch can be produced on demand,
rem with the client's own device-lost counter measured on either side of it.
echo uac probe ran > C:\Users\Apo\Py4GW_Stealth\live_reports\_uac_probe.txt
