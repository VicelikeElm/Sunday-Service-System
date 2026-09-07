@echo off
setlocal
title SSS OBS Discovery Test
cd /d C:\Church\SermonAI
call venv\Scripts\activate.bat

echo.
echo This is read-only. It will NOT start/stop recording or streaming
echo and it will NOT transition anything to Program.
echo.
python test_sss_obs_discovery.py

echo.
pause
endlocal
