@echo off
cd /d C:\Church\SermonAI
call venv\Scripts\activate.bat

echo.
echo ============================================================
echo  WorshipTools Planning Diagnostic - Setup
echo ============================================================
echo.

python -m pip install playwright

if errorlevel 1 (
    echo.
    echo Playwright installation failed.
    pause
    exit /b 1
)

echo.
echo Setup complete.
echo.
echo This diagnostic uses your already-installed Chrome or Edge,
echo so it does not download a separate browser.
echo.
pause
