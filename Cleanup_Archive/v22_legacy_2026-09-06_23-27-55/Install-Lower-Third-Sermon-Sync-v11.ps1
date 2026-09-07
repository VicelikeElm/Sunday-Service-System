$ErrorActionPreference = "Stop"

$Base = "C:\Church\SermonAI"
$LowerThirds = "C:\Users\Vicel\Documents\Animated-Lower-Thirds\lower thirds"
$ControlPanel = Join-Path $LowerThirds "control-panel.html"
$PatchedPanel = Join-Path $PSScriptRoot "control-panel-v11.html"
$BackupFolder = Join-Path $Base "LowerThird_Backups"

Write-Host ""
Write-Host "============================================================"
Write-Host " Lower Third Sermon Sync v11"
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
    Write-Host "Current control-panel.html was not found." -ForegroundColor Red
    Write-Host "  $ControlPanel"
    Read-Host "Press Enter to close"
    exit 1
}

if (-not (Test-Path -LiteralPath $PatchedPanel)) {
    Write-Host "control-panel-v11.html was not found beside this installer." -ForegroundColor Red
    Read-Host "Press Enter to close"
    exit 1
}

New-Item -ItemType Directory -Path $BackupFolder -Force | Out-Null

$stamp = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
$backup = Join-Path $BackupFolder "control-panel_before_v11_$stamp.html"

Copy-Item -LiteralPath $ControlPanel -Destination $backup -Force
Copy-Item -LiteralPath $PatchedPanel -Destination $ControlPanel -Force

# Remove all old Sermon AI external loader experiments.
$oldLoaders = @(
    (Join-Path $LowerThirds "sermon_plan_loader.js"),
    (Join-Path $LowerThirds "sermon-plan-loader.js")
)

foreach ($loader in $oldLoaders) {
    if (Test-Path -LiteralPath $loader) {
        Remove-Item -LiteralPath $loader -Force
    }
}

Write-Host "Installed v11 control panel." -ForegroundColor Green
Write-Host ""
Write-Host "Backup:"
Write-Host "  $backup"
Write-Host ""
Write-Host "Next:"
Write-Host "  1. Copy the other v11 files into C:\Church\SermonAI"
Write-Host "  2. Run Sync-Current-Sermon-Plan.bat once"
Write-Host "  3. Reopen OBS / Sunday Mode"
Write-Host ""
Read-Host "Press Enter to close"
