@echo off
setlocal
title Presenter PREVIOUS - Single Event Test
cd /d C:\Church\SermonAI
call venv\Scripts\activate.bat

echo.
echo Put Presenter on a Scripture verse.
echo This will send ONE Note On event: Ch 10 / Note 62 / Vel 126.
echo It should go back exactly ONE slide.
echo.
pause

python test_presenter_single_event.py back

echo.
pause
endlocal
