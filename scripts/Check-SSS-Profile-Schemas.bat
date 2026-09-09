@echo off
setlocal
title Sunday Service System - Profile Schema Check
cd /d C:\Church\SermonAI
call venv\Scripts\activate.bat
echo.
python core\sss_profile_schema_check.py
echo.
pause
endlocal
