@echo off
setlocal
title SSS Audio Profile Diagnostic
cd /d C:\Church\SermonAI
call venv\Scripts\activate.bat
echo.
python test_audio_profile.py
echo.
pause
endlocal
