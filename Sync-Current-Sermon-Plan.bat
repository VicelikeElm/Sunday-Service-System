@echo off
cd /d C:\Church\SermonAI
call venv\Scripts\activate.bat
python sync_sermon_plan_to_lower_thirds.py
echo.
pause
