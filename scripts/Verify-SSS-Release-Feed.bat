@echo off
setlocal
title Sunday Service System - Verify Signed Release Feed

cd /d C:\Church\SermonAI
set PROD_PYTHON=C:\Church\SermonAI\venv\Scripts\python.exe

set CHANNEL=stable
if not "%~1"=="" set CHANNEL=%~1

set FOLDER=C:\Church\SermonAI\release-feed-output\%CHANNEL%

if not exist "%FOLDER%\latest.json" (
    echo.
    echo [FIX] Signed feed folder was not found:
    echo       %FOLDER%
    echo.
    echo Run Build-SSS-Signed-Release-Feed.bat first.
    echo.
    pause
    exit /b 1
)

"%PROD_PYTHON%" core\sss_release_feed_verify.py --folder "%FOLDER%"
if errorlevel 1 (
    echo.
    echo [FIX] Release-feed verification failed.
    echo Do not upload this feed.
    echo.
    pause
    exit /b 1
)

echo.
pause
endlocal
