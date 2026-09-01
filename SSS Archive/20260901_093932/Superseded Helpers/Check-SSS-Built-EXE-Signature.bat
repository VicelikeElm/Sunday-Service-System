@echo off
setlocal
title Sunday Service System - Built EXE Signature Check
cd /d C:\Church\SermonAI
powershell -NoProfile -ExecutionPolicy Bypass -File "C:\Church\SermonAI\Check-SSS-Built-EXE-Signature.ps1"
echo.
pause
endlocal
