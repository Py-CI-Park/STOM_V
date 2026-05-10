@echo off
setlocal
set "STOM_PY313=C:\Python\64\Python31313\python.exe"

>nul 2>&1 "%SYSTEMROOT%\system32\cacls.exe" "%SYSTEMROOT%\system32\config\system"

if '%errorlevel%' NEQ '0' (
    echo Requesting administrative privileges...
    goto UACPrompt
) else ( goto gotAdmin )

:UACPrompt
    echo Set UAC = CreateObject^("Shell.Application"^) > "%temp%\getadmin.vbs"
    set params = %*:"=""
    echo UAC.ShellExecute "cmd.exe", "/c %~s0 %params%", "", "runas", 1 >> "%temp%\getadmin.vbs"

    "%temp%\getadmin.vbs"
    del "%temp%\getadmin.vbs"
    exit /B

:gotAdmin
    pushd "%CD%"
    CD /D "%~dp0"
    if not exist "%STOM_PY313%" (
        echo ERROR: Python 3.13 executable not found: %STOM_PY313%
        echo Install Python 3.13.13 to C:\Python\64\Python31313 or update STOM_PY313 in this file.
        pause
        popd
        exit /B 1
    )
    "%STOM_PY313%" .\utility\update_db_20260211.py
    set "EXIT_CODE=%errorlevel%"
    pause
    popd
    exit /B %EXIT_CODE%
