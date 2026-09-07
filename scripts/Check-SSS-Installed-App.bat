@echo off
setlocal
title Sunday Service System - Installed App / Signature Check

set APPROOT=%ProgramFiles%\Sunday Service System
set MAINEXE=%APPROOT%\SundayServiceSystem\SundayServiceSystem.exe
set SETTINGSEXE=%APPROOT%\SundayServiceSystemSettings\SundayServiceSystemSettings.exe
set UPDATEREXE=%APPROOT%\SundayServiceSystemUpdater\SundayServiceSystemUpdater.exe

echo.
echo ================================================================
echo SUNDAY SERVICE SYSTEM - INSTALLED APP / SIGNATURE CHECK
echo ================================================================
echo.

for %%F in ("%MAINEXE%" "%SETTINGSEXE%" "%UPDATEREXE%") do (
    if exist "%%~F" (
        echo [READY] %%~F
        powershell -NoProfile -NonInteractive -Command "$s=Get-AuthenticodeSignature -LiteralPath '%%~F'; Write-Host ('        Version: ' + (Get-Item '%%~F').VersionInfo.ProductVersion); Write-Host ('        Signature: ' + $s.Status); if($s.SignerCertificate){Write-Host ('        Signer: ' + $s.SignerCertificate.Subject); Write-Host ('        Thumbprint: ' + $s.SignerCertificate.Thumbprint)}"
    ) else (
        echo [FIX] Missing: %%~F
    )
    echo.
)

if exist "C:\Church\SermonAI" (
    echo [READY] Compatibility runtime root:
    echo         C:\Church\SermonAI
) else (
    echo [CHECK] Compatibility runtime root missing:
    echo         C:\Church\SermonAI
)

echo.
echo This check is READ-ONLY.
echo It does not launch SSS and does not affect Recording or Streaming.
echo.
pause
endlocal
