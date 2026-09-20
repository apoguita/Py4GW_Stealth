@echo off
setlocal

set "PROJECT_ROOT=%~dp0"
set "SCRIPT_PATH=%~1"

if "%SCRIPT_PATH%"=="" (
    echo Usage: py4gw.bat /path/to/script.py [script arguments]
    exit /b 2
)

if "%SCRIPT_PATH:~0,1%"=="/" set "SCRIPT_PATH=%SCRIPT_PATH:~1%"
if "%SCRIPT_PATH:~0,1%"=="\" set "SCRIPT_PATH=%SCRIPT_PATH:~1%"

if not exist "%PROJECT_ROOT%%SCRIPT_PATH%" (
    echo Script not found: %PROJECT_ROOT%%SCRIPT_PATH%
    exit /b 1
)

set "PYTHONPATH=%PROJECT_ROOT%;%PYTHONPATH%"
python "%PROJECT_ROOT%%SCRIPT_PATH%" %2 %3 %4 %5 %6 %7 %8 %9
exit /b %ERRORLEVEL%
