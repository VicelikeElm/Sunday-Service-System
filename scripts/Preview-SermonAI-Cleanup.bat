@echo off
title SermonAI Cleanup - Preview
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0sermonai_cleanup.ps1"
echo.
pause
