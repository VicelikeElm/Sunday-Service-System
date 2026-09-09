@echo off
setlocal
title SSS Recovery Snapshot Check
cd /d C:\Church\SermonAI
call venv\Scripts\activate.bat
echo.
python core\sss_recovery_check.py
echo.
pause
endlocal
