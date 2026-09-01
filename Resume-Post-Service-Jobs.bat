@echo off
title SSS v22 - Resume Post-Service Jobs
cd /d C:\Church\SermonAI
call venv\Scripts\activate.bat
start "" /b venv\Scripts\pythonw.exe post_service_supervisor.py
echo Post-service supervisor started.
timeout /t 2 >nul
