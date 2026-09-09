@echo off
cd /d C:\Church\SermonAI
call venv\Scripts\activate.bat
python core\planning_update_sermon.py
echo.
pause
