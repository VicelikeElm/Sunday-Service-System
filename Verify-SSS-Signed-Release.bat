@echo off
setlocal
title Sunday Service System - Verify Signed Release v3.1

cd /d C:\Church\SermonAI
set PROD_PYTHON=C:\Church\SermonAI\venv\Scripts\python.exe

set MAIN=C:\Church\SermonAI\dist\SundayServiceSystem\SundayServiceSystem.exe
set SETTINGS=C:\Church\SermonAI\dist\SundayServiceSystemSettings\SundayServiceSystemSettings.exe
set UPDATER=C:\Church\SermonAI\dist\SundayServiceSystemUpdater\SundayServiceSystemUpdater.exe
set PACKAGE=C:\Church\SermonAI\update-output\SundayServiceSystem-Update-v3.1.0.sssupdate
set INSTALLER=C:\Church\SermonAI\installer-output\SundayServiceSystem-Setup-v3.1.0.exe
set FEEDFOLDER=C:\Church\SermonAI\release-feed-output\stable

echo.
echo ================================================================
echo SSS v3.1 SIGNED RELEASE VERIFICATION
echo ================================================================
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "C:\Church\SermonAI\Check-SSS-Code-Signing.ps1"
if errorlevel 1 goto :fail

for %%F in ("%MAIN%" "%SETTINGS%" "%UPDATER%") do (
    if not exist "%%~F" (
        echo [FIX] Missing release file:
        echo       %%~F
        goto :fail
    )
)

echo.
echo Verifying Authenticode signatures and pinned signed update manifest...
"%PROD_PYTHON%" -c "from sss_signing import load_signing_config, signing_thumbprint, manifest_thumbprint, verify_authenticode_file; from sss_updater_core import verify_update_package; c=load_signing_config(required=True); trusted=(signing_thumbprint(c),manifest_thumbprint(c)); [verify_authenticode_file(p,trusted_thumbprints=trusted,require_valid=True) for p in [r'%MAIN%',r'%SETTINGS%',r'%UPDATER%']]; m=verify_update_package(r'%PACKAGE%'); print('SIGNED UPDATE READY:',m['version']); print('MANIFEST SIGNER:',m['signer_thumbprint'])"
if errorlevel 1 goto :fail

if exist "%INSTALLER%" (
    echo.
    echo Verifying installer Authenticode signature...
    "%PROD_PYTHON%" -c "from sss_signing import load_signing_config, signing_thumbprint, verify_authenticode_file; c=load_signing_config(required=True); print(verify_authenticode_file(r'%INSTALLER%',trusted_thumbprints=(signing_thumbprint(c),),require_valid=True))"
    if errorlevel 1 goto :fail
) else (
    echo.
    echo [CHECK] Installer was not built. This is okay if Inno Setup 6 is not installed.
)

if exist "%FEEDFOLDER%\latest.json" (
    echo.
    echo Verifying locally-built STABLE online release feed...
    "%PROD_PYTHON%" sss_release_feed_verify.py --folder "%FEEDFOLDER%"
    if errorlevel 1 goto :fail
) else (
    echo.
    echo [INFO] No stable online release feed has been built yet.
    echo        Run Build-SSS-Signed-Release-Feed.bat after choosing the HTTPS host URL.
)

echo.
echo ================================================================
echo [READY] SSS v3.1 SIGNED RELEASE VERIFICATION PASSED
echo ================================================================
echo.
pause
exit /b 0

:fail
echo.
echo [FIX] Signed release verification failed.
echo Do not distribute or upload this build.
echo.
pause
exit /b 1
