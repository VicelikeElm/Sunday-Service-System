@echo off
cd /d C:\Church\SermonAI
call venv\Scripts\activate.bat
python install_sermon_plan_loader.py
echo.
pause
