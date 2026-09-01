@echo off
title SermonAI Cleanup - Undo Last
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0sermonai_cleanup.ps1" -UndoLast
echo.
pause
