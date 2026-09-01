@echo off
setlocal
title Sunday Service System - Fix Timestamp URL
cd /d C:\Church\SermonAI
powershell -NoProfile -ExecutionPolicy Bypass -File "C:\Church\SermonAI\Fix-SSS-Timestamp-URL.ps1"
echo.
pause
endlocal
