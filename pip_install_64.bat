@echo off
setlocal
set "STOM_PY313=C:\Python\64\Python31313\python.exe"
title "%~dp0"
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

    echo.
    echo ========================================
    echo    STOM Python 3.13 64-bit Library Installation
    echo ========================================
    echo.

    if not exist "%STOM_PY313%" (
        echo ERROR: Python 3.13 executable not found: %STOM_PY313%
        echo Install Python 3.13.13 to C:\Python\64\Python31313 or update STOM_PY313 in this file.
        pause
        popd
        exit /B 1
    )

    echo [1/4] Python version...
    "%STOM_PY313%" --version

    echo.
    echo [2/4] Upgrading pip...
    "%STOM_PY313%" -m pip install --upgrade pip

    echo.
    echo [3/4] Installing from requirements64.txt...
    if exist requirements64.txt (
        "%STOM_PY313%" -m pip install -r requirements64.txt
    ) else (
        echo ERROR: requirements64.txt file not found!
        pause
        popd
        exit /b 1
    )

    echo.
    echo [4/4] Installing local Python 3.13 TA-Lib wheel...
    if exist "utility\ta_lib-0.6.8-cp313-cp313-win_amd64.whl" (
        "%STOM_PY313%" -m pip install ".\utility\ta_lib-0.6.8-cp313-cp313-win_amd64.whl"
    ) else (
        echo WARNING: TA-Lib wheel file not found. ^(utility\ta_lib-0.6.8-cp313-cp313-win_amd64.whl^)
    )

    echo.
    echo ========================================
    echo    Python 3.13 64-bit Library Installation Complete!
    echo ========================================
    echo.
    pause
    popd
