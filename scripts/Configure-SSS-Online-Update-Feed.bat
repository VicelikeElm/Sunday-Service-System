@echo off
setlocal
title Sunday Service System - Configure Online Update Feed
cd /d C:\Church\SermonAI
powershell -NoProfile -ExecutionPolicy Bypass -File "C:\Church\SermonAI\Configure-SSS-Online-Update-Feed.ps1"
echo.
pause
endlocal
