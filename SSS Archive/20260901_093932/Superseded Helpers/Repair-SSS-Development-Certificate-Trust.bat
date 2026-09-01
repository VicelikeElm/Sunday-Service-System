@echo off
setlocal
title Sunday Service System - Repair Development Signing Trust
cd /d C:\Church\SermonAI
powershell -NoProfile -ExecutionPolicy Bypass -File "C:\Church\SermonAI\Repair-SSS-Development-Certificate-Trust.ps1"
echo.
pause
endlocal
