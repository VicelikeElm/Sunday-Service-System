@echo off
setlocal
title Apply Built Sunday Service System v2.9 Update

set APPROOT=%ProgramFiles%\Sunday Service System
set MAINEXE=%APPROOT%\SundayServiceSystem\SundayServiceSystem.exe
set UPDATER=C:\Church\SermonAI\dist\SundayServiceSystemUpdater\SundayServiceSystemUpdater.exe
set PACKAGE=C:\Church\SermonAI\update-output\SundayServiceSystem-Update-v2.9.0.sssupdate

echo.
echo ================================================================
echo APPLY BUILT SSS v2.9.0 UPDATE
echo ================================================================
echo.
echo Close the installed Sunday Service System and Settings windows first.
echo OBS itself does NOT need to be closed unless its live output status
echo cannot be verified.
echo.
echo The updater will REFUSE to continue while OBS Recording/Streaming is active.
echo.

if not exist "%MAINEXE%" (
    echo [FIX] Installed SSS was not found:
    echo       %MAINEXE%
    echo.
    echo Use the v2.9 installer instead for a fresh install.
    pause
    exit /b 1
)

if not exist "%UPDATER%" (
    echo [FIX] Fresh updater EXE was not found:
    echo       %UPDATER%
    echo.
    echo Run Build-SSS-Windows-Installer.bat first.
    pause
    exit /b 1
)

if not exist "%PACKAGE%" (
    echo [FIX] v2.9 update package was not found:
    echo       %PACKAGE%
    echo.
    echo Run Build-SSS-Windows-Installer.bat first.
    pause
    exit /b 1
)

set CURRENT=
for /f "usebackq delims=" %%V in (`powershell -NoProfile -Command "(Get-Item '%MAINEXE%').VersionInfo.ProductVersion"`) do set CURRENT=%%V

if "%CURRENT%"=="" set CURRENT=0.0.0

echo Installed version: %CURRENT%
echo Target version:    2.9.0
echo.

choice /M "Launch the protected v2.9 updater now"
if errorlevel 2 exit /b 0

"%UPDATER%" --apply "%PACKAGE%" --install-root "%APPROOT%" --current-version "%CURRENT%"

endlocal
