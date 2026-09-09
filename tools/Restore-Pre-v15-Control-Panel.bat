@echo off
if exist "C:\Church\SermonAI\venv\Scripts\python.exe" (
    "C:\Church\SermonAI\venv\Scripts\python.exe" "C:\Church\SermonAI\core\sunday_freeze_guard.py"
    if errorlevel 1 (
        echo.
        pause
        exit /b 9
    )
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Restore-Pre-v15-Control-Panel.ps1"
