@echo off
setlocal
title SSS Sermon Source Diagnostic
cd /d C:\Church\SermonAI
call venv\Scripts\activate.bat
echo.
python core\test_sermon_source_profile.py
echo.
pause
endlocal
