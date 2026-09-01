$ErrorActionPreference = "Stop"

$Base = "C:\Church\SermonAI"
$LowerThirds = "C:\Users\Vicel\Documents\Animated-Lower-Thirds\lower thirds"
$ControlPanel = Join-Path $LowerThirds "control-panel.html"
$Template = Join-Path $Base "control-panel-v15-template.html"
$BackupFolder = Join-Path $Base "LowerThird_Backups"

Write-Host ""
Write-Host "============================================================"
Write-Host " Lower Third Sermon Sync v15"
Write-Host " Reset Weekly Defaults On OBS Start"
Write-Host "============================================================"
Write-Host ""

if (Get-Process obs64 -ErrorAction SilentlyContinue) {
    Write-Host "OBS is running." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Close OBS completely, then run this installer again."
    Write-Host ""
    Read-Host "Press Enter to close"
    exit 1
}

if (-not (Test-Path -LiteralPath $ControlPanel)) {
    Write-Host "Current control-panel.html not found:" -ForegroundColor Red
    Write-Host "  $ControlPanel"
    Read-Host "Press Enter to close"
    exit 1
}

if (-not (Test-Path -LiteralPath $Template)) {
    Write-Host "v15 template is missing:" -ForegroundColor Red
    Write-Host "  $Template"
    Write-Host ""
    Write-Host "Copy all v15 package files to C:\Church\SermonAI first."
    Read-Host "Press Enter to close"
    exit 1
}

New-Item -ItemType Directory -Path $BackupFolder -Force | Out-Null

$stamp = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
$backup = Join-Path $BackupFolder "control-panel_before_v15_$stamp.html"

Copy-Item -LiteralPath $ControlPanel -Destination $backup -Force
Copy-Item -LiteralPath $Template -Destination $ControlPanel -Force

Write-Host "v15 control panel installed." -ForegroundColor Green
Write-Host ""
Write-Host "Startup behavior:"
Write-Host "  LT1 Active = Point 1 / Scripture"
Write-Host "  LT2 Active = Sermon Title / Scripture"
Write-Host "  LT2 Slot 3+ = PRESERVED"
Write-Host ""
Write-Host "Backup:"
Write-Host "  $backup"
Write-Host ""
Write-Host "Embedding the current sermon plan..."
Write-Host ""

& "C:\Church\SermonAI\venv\Scripts\python.exe" `
    "C:\Church\SermonAI\sync_sermon_plan_to_lower_thirds.py"

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "READY." -ForegroundColor Green
    Write-Host ""
    Write-Host "Reopen OBS and test by changing LT1, closing OBS, and reopening."
    Write-Host "It should return to Point 1 automatically."
} else {
    Write-Host ""
    Write-Host "The control panel installed, but sermon embedding failed." -ForegroundColor Yellow
}

Write-Host ""
Read-Host "Press Enter to close"
