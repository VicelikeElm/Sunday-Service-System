@echo off
setlocal
title Sunday Service System - Security Check
cd /d C:\Church\SermonAI
call venv\Scripts\activate.bat
echo.
python core\sss_security_check.py
echo.
pause
endlocal
