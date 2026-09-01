@echo off
cd /d C:\Church\SermonAI
call venv\Scripts\activate.bat
python planning_update_sermon.py --show --dry-run
echo.
pause
