@echo off
setlocal
title Sunday Service System - Trusted Online Update Feed Check
cd /d C:\Church\SermonAI
call venv\Scripts\activate.bat
echo.
python sss_online_update_feed_check.py
echo.
pause
endlocal
