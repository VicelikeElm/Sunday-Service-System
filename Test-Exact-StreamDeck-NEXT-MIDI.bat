@echo off
setlocal
title Exact Stream Deck MIDI - NEXT
cd /d C:\Church\SermonAI
call venv\Scripts\activate.bat

echo.
echo This sends EXACTLY:
echo   Port Presenter
echo   Channel 10
echo   Note 60
echo   Velocity 126
echo   NOTE ON ONLY - NO RELEASE / NOTE OFF
echo.
pause

python test_presenter_streamdeck_exact_midi.py next

echo.
pause
endlocal
