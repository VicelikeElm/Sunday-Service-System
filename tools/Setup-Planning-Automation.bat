@echo off
cd /d C:\Church\SermonAI
call venv\Scripts\activate.bat

if exist "C:\Church\SermonAI\venv\Scripts\python.exe" (
    "C:\Church\SermonAI\venv\Scripts\python.exe" "C:\Church\SermonAI\core\sunday_freeze_guard.py"
    if errorlevel 1 (
        echo.
        pause
        exit /b 9
    )
)


echo.
echo ============================================================
echo  WorshipTools Planning Automation - Setup
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
echo The automation uses the dedicated Planning profile:
echo   C:\Church\SermonAI\WorshipTools_Planning_Profile
echo.
echo If that profile is not signed in, run:
echo   Planning-Update-Sermon-Show.bat
echo.
pause
