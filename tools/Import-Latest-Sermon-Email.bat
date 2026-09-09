@echo off
cd /d C:\Church\SermonAI
call venv\Scripts\activate.bat

if exist "C:\Church\SermonAI\venv\Scripts\python.exe" (
    "C:\Church\SermonAI\venv\Scripts\python.exe" "C:\Church\SermonAI\core\sunday_freeze_guard.py"
    if errorlevel 1 (
        echo.
        pause
        exit /b 9
    )
)

python core\gmail_sermon_importer.py

echo.
echo Syncing sermon plan to lower thirds...
python core\sync_sermon_plan_to_lower_thirds.py

echo.
echo Syncing Gmail sermon points to Additional Chapter Hotkeys...
python core\sync_named_chapter_hotkeys.py

echo.
echo Current rotating sermon chapter sequence:
python core\sermon_chapter_manager.py show

echo.
pause
