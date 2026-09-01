$ErrorActionPreference = "Stop"

$Base = "C:\Church\SermonAI"
$Panel = "C:\Users\Vicel\Documents\Animated-Lower-Thirds\lower thirds\control-panel.html"
$BackupFolder = Join-Path $Base "LowerThird_Backups"

if (Get-Process obs64 -ErrorAction SilentlyContinue) {
    Write-Host "Close OBS completely before restoring." -ForegroundColor Yellow
    Read-Host "Press Enter to close"
    exit 1
}

$backups = @(
    Get-ChildItem -LiteralPath $BackupFolder -Filter "control-panel_before_v14_*.html" -File |
        Sort-Object LastWriteTime -Descending
)

if ($backups.Count -eq 0) {
    Write-Host "No v14 backup found." -ForegroundColor Red
    Read-Host "Press Enter to close"
    exit 1
}

Copy-Item -LiteralPath $backups[0].FullName -Destination $Panel -Force

Write-Host ""
Write-Host "Restored:" -ForegroundColor Green
Write-Host "  $($backups[0].FullName)"
Write-Host ""
Read-Host "Press Enter to close"
