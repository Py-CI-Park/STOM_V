@echo off
cd /d "%~dp0"
chcp 65001 > nul
echo Uninstalling web dashboard libraries...
echo.

echo Checking npm installation...
where npm >nul 2>nul
if %errorlevel% neq 0 (
    echo Node.js/npm not found. Nothing to uninstall.
    goto :end
)

echo.
echo Uninstalling frontend Node.js libraries...
cd dashboard\frontend
if exist node_modules (
    rmdir /s /q node_modules
    echo node_modules folder removed.
) else (
    echo No node_modules folder found.
)
if exist package-lock.json (
    del package-lock.json
    echo package-lock.json removed.
)
cd ..\..

echo.
echo All libraries uninstalled successfully!

:end
echo.
pause
