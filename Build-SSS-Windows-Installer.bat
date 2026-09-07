@echo off
setlocal
title Sunday Service System - SIGNED Windows Release Build v3.1.2

cd /d C:\Church\SermonAI

echo.
echo ================================================================
echo SUNDAY SERVICE SYSTEM - SIGNED WINDOWS RELEASE v3.1.2
echo ================================================================
echo.
echo This build creates signed Main, Settings, Updater, .sssupdate,
echo and installer files.
echo.
echo v3.1 also adds the TRUSTED ONLINE RELEASE FEED CLIENT.
echo The feed itself is built separately after you know the HTTPS hosting URL:
echo   Build-SSS-Signed-Release-Feed.bat
echo.
echo This build does NOT start or stop OBS Recording/Streaming.
echo.

set PROD_PYTHON=C:\Church\SermonAI\venv\Scripts\python.exe
set BUILD_TOOLS=C:\Church\SermonAI\.sss-build-tools
set SIGNING_CONFIG=C:\Church\SermonAI\sss_signing_config.json

if not exist "%PROD_PYTHON%" (
    echo [FIX] Production SSS Python was not found:
    echo       %PROD_PYTHON%
    goto :fail
)

if not exist "%SIGNING_CONFIG%" (
    echo [FIX] Signing configuration was not found:
    echo       %SIGNING_CONFIG%
    echo.
    echo Run:
    echo   Configure-SSS-Code-Signing.bat
    echo.
    echo For LOCAL TESTING only, if needed:
    echo   Create-SSS-Development-Signing-Certificate.bat
    echo   Configure-SSS-Code-Signing.bat
    goto :fail
)

echo Checking release signing configuration...
powershell -NoProfile -ExecutionPolicy Bypass -File "C:\Church\SermonAI\Check-SSS-Code-Signing.ps1"
if errorlevel 1 goto :fail

echo.
echo Checking for an older packaged SSS EXE still running...
powershell -NoProfile -ExecutionPolicy Bypass -File "C:\Church\SermonAI\Check-SSS-Packaged-Build-Locks.ps1"
set LOCKCHECK=%ERRORLEVEL%

if "%LOCKCHECK%"=="11" (
    echo.
    echo Close the old packaged SSS EXE first.
    echo If it is stuck, run:
    echo   Close-Old-SSS-Build-EXEs.bat
    echo.
    echo OBS will NOT be closed by that helper.
    goto :fail
)

if not "%LOCKCHECK%"=="0" (
    echo.
    echo [FIX] The packaged-build lock check itself failed.
    echo       Build stopped safely instead of guessing.
    goto :fail
)

echo.
echo Checking production runtime dependency: obsws_python...
"%PROD_PYTHON%" -c "import obsws_python; print('obsws_python READY')"
if errorlevel 1 goto :fail

if not exist "%BUILD_TOOLS%" mkdir "%BUILD_TOOLS%"

echo.
echo Installing/updating isolated packaging tools...
"%PROD_PYTHON%" -m pip install --upgrade --target "%BUILD_TOOLS%" -r requirements-build.txt
if errorlevel 1 goto :fail

set PYTHONPATH=%BUILD_TOOLS%;%PYTHONPATH%

echo.
echo Verifying PyInstaller can see SSS runtime packages...
"%PROD_PYTHON%" -c "import PyInstaller, obsws_python; print('PyInstaller READY'); print('obsws_python visible to builder')"
if errorlevel 1 goto :fail

echo.
echo Building SIGNED SSS v3.1 release...
"%PROD_PYTHON%" build_sss_windows.py
if errorlevel 1 goto :fail

echo.
echo ================================================================
echo SIGNED RELEASE BUILD COMPLETE
echo ================================================================
echo.
echo Main:
echo   C:\Church\SermonAI\dist\SundayServiceSystem\SundayServiceSystem.exe
echo.
echo Settings:
echo   C:\Church\SermonAI\dist\SundayServiceSystemSettings\SundayServiceSystemSettings.exe
echo.
echo Updater:
echo   C:\Church\SermonAI\dist\SundayServiceSystemUpdater\SundayServiceSystemUpdater.exe
echo.
echo SIGNED update package:
echo   C:\Church\SermonAI\update-output\SundayServiceSystem-Update-v3.1.2.sssupdate
echo.
echo Installer, when Inno Setup is installed:
echo   C:\Church\SermonAI\installer-output\SundayServiceSystem-Setup-v3.1.2.exe
echo.
echo NEXT for online updates:
echo   Build-SSS-Signed-Release-Feed.bat
echo.
pause
exit /b 0

:fail
echo.
echo SIGNED RELEASE BUILD STOPPED / FAILED.
echo Review the messages above.
echo.
pause
exit /b 1
