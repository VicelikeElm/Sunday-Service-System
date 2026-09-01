@echo off
setlocal
title Sunday Service System - Code Signing Check
cd /d C:\Church\SermonAI
powershell -NoProfile -ExecutionPolicy Bypass -File "C:\Church\SermonAI\Check-SSS-Code-Signing.ps1"
echo.
pause
endlocal
