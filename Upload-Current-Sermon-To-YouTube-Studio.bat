@echo off
cd /d C:\Church\SermonAI
call venv\Scripts\activate.bat

echo.
echo ============================================================
echo  YOUTUBE STUDIO - MANUAL FULL SERMON UPLOAD
echo ============================================================
echo.
echo The production safeguards remain active:
echo   Correct sermon date
echo   D:\2026 root only
echo   Matching filename date
echo   Minimum size
echo   Minimum duration
echo   Stable/finished file
echo   Largest eligible recording wins
echo   Exact church channel ID/name/Manager role verification
echo   Duplicate-upload protection
echo.
python youtube_studio_upload_worker.py --manual
echo.
pause
