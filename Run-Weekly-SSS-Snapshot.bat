@echo off
title SSS v22 - Weekly Snapshot
cd /d C:\Church\SermonAI
call venv\Scripts\activate.bat
python weekly_snapshot.py
echo.
pause
