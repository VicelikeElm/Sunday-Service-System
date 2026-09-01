@echo off
cd /d C:\Church\SermonAI
call venv\Scripts\activate.bat

echo.
echo ============================================================
echo  YouTube Studio Diagnostic v1.1 Setup
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
pause
