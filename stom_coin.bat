@echo off
setlocal

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
    echo.
    echo [STOM] Starting...
    echo [STOM] Working directory: %CD%
    echo [STOM] Command: python stom.py coin
    echo.
    python stom.py coin
    set "EXIT_CODE=%errorlevel%"
    echo.
    echo [STOM] Command exited with code %EXIT_CODE%.
    echo [STOM] Press any key to close this window...
    pause >nul
    popd
    exit /B %EXIT_CODE%
