@echo off
setlocal
title SSS Camera Connection Test
cd /d C:\Church\SermonAI
call venv\Scripts\activate.bat
echo.
python core\test_camera_connection.py
echo.
pause
endlocal
