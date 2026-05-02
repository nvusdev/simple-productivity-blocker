@echo off
setlocal enabledelayedexpansion
title Productivity Application Installer

:: Check for Administrative Privileges
net session >nul 2>&1
if %errorLevel% == 0 (
    goto :admin_granted
) else (
    echo =======================================================
    echo Administrator Privileges Required
    echo =======================================================
    echo.
    echo The Productivity Application needs Administrator rights
    echo during installation to:
    echo 1. Modify the system hosts file (for blocking websites).
    echo 2. Manage system processes (for blocking applications).
    echo 3. Create a Desktop shortcut.
    echo.
    echo Please grant permission in the prompt that appears.
    echo.
    pause
    powershell -Command "Start-Process '%~dpnx0' -Verb RunAs"
    exit /B
)

:admin_granted
echo =======================================================
echo Installing Productivity Application...
echo =======================================================
echo.

:: Check for Python
python --version >nul 2>&1
if %errorLevel% == 0 (
    echo [OK] Python is installed.
) else (
    echo [ERROR] Python is not installed or not in PATH.
    echo Opening the official Python download page...
    start https://www.python.org/downloads/
    echo.
    echo Please install Python, ensure you check "Add python.exe to PATH",
    echo and then run this installer again.
    pause
    exit /B
)

echo.
echo Installing required Python packages...
pip install -r requirements.txt
if %errorLevel% neq 0 (
    echo [WARNING] Some packages failed to install. Please check your internet connection.
) else (
    echo [OK] Packages installed successfully.
)

echo.
echo Creating Desktop Shortcut...
set "TARGET_DIR=%~dp0"
set "SHORTCUT_PATH=%USERPROFILE%\Desktop\Productivity Application.lnk"

powershell -Command "$wshell = New-Object -ComObject WScript.Shell; $shortcut = $wshell.CreateShortcut('%SHORTCUT_PATH%'); $shortcut.TargetPath = 'pythonw.exe'; $shortcut.Arguments = '\"%TARGET_DIR%main.py\"'; $shortcut.WorkingDirectory = '%TARGET_DIR%'; $shortcut.Save()"

echo.
echo =======================================================
echo Installation Complete!
echo =======================================================
echo A shortcut has been placed on your Desktop.
echo You can close this window now.
pause
