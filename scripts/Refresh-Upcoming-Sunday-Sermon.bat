@echo off
setlocal
title Refresh Upcoming Sunday Sermon

cd /d C:\Church\SermonAI
call venv\Scripts\activate.bat

echo.
echo Looking for the pastor's sermon plan for the upcoming Sunday...
echo.

python gmail_sermon_importer.py

echo.
if errorlevel 1 (
    echo The upcoming Sunday sermon was NOT changed.
    echo Read the message above.
) else (
    echo.
    echo sermon_plan.json has been updated for the upcoming Sunday.
)

echo.
pause
endlocal
