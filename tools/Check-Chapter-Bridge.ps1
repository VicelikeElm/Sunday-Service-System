$ErrorActionPreference = "Continue"

$Base = "C:\Church\SermonAI"
$Python = Join-Path $Base "venv\Scripts\python.exe"
$PythonW = Join-Path $Base "venv\Scripts\pythonw.exe"
$Bridge = Join-Path $Base "core\chapter_bridge.py"
$Status = Join-Path $Base "chapter_bridge_status.json"
$Log = Join-Path $Base "chapter_bridge.log"

Write-Host ""
Write-Host "============================================================"
Write-Host " Chapter Bridge Check"
Write-Host "============================================================"
Write-Host ""

if (-not (Test-Path $Python)) {
    Write-Host "Python not found: $Python" -ForegroundColor Red
    Read-Host "Press Enter to close"
    exit 1
}

if (-not (Test-Path $Bridge)) {
    Write-Host "chapter_bridge.py not found: $Bridge" -ForegroundColor Red
    Read-Host "Press Enter to close"
    exit 1
}

Write-Host "Checking required Python import..."
& $Python -c "from ccl_chromium_reader import ccl_chromium_localstorage; print('CCL Chromium Reader: OK')"

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "The CCL Chromium Reader import failed." -ForegroundColor Red
    Read-Host "Press Enter to close"
    exit 1
}

$processes = Get-CimInstance Win32_Process |
    Where-Object {
        $_.CommandLine -and
        $_.CommandLine -like '*chapter_bridge.py*' -and
        $_.ProcessId -ne $PID
    }

if ($processes) {
    Write-Host ""
    Write-Host "Chapter Bridge process is already running:" -ForegroundColor Green
    foreach ($p in $processes) {
        Write-Host "  PID $($p.ProcessId)"
    }
}
else {
    Write-Host ""
    Write-Host "Chapter Bridge is not running. Starting it now..."
    Start-Process -FilePath $PythonW -ArgumentList "`"$Bridge`"" -WorkingDirectory $Base -WindowStyle Hidden
    Start-Sleep -Seconds 3
}

Write-Host ""
if (Test-Path $Status) {
    Write-Host "Current status:" -ForegroundColor Cyan
    Get-Content $Status
}
else {
    Write-Host "No chapter_bridge_status.json has been created yet." -ForegroundColor Yellow
}

Write-Host ""
if (Test-Path $Log) {
    Write-Host "Recent Chapter Bridge log:" -ForegroundColor Cyan
    Get-Content $Log -Tail 12
}

Write-Host ""
Read-Host "Press Enter to close"
