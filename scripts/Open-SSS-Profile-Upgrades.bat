@echo off
setlocal
cd /d C:\Church\SermonAI
call venv\Scripts\activate.bat
pythonw core\sss_settings.py --migrations
endlocal
