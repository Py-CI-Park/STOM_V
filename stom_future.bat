@echo off
setlocal
set "STOM_PY313=C:\Python\64\Python31313\python.exe"

>nul 2>&1 "%SYSTEMROOT%\system32\cacls.exe" "%SYSTEMROOT%\system32\config\system"

if "%errorlevel%" NEQ "0" (
    echo Requesting administrative privileges...
    goto UACPrompt
) else (
    goto gotAdmin
)

:UACPrompt
    set "params=%*"
    echo Set UAC = CreateObject^("Shell.Application"^) > "%temp%\getadmin.vbs"
    echo UAC.ShellExecute "cmd.exe", "/c ""%~f0"" %params%", "", "runas", 1 >> "%temp%\getadmin.vbs"
    "%temp%\getadmin.vbs"
    del "%temp%\getadmin.vbs"
    exit /B

:gotAdmin
    pushd "%~dp0"
    if not exist "%STOM_PY313%" (
        echo ERROR: Python 3.13 executable not found: %STOM_PY313%
        echo Install Python 3.13.13 to C:\Python\64\Python31313 or update STOM_PY313 in this file.
        pause
        popd
        exit /B 1
    )
    echo.
    echo [STOM] Starting...
    echo [STOM] Working directory: %CD%
    echo [STOM] Python: %STOM_PY313%
    echo [STOM] Command: "%STOM_PY313%" stom.py future
    echo.
    "%STOM_PY313%" stom.py future
    set "EXIT_CODE=%errorlevel%"
    echo.
    echo [STOM] Command exited with code %EXIT_CODE%.
    echo [STOM] Press any key to close this window...
    pause >nul
    popd
    exit /B %EXIT_CODE%
