@echo off
setlocal
title Sunday Service System - Safe Workspace Trim
cd /d C:\Church\SermonAI

echo.
echo This will remove rebuildable build/cache clutter and archive superseded
echo SSS helper/documentation files. Runtime/config/profile/release files stay.
echo.
choice /M "Continue with the safe SSS workspace trim"
if errorlevel 2 exit /b 0

powershell -NoProfile -ExecutionPolicy Bypass -File "C:\Church\SermonAI\Trim-SSS-Workspace.ps1"

echo.
pause
endlocal
