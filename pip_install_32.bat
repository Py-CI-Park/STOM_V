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
    python32 -m pip install --upgrade pip
    python32 -m pip install numpy==1.26.4 pandas==2.0.3 python-telegram-bot==22.4
    python32 -m pip install psutil pyqt5 pyzmq pywin32 cryptography requests exchange_calendars loguru
    python32 -m pip install --upgrade apscheduler pytz tzlocal
    python32 -m pip install ./utility/TA_Lib-0.4.27-cp311-cp311-win32.whl
    pause