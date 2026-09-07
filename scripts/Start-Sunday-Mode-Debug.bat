@echo off
title Sunday Service System - DEBUG
cd /d C:\Church\SermonAI
call venv\Scripts\activate.bat
python -X faulthandler -u sunday_mode.py
echo.
echo ============================================================
echo Sunday Mode exited.
echo If there is an error above, take a picture or copy the text.
echo ============================================================
pause
