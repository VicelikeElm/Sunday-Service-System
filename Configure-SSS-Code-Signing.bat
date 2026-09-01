@echo off
setlocal
title Sunday Service System - Configure Code Signing
cd /d C:\Church\SermonAI
powershell -NoProfile -ExecutionPolicy Bypass -File "C:\Church\SermonAI\Configure-SSS-Code-Signing.ps1"
echo.
pause
endlocal
