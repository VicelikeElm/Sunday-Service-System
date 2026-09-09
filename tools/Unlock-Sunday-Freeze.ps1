$Freeze = "C:\Church\SermonAI\State\Sunday_Freeze.json"

Write-Host ""
Write-Host "============================================================"
Write-Host " FORCE UNLOCK SUNDAY FREEZE"
Write-Host "============================================================"
Write-Host ""
Write-Host "Only do this if OBS is NOT recording and NOT streaming." -ForegroundColor Yellow
Write-Host ""

$answer = Read-Host "Type UNLOCK to remove the freeze marker"

if ($answer -cne "UNLOCK") {
    Write-Host ""
    Write-Host "Cancelled."
    Read-Host "Press Enter to close"
    exit 1
}

Remove-Item -LiteralPath $Freeze -Force -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "Sunday Freeze marker removed." -ForegroundColor Green
Write-Host "If OBS is still recording/streaming, SSS will recreate it."
Write-Host ""
Read-Host "Press Enter to close"
