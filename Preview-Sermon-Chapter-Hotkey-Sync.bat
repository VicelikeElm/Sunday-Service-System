@echo off
title SSS - Preview Sermon Chapter Hotkeys
cd /d C:\Church\SermonAI
call venv\Scripts\activate.bat

echo.
echo ============================================================
echo  PREVIEW GMAIL -> ADDITIONAL CHAPTER HOTKEYS
echo ============================================================
echo.
echo This is READ ONLY. It does not edit OBS and does not fire a chapter.
echo.
python sync_named_chapter_hotkeys.py --preview
echo.
pause
