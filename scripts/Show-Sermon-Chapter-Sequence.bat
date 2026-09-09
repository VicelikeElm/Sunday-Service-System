@echo off
title SSS - Sermon Chapter Sequence
cd /d C:\Church\SermonAI
call venv\Scripts\activate.bat
python core\sermon_chapter_manager.py show
echo.
pause
