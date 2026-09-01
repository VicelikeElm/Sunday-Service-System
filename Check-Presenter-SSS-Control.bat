@echo off
setlocal
cd /d C:\Church\SermonAI
call venv\Scripts\activate.bat

python -c "from presenter_accessibility import presenter_control_ready; from presenter_scripture_locator import _cdp_targets; ok,d=presenter_control_ready(); print('Control ready:',ok); print('Detail:',d); print(); print('Targets:'); print(_cdp_targets() if ok else 'No targets because control is offline')"

echo.
pause
endlocal
