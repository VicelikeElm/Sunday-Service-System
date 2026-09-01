@echo off
setlocal
title Apply SIGNED Sunday Service System v3.0 Update

set APPROOT=%ProgramFiles%\Sunday Service System
set MAINEXE=%APPROOT%\SundayServiceSystem\SundayServiceSystem.exe
set UPDATER=C:\Church\SermonAI\dist\SundayServiceSystemUpdater\SundayServiceSystemUpdater.exe
set PACKAGE=C:\Church\SermonAI\update-output\SundayServiceSystem-Update-v3.0.0.sssupdate

echo.
echo ================================================================
echo APPLY SIGNED SSS v3.0.0 UPDATE
echo ================================================================
echo.
echo Close the installed Sunday Service System and Settings windows first.
echo.
echo OBS itself does NOT need to be closed when Recording and Streaming are
echo stopped and SSS can verify that state.
echo.
echo The v3.0 updater REFUSES:
echo   - unsigned update manifests
echo   - an untrusted manifest signer
echo   - invalid payload hashes
echo   - unsigned/untrusted Main or Settings EXEs
echo   - update while OBS Recording/Streaming is active
echo.

if not exist "%MAINEXE%" (
    echo [FIX] Installed SSS was not found:
    echo       %MAINEXE%
    echo.
    echo Use the v3.0 installer instead for a fresh install.
    pause
    exit /b 1
)

if not exist "%UPDATER%" (
    echo [FIX] Signed v3.0 updater EXE was not found:
    echo       %UPDATER%
    echo.
    echo Run Build-SSS-Windows-Installer.bat first.
    pause
    exit /b 1
)

if not exist "%PACKAGE%" (
    echo [FIX] Signed v3.0 update package was not found:
    echo       %PACKAGE%
    echo.
    echo Run Build-SSS-Windows-Installer.bat first.
    pause
    exit /b 1
)

echo Checking fresh updater Authenticode signature...
powershell -NoProfile -NonInteractive -Command ^
  "$s=Get-AuthenticodeSignature -LiteralPath '%UPDATER%';" ^
  "Write-Host ('Status: ' + $s.Status);" ^
  "if($s.SignerCertificate){Write-Host ('Signer: ' + $s.SignerCertificate.Subject); Write-Host ('Thumbprint: ' + $s.SignerCertificate.Thumbprint)};" ^
  "if($s.Status -ne 'Valid'){exit 12}"
if errorlevel 12 (
    echo.
    echo [FIX] The fresh v3.0 updater does not have a VALID Authenticode signature.
    echo Do not run this update.
    echo.
    pause
    exit /b 1
)

set CURRENT=
for /f "usebackq delims=" %%V in (`powershell -NoProfile -Command "(Get-Item '%MAINEXE%').VersionInfo.ProductVersion"`) do set CURRENT=%%V
if "%CURRENT%"=="" set CURRENT=0.0.0

echo.
echo Installed version: %CURRENT%
echo Target version:    3.0.0
echo.

choice /M "Launch the SIGNED protected v3.0 updater now"
if errorlevel 2 exit /b 0

"%UPDATER%" --apply "%PACKAGE%" --install-root "%APPROOT%" --current-version "%CURRENT%"

endlocal
