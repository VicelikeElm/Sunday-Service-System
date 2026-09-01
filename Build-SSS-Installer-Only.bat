@echo off
setlocal
title Sunday Service System - Build SIGNED Installer v3.1

cd /d C:\Church\SermonAI

set PROD_PYTHON=C:\Church\SermonAI\venv\Scripts\python.exe
set ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe

if not exist "%ISCC%" set ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe

if not exist "%ISCC%" (
    echo.
    echo [FIX] Inno Setup 6 was not found.
    echo.
    pause
    exit /b 1
)

if not exist "%PROD_PYTHON%" (
    echo.
    echo [FIX] Production SSS Python was not found.
    echo.
    pause
    exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -File "C:\Church\SermonAI\Check-SSS-Code-Signing.ps1"
if errorlevel 1 exit /b 1

echo.
echo Building installer...
"%ISCC%" "C:\Church\SermonAI\installer\SundayServiceSystem.iss"
if errorlevel 1 goto :fail

set INSTALLER=C:\Church\SermonAI\installer-output\SundayServiceSystem-Setup-v3.1.0.exe

if not exist "%INSTALLER%" (
    echo.
    echo [FIX] Expected installer was not created:
    echo       %INSTALLER%
    goto :fail
)

echo.
echo Signing and RFC3161 timestamping installer...
"%PROD_PYTHON%" -c "from sss_signing import load_signing_config, sign_authenticode_file; sign_authenticode_file(r'%INSTALLER%', load_signing_config(required=True)); print('Installer signature READY')"
if errorlevel 1 goto :fail

echo.
echo SIGNED installer complete:
echo %INSTALLER%
echo.
pause
exit /b 0

:fail
echo.
echo Signed installer build failed.
echo.
pause
exit /b 1
