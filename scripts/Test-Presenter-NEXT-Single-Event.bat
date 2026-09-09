@echo off
setlocal
title Presenter NEXT - Single Event Test
cd /d C:\Church\SermonAI
call venv\Scripts\activate.bat

echo.
echo Put Presenter on a Scripture verse.
echo This will send ONE Note On event: Ch 10 / Note 60 / Vel 126.
echo It should advance exactly ONE slide.
echo.
pause

python core\test_presenter_single_event.py next

echo.
pause
endlocal
