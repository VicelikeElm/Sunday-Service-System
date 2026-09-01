@echo off
if exist "C:\Church\SermonAI\venv\Scripts\python.exe" (
    "C:\Church\SermonAI\venv\Scripts\python.exe" "C:\Church\SermonAI\sunday_freeze_guard.py"
    if errorlevel 1 (
        echo.
        pause
        exit /b 9
    )
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Install-Lower-Third-Sermon-Sync-v15.ps1"
