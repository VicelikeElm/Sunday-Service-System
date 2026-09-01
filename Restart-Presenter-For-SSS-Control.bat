@echo off
setlocal
title Restart Presenter for SSS Control

echo.
echo Closing all Presenter processes...
taskkill /F /IM Presenter.exe >nul 2>&1

timeout /t 2 /nobreak >nul

echo Starting Presenter with SSS Scripture auto-cue control...
cd /d C:\Church\SermonAI
call venv\Scripts\activate.bat

python -c "from presenter_accessibility import launch_presenter_accessible; r=launch_presenter_accessible(None); print(r.get('reason','')); print('Executable:',r.get('exe','')); print('Control ready:',r.get('control_ready',False)); raise SystemExit(0 if r.get('control_ready') else 1)"

echo.
if errorlevel 1 (
  echo Presenter opened without the SSS auto-cue connection.
  echo Run Check-Presenter-SSS-Control.bat and send the result.
) else (
  echo Presenter is ready for SSS Scripture auto-cue.
)

echo.
pause
endlocal
