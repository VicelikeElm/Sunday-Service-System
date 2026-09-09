@echo off
title SermonAI Cleanup - Run
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0sermonai_cleanup.ps1" -Apply
echo.
pause
