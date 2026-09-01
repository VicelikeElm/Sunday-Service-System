@echo off
setlocal
title Sunday Service System - Build SIGNED Update Package v3.1

cd /d C:\Church\SermonAI
set PROD_PYTHON=C:\Church\SermonAI\venv\Scripts\python.exe

if not exist "%PROD_PYTHON%" goto :missingpython

if not exist "C:\Church\SermonAI\sss_signing_config.json" (
    echo.
    echo [FIX] sss_signing_config.json is missing.
    echo Run Configure-SSS-Code-Signing.bat first.
    echo.
    pause
    exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -File "C:\Church\SermonAI\Check-SSS-Code-Signing.ps1"
if errorlevel 1 exit /b 1

if not exist "C:\Church\SermonAI\dist\SundayServiceSystem\SundayServiceSystem.exe" goto :missingbuild
if not exist "C:\Church\SermonAI\dist\SundayServiceSystemSettings\SundayServiceSystemSettings.exe" goto :missingbuild

"%PROD_PYTHON%" build_sss_update_package.py
if errorlevel 1 (
    echo.
    echo Signed update package build failed.
    echo.
    pause
    exit /b 1
)

echo.
echo Signed update package build complete.
echo.
pause
exit /b 0

:missingpython
echo.
echo Production SSS Python is missing.
echo.
pause
exit /b 1

:missingbuild
echo.
echo Signed EXE build folders are missing.
echo Run Build-SSS-Windows-Installer.bat first.
echo.
pause
exit /b 1
