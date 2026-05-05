@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
chcp 65001 > nul
echo Installing web dashboard libraries...
echo.

echo [1/4] Checking dashboard folder exists...
if not exist "dashboard" (
    echo ERROR: dashboard folder not found!
    echo Current path: %cd%
    goto :error
)

echo.
echo [2/4] Installing backend Python libraries...
if not exist "dashboard\backend" (
    echo ERROR: dashboard\backend folder not found!
    goto :error
)
cd dashboard\backend
python -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo WARNING: pip install returned error code %errorlevel%
)
cd ..\..

echo.
echo [3/4] Checking npm installation...
where npm >nul 2>nul
if %errorlevel% neq 0 (
    echo Node.js not found. Installing automatically via winget...
    winget install --id OpenJS.NodeJS -e --source winget --accept-package-agreements --accept-source-agreements
    if %errorlevel% neq 0 (
        echo ERROR: Automatic installation failed.
        echo Please install Node.js manually from https://nodejs.org/
        echo.
    ) else (
        echo Node.js installed successfully!
        goto :install_npm
    )
) else (
    call :install_npm
)

echo.
echo ========================================
echo Installation process completed!
echo ========================================
goto :end

:install_npm
echo [4/4] Installing frontend Node.js libraries...
if not exist "dashboard\frontend" (
    echo ERROR: dashboard\frontend folder not found!
    exit /b 1
)
cd dashboard\frontend
echo Running npm install with --legacy-peer-deps...
call npm install --legacy-peer-deps
set NPM_ERROR=%errorlevel%
if %NPM_ERROR% neq 0 (
    echo.
    echo ERROR: npm install failed with code %NPM_ERROR%
    cd ..\..
    exit /b %NPM_ERROR%
)
cd ..\..
exit /b 0

:error
echo.
echo ========================================
echo ERROR: Installation failed!
echo ========================================

:end
echo.
pause
