@echo off
echo ============================================
echo   Grade Report Tool - Build Script (run once on Windows)
echo ============================================
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python was not found on this computer.
    echo Please install Python 3 from https://www.python.org/downloads/
    echo During installation, make sure to check "Add python.exe to PATH".
    echo Then run this script again.
    pause
    exit /b 1
)

echo [1/2] Installing dependencies: openpyxl, xlrd, pyinstaller ...
python -m pip install --upgrade pip >nul
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies. Please check your internet connection and try again.
    pause
    exit /b 1
)

echo.
echo [2/2] Building a single exe file ...
python -m PyInstaller --onefile --noconsole --clean --name GradeReportTool --paths src main.py
if errorlevel 1 (
    echo [ERROR] Build failed. Please take a screenshot of the messages above and send it to the developer.
    pause
    exit /b 1
)

echo.
echo Done! The program is at: dist\GradeReportTool.exe
echo Copy that one file anywhere you like and double-click it to run.
echo You can rename it to Chinese (e.g. right-click -^> Rename in File Explorer) if you prefer - that works fine.
pause
