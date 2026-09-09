@echo off
title Sunday Service System v22 - Setup
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


echo.
echo ============================================================
echo  SUNDAY SERVICE SYSTEM v22 - RELIABILITY SUITE SETUP
echo ============================================================
echo.
echo This setup adds the isolated OBS audio meter dependency and
echo creates the reliability folders. It does NOT change Google logins,
echo YouTube permissions, OBS scenes, recording, or streaming.
echo.

python -m pip install websocket-client

if errorlevel 1 (
    echo.
    echo ERROR: websocket-client installation failed.
    pause
    exit /b 1
)

if not exist "C:\Church\SermonAI\State" mkdir "C:\Church\SermonAI\State"
if not exist "C:\Church\SermonAI\Logs" mkdir "C:\Church\SermonAI\Logs"
if not exist "C:\Church\SermonAI\Weekly_Backups" mkdir "C:\Church\SermonAI\Weekly_Backups"

echo.
echo Running a Python syntax check...
python -m py_compile ^
  core\sunday_mode.py ^
  core\sss_reliability.py ^
  core\audio_sanity_monitor.py ^
  core\post_service_supervisor.py ^
  core\thumbnail_handoff.py ^
  core\weekly_snapshot.py ^
  core\operational_cleanup.py ^
  core\sss_test_mode.py ^
  core\sermon_chapter_manager.py ^
  core\sync_named_chapter_hotkeys.py ^
  core\ptz_settings.py ^
  core\youtube_studio_upload_worker.py

if errorlevel 1 (
    echo.
    echo ERROR: One or more v22 scripts did not compile.
    pause
    exit /b 1
)

echo.
echo Archiving obsolete pre-v22 development files...
powershell -NoProfile -ExecutionPolicy Bypass -File "C:\Church\SermonAI\tools\Archive-v22-Legacy-Files.ps1"

echo.
echo v22 setup complete.
echo.
echo Recommended first check:
echo   Run-Safe-SSS-Test-Mode.bat
echo.
pause
