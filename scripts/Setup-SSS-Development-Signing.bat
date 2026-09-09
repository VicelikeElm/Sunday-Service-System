@echo off
setlocal
title Sunday Service System - One-Click Development Signing Setup
cd /d C:\Church\SermonAI
powershell -NoProfile -ExecutionPolicy Bypass -File "C:\Church\SermonAI\tools\Setup-SSS-Development-Signing.ps1"
echo.
pause
endlocal
