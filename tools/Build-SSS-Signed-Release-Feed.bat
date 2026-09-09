@echo off
setlocal
title Sunday Service System - Build Signed Online Release Feed
cd /d C:\Church\SermonAI
powershell -NoProfile -ExecutionPolicy Bypass -File "C:\Church\SermonAI\tools\Build-SSS-Signed-Release-Feed.ps1"
echo.
pause
endlocal
