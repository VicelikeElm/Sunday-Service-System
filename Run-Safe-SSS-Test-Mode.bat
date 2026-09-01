@echo off
title SSS v22 - Safe Test Mode
cd /d C:\Church\SermonAI
call venv\Scripts\activate.bat
python sss_test_mode.py
echo.
pause
