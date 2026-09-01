@echo off
setlocal
title Sunday Service System - Full System Diagnostics
cd /d C:\Church\SermonAI
call venv\Scripts\activate.bat
python sss_diagnostics_cli.py
echo.
pause
endlocal
