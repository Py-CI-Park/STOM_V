@echo off
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
    echo    STOM 64-bit Library Installation
    echo ========================================
    echo.

    echo [1/3] Upgrading pip...
    python -m pip install --upgrade pip

    echo.
    echo [2/3] Installing from requirements64.txt...
    if exist requirements64.txt (
        python -m pip install -r requirements64.txt
    ) else (
        echo ERROR: requirements64.txt file not found!
        pause
        exit /b 1
    )

    echo.
    echo [3/3] Installing local TA-Lib wheel...
    if exist "utility\ta_lib-0.6.8-cp311-cp311-win_amd64.whl" (
        python -m pip install "./utility/ta_lib-0.6.8-cp311-cp311-win_amd64.whl"
    ) else (
        echo WARNING: TA-Lib wheel file not found. (utility/ta_lib-0.6.8-cp311-cp311-win_amd64.whl)
    )

    echo.
    echo ========================================
    echo    64-bit Library Installation Complete!
    echo ========================================
    echo.
    pause
