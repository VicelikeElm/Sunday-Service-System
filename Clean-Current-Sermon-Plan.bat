@echo off
cd /d C:\Church\SermonAI
call venv\Scripts\activate.bat

if exist "C:\Church\SermonAI\venv\Scripts\python.exe" (
    "C:\Church\SermonAI\venv\Scripts\python.exe" "C:\Church\SermonAI\sunday_freeze_guard.py"
    if errorlevel 1 (
        echo.
        pause
        exit /b 9
    )
)

python clean_current_sermon_plan.py
echo.
pause
