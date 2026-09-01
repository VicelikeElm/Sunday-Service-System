@echo off
setlocal
title Sunday Service System - Development Signing Certificate
cd /d C:\Church\SermonAI
powershell -NoProfile -ExecutionPolicy Bypass -File "C:\Church\SermonAI\Create-SSS-Development-Signing-Certificate.ps1"
echo.
pause
endlocal
