@echo off
title AirOS — Touchless Computer Operating Environment
color 0B
echo ========================================================
echo        AirOS — Touchless Desktop Operating System        
echo ========================================================
echo.
echo [1/3] Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH!
    echo Please install Python 3.11+ and run this script again.
    pause
    exit /b 1
)

echo [2/3] Checking dependencies from requirements.txt...
pip install -r requirements.txt --quiet

echo.
echo [3/3] Launching AirOS desktop environment...
python main.py

if errorlevel 1 (
    echo.
    echo [ERROR] AirOS exited with an error. Check logs above.
    pause
)
