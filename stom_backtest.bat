@echo off
setlocal
pushd "%~dp0"
echo.
echo [STOM] Starting...
echo [STOM] Working directory: %CD%
echo [STOM] Command: python stom_backtest.py %*
echo.
python stom_backtest.py %*
set "EXIT_CODE=%errorlevel%"
echo.
echo [STOM] Command exited with code %EXIT_CODE%.
echo [STOM] Press any key to close this window...
pause >nul
popd
exit /B %EXIT_CODE%
