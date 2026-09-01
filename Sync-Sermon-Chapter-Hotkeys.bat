@echo off
title SSS - Sync Sermon Chapter Hotkeys
cd /d C:\Church\SermonAI
call venv\Scripts\activate.bat

echo.
echo ============================================================
echo  SYNC GMAIL -> ADDITIONAL CHAPTER HOTKEYS
echo ============================================================
echo.
echo This updates the Church recording SCENE COLLECTION chapter-hotkey
echo names while preserving existing IDs and bindings where possible.
echo.
echo If OBS is currently open, the sync safely DEFERs instead of editing
echo the scene collection underneath OBS.
echo.
python sync_named_chapter_hotkeys.py
echo.
pause
