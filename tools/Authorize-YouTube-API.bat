@echo off
cd /d C:\Church\SermonAI
call venv\Scripts\activate.bat

echo.
echo ============================================================
echo  YOUTUBE DATA API - ONE-TIME AUTHORIZATION
echo ============================================================
echo.
echo This opens a real Google sign-in page in your browser.
echo Sign in with the account that owns/manages the church channel,
echo then approve the requested YouTube upload permission.
echo.
echo Sign in yourself in the browser window that opens - this
echo script does not know your password and never asks for it.
echo.
pause

python core\youtube_api_upload_worker.py --authorize-only --interactive
echo.
pause
