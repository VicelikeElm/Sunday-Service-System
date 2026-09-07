@echo off
setlocal
title Sunday Service System - Preview Workspace Trim
cd /d C:\Church\SermonAI
powershell -NoProfile -ExecutionPolicy Bypass -File "C:\Church\SermonAI\Trim-SSS-Workspace.ps1" -PreviewOnly
echo.
pause
endlocal
