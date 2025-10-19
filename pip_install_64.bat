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
    python -m pip install --upgrade pip
    python -m pip install llvmlite==0.44.0 numpy==1.26.4 pandas==2.0.3 python-telegram-bot==22.4 numba
    python -m pip install websockets cryptography psutil pyqt5 PyQtWebEngine BeautifulSoup4 optuna optuna-dashboard
    python -m pip install cmaes lxml squarify matplotlib pyqtgraph pyupbit ntplib python-dateutil python-binance
    python -m pip install exchange_calendars pyzmq pyttsx3 yfinance cython loguru fake_useragent
    python -m pip install --upgrade apscheduler pytz tzlocal
    python -m pip install ./utility/TA_Lib-0.4.25-cp311-cp311-win_amd64.whl
    pause