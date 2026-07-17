@echo off
setlocal
set "STOM_PY313=C:\Python\64\Python31313\python.exe"

rem STOM AI web dashboard launcher.
rem Default UI: V4 graph-first dashboard (/ui). Legacy shell: /ui/?dashboard_version=legacy
rem Optional environment overrides before running this file:
rem   set STOM_DASHBOARD_HOST=127.0.0.1
rem   set STOM_DASHBOARD_PORT=8770
rem   set STOM_DASHBOARD_NO_BROWSER=1
rem   set STOM_DASHBOARD_NO_PAUSE=1

if not defined STOM_DASHBOARD_HOST set "STOM_DASHBOARD_HOST=127.0.0.1"
if not defined STOM_DASHBOARD_PORT set "STOM_DASHBOARD_PORT=8770"
set "STOM_DASHBOARD_URL=http://%STOM_DASHBOARD_HOST%:%STOM_DASHBOARD_PORT%/ui"
set "STOM_DASHBOARD_HEALTH=http://%STOM_DASHBOARD_HOST%:%STOM_DASHBOARD_PORT%/health"

pushd "%~dp0"
if not exist "%STOM_PY313%" (
    echo ERROR: Python 3.13 executable not found: %STOM_PY313%
    echo Install Python 3.13.13 to C:\Python\64\Python31313 or update STOM_PY313 in this file.
    if /I not "%STOM_DASHBOARD_NO_PAUSE%"=="1" pause
    popd
    exit /B 1
)

echo.
echo [STOM DASHBOARD] Starting web dashboard...
echo [STOM DASHBOARD] Working directory: %CD%
echo [STOM DASHBOARD] Python: %STOM_PY313%
echo [STOM DASHBOARD] URL: %STOM_DASHBOARD_URL%
echo [STOM DASHBOARD] Command: "%STOM_PY313%" -m ai_strategy_loop --host %STOM_DASHBOARD_HOST% --port %STOM_DASHBOARD_PORT% %*
echo.
echo [STOM DASHBOARD] Close this command window or press Ctrl+C to stop the server.
echo.

if /I "%~1"=="--help" goto runDashboard
if /I "%~1"=="-h" goto runDashboard
if /I "%STOM_DASHBOARD_NO_BROWSER%"=="1" goto runDashboard

echo [STOM DASHBOARD] A browser window will open when /health responds.
start "STOM Dashboard Browser Opener" powershell -NoProfile -ExecutionPolicy Bypass -Command "$health='%STOM_DASHBOARD_HEALTH%'; $ui='%STOM_DASHBOARD_URL%'; for ($i=0; $i -lt 60; $i++) { try { Invoke-WebRequest -UseBasicParsing -TimeoutSec 1 $health ^| Out-Null; Start-Process $ui; exit 0 } catch { Start-Sleep -Milliseconds 500 } }; Start-Process $ui"

:runDashboard
"%STOM_PY313%" -m ai_strategy_loop --host %STOM_DASHBOARD_HOST% --port %STOM_DASHBOARD_PORT% %*
set "EXIT_CODE=%errorlevel%"
echo.
echo [STOM DASHBOARD] Command exited with code %EXIT_CODE%.
if /I not "%STOM_DASHBOARD_NO_PAUSE%"=="1" (
    echo [STOM DASHBOARD] Press any key to close this window...
    pause >nul
)
popd
exit /B %EXIT_CODE%
