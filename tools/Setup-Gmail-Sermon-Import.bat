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


echo.
echo ============================================================
echo  Gmail Sermon Import - One-Time Setup
echo ============================================================
echo.
echo This setup expects:
echo.
echo   C:\Church\SermonAI\gmail_credentials.json
echo.
echo If that file is not there yet, close this window and place your
echo Google OAuth Desktop App credentials file there first.
echo.

if not exist "C:\Church\SermonAI\gmail_credentials.json" (
    echo ERROR: gmail_credentials.json is missing.
    echo.
    pause
    exit /b 1
)

python -m pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib

if errorlevel 1 (
    echo.
    echo Package installation failed.
    pause
    exit /b 1
)

echo.
echo A browser window will open for Gmail authorization.
echo.
python core\gmail_sermon_importer.py --interactive --authorize-only

if errorlevel 1 (
    echo.
    echo Gmail authorization failed.
    pause
    exit /b 1
)

echo.
echo Testing the latest sermon-notes import...
echo.
python core\gmail_sermon_importer.py

echo.
pause
