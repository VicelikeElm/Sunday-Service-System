@echo off
setlocal
title SSS ProPresenter API Connection Test
cd /d C:\Church\SermonAI
call venv\Scripts\activate.bat
echo.
python test_propresenter_connection.py
echo.
pause
endlocal
