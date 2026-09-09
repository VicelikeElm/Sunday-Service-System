@echo off
setlocal
title Close Old Packaged SSS EXEs

echo.
echo ================================================================
echo CLOSE OLD PACKAGED SSS EXEs
echo ================================================================
echo.
echo This helper ONLY closes:
echo   SundayServiceSystem.exe
echo   SundayServiceSystemSettings.exe
echo   SundayServiceSystemUpdater.exe
echo.
echo It does NOT close OBS.
echo It does NOT close python.exe/pythonw.exe.
echo It does NOT stop Recording or Streaming in OBS.
echo.

choice /M "Close any old packaged SSS EXEs now"
if errorlevel 2 exit /b 0

taskkill /IM SundayServiceSystem.exe /F >nul 2>&1
taskkill /IM SundayServiceSystemSettings.exe /F >nul 2>&1
taskkill /IM SundayServiceSystemUpdater.exe /F >nul 2>&1

echo.
echo Old packaged SSS EXE processes have been closed if they were running.
echo You can now run Build-SSS-Windows-Installer.bat again.
echo.
pause
endlocal
