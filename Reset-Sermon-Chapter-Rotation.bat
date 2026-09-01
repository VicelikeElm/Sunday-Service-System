@echo off
title SSS - Reset Sermon Chapter Rotation
cd /d C:\Church\SermonAI
call venv\Scripts\activate.bat
python sermon_chapter_manager.py reset
echo.
pause
