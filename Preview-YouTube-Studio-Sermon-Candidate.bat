@echo off
cd /d C:\Church\SermonAI
call venv\Scripts\activate.bat
python youtube_studio_upload_worker.py --manual --preview
echo.
pause
