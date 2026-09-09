@echo off
cd /d C:\Church\SermonAI
call venv\Scripts\activate.bat

echo.
echo ============================================================
echo  YOUTUBE DATA API - MANUAL FULL SERMON UPLOAD (sanity check)
echo ============================================================
echo.
echo Uses the real YouTube Data API (not browser automation).
echo Requires Authorize-YouTube-API.bat to have been run first.
echo.
echo Same safeguards as before:
echo   Correct sermon date / D:\2026 root only / matching filename date
echo   Minimum size / minimum duration / stable file
echo   Largest eligible recording wins
echo   Channel ID verification against the authorized channel
echo   Duplicate-upload protection
echo.
python core\youtube_api_upload_worker.py --manual
echo.
pause
