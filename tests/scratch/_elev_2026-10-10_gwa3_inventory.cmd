@echo off
rem Elevated, READ-ONLY: what the inventory struct's weapon-set pointers hold, and whether GwAu3's
rem `id + 0x10` arithmetic for a mod pointer is readable at all.  Evidence for `Item_GetInventoryInfo`
rem and `Item_GetModStruct` in `py4gw/gwa3/data_item.py`.
set PY=C:\Users\Apo\AppData\Local\Programs\Python\Python313-32\python.exe
cd /d C:\Users\Apo\Py4GW_Stealth
echo === inventory probe: started %DATE% %TIME% === > tests\live_reports\gwa3_inventory.log
"%PY%" -u tests\probe_gwa3_inventory_live.py >> tests\live_reports\gwa3_inventory.log 2>&1
echo === exit=%ERRORLEVEL% === >> tests\live_reports\gwa3_inventory.log
