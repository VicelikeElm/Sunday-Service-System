@echo off
cd /d C:\Church\SermonAI
call venv\Scripts\activate.bat

echo.
echo ============================================================
echo  YOUTUBE STUDIO UPLOAD - DRY RUN
echo ============================================================
echo.
echo WARNING:
echo This selects the real sermon file in YouTube Studio and begins the
echo browser-side upload, but it STOPS before Next / Visibility / Publish.
echo Use only when intentionally testing the upload form.
echo.
pause

python core\youtube_studio_upload_worker.py --manual --dry-run
echo.
pause
