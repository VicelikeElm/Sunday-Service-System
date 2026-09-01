$ErrorActionPreference = "Stop"

$Base = "C:\Church\SermonAI"
$LowerThirds = "C:\Users\Vicel\Documents\Animated-Lower-Thirds\lower thirds"
$ControlPanel = Join-Path $LowerThirds "control-panel.html"
$Template = Join-Path $Base "control-panel-v12-template.html"
$BackupFolder = Join-Path $Base "LowerThird_Backups"

Write-Host ""
Write-Host "============================================================"
Write-Host " Lower Third Sermon Sync v12"
Write-Host "============================================================"
Write-Host ""

$obs = Get-Process obs64 -ErrorAction SilentlyContinue

if ($obs) {
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
    Write-Host "v12 template is missing:" -ForegroundColor Red
    Write-Host "  $Template"
    Write-Host ""
    Write-Host "Copy all v12 package files to C:\Church\SermonAI first."
    Read-Host "Press Enter to close"
    exit 1
}

New-Item -ItemType Directory -Path $BackupFolder -Force | Out-Null

$stamp = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
$backup = Join-Path $BackupFolder "control-panel_before_v12_$stamp.html"

Copy-Item -LiteralPath $ControlPanel -Destination $backup -Force
Copy-Item -LiteralPath $Template -Destination $ControlPanel -Force

# Remove all files from the older loader experiments.
$oldFiles = @(
    (Join-Path $LowerThirds "sermon_plan_loader.js"),
    (Join-Path $LowerThirds "sermon-plan-loader.js"),
    (Join-Path $LowerThirds "sermon-plan-data.js")
)

foreach ($file in $oldFiles) {
    if (Test-Path -LiteralPath $file) {
        Remove-Item -LiteralPath $file -Force
    }
}

Write-Host "v12 base control panel installed." -ForegroundColor Green
Write-Host ""
Write-Host "Backup:"
Write-Host "  $backup"
Write-Host ""
Write-Host "Now embedding the current sermon plan..."
Write-Host ""

& "C:\Church\SermonAI\venv\Scripts\python.exe" `
    "C:\Church\SermonAI\sync_sermon_plan_to_lower_thirds.py"

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "The panel was installed, but the sermon plan embed failed." -ForegroundColor Yellow
    Write-Host "Run Sync-Current-Sermon-Plan.bat after checking sermon_plan.json."
}
else {
    Write-Host ""
    Write-Host "READY." -ForegroundColor Green
    Write-Host ""
    Write-Host "Reopen OBS. LT1/LT2 should load this week's sermon."
}

Write-Host ""
Read-Host "Press Enter to close"
