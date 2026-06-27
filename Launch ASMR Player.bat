@echo off
title ASMR Player - Setup & Launch
color 0B

echo =======================================
echo        ASMR Player with Subtitles
echo =======================================
echo.

:: Check Python
python --version >nul 2>&1
IF ERRORLEVEL 1 (
    echo [ERROR] Python not found!
    echo Please install Python 3.8+ from https://python.org
    echo Make sure to check "Add Python to PATH" during install.
    pause
    exit /b 1
)

echo [OK] Python found.

:: Install dependencies
echo.
echo Installing/checking dependencies...
pip install pygame mutagen --quiet
IF ERRORLEVEL 1 (
    echo [WARN] pip install had issues. Trying anyway...
)

echo.
echo Launching ASMR Player...
echo.
python "%~dp0asmr_player.py"

IF ERRORLEVEL 1 (
    echo.
    echo [ERROR] App crashed. Check the output above.
    pause
)
