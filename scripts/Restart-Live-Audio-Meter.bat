@echo off
setlocal

echo Restarting the SSS live audio meter helper...

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$procs = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -and $_.CommandLine -like '*audio_sanity_monitor.py*' }; foreach ($p in $procs) { try { Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue } catch {} }"

timeout /t 1 /nobreak >nul

if exist "C:\Church\SermonAI\venv\Scripts\pythonw.exe" (
    start "" "C:\Church\SermonAI\venv\Scripts\pythonw.exe" "C:\Church\SermonAI\audio_sanity_monitor.py"
    echo Live audio meter helper restarted.
) else (
    echo ERROR: Python environment not found.
)

timeout /t 2 /nobreak >nul
endlocal
