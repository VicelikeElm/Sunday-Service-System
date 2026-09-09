@echo off
setlocal
title Test Presenter Visual Read

cd /d C:\Church\SermonAI
call venv\Scripts\activate.bat

python core\test_presenter_visual_read.py

echo.
echo The text above is what SSS can currently read from webcam TP.
echo.
pause
endlocal
