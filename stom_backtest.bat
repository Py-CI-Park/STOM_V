@echo off
setlocal
set "STOM_PY313=C:\Python\64\Python31313\python.exe"
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
echo [STOM] Command: "%STOM_PY313%" stom_backtest.py %*
echo.
"%STOM_PY313%" stom_backtest.py %*
set "EXIT_CODE=%errorlevel%"
echo.
echo [STOM] Command exited with code %EXIT_CODE%.
echo [STOM] Press any key to close this window...
pause >nul
popd
exit /B %EXIT_CODE%
