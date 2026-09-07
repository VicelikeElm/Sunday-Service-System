@echo off
setlocal
title Sunday Service System - Recent Event History
cd /d C:\Church\SermonAI
call venv\Scripts\activate.bat
echo.
python sss_event_history_cli.py
echo.
pause
endlocal
