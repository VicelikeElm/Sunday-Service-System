@echo off
cd /d C:\Church\SermonAI

call venv\Scripts\activate.bat

python -u sermon_ai.py > sermon_ai.log 2>&1