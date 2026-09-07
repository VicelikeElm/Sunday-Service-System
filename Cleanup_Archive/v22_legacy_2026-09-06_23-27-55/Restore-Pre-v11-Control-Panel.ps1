$ErrorActionPreference = "Stop"

$Base = "C:\Church\SermonAI"
$LowerThirds = "C:\Users\Vicel\Documents\Animated-Lower-Thirds\lower thirds"
$ControlPanel = Join-Path $LowerThirds "control-panel.html"
$BackupFolder = Join-Path $Base "LowerThird_Backups"

$obs = Get-Process obs64 -ErrorAction SilentlyContinue

if ($obs) {
    Write-Host "Close OBS completely before restoring." -ForegroundColor Yellow
    Read-Host "Press Enter to close"
    exit 1
}

$backups = @(
    Get-ChildItem -LiteralPath $BackupFolder -Filter "control-panel_before_v11_*.html" -File |
        Sort-Object LastWriteTime -Descending
)

if ($backups.Count -eq 0) {
    Write-Host "No v11 backup was found." -ForegroundColor Red
    Read-Host "Press Enter to close"
    exit 1
}

$restore = $backups[0]
Copy-Item -LiteralPath $restore.FullName -Destination $ControlPanel -Force

Write-Host ""
Write-Host "Restored:"
Write-Host "  $restore"
Write-Host ""
Read-Host "Press Enter to close"
