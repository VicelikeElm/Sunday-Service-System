@echo off
setlocal
title Sunday Service System - Stage GitHub Pages Feed
cd /d C:\Church\SermonAI
powershell -NoProfile -ExecutionPolicy Bypass -File "C:\Church\SermonAI\tools\Stage-SSS-GitHub-Pages-Feed.ps1"
echo.
pause
endlocal
