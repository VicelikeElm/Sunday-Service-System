$ErrorActionPreference = "Continue"

$Panel = "C:\Users\Vicel\Documents\Animated-Lower-Thirds\lower thirds\control-panel.html"
$Plan = "C:\Church\SermonAI\sermon_plan.json"

Write-Host ""
Write-Host "============================================================"
Write-Host " Lower Third Sermon Sync v13 - Diagnostic"
Write-Host "============================================================"
Write-Host ""

$json = Get-Content $Plan -Raw -Encoding UTF8 | ConvertFrom-Json
$html = Get-Content $Panel -Raw -Encoding UTF8

Write-Host "Plan title:"
Write-Host "  $($json.title)"
Write-Host ""

Write-Host "Current sermon title embedded:"
if ($html.Contains($json.title)) {
    Write-Host "  YES" -ForegroundColor Green
} else {
    Write-Host "  NO" -ForegroundColor Red
}

Write-Host ""
Write-Host "v13 startup-switch block removed:"
if (
    $html.Contains("SERMON AI - EMBEDDED LOWER THIRD SYNC v13") -and
    -not $html.Contains("LT1/LT2 active; embedded plan not applied")
) {
    Write-Host "  YES" -ForegroundColor Green
} else {
    Write-Host "  NO" -ForegroundColor Red
}

Write-Host ""
Read-Host "Press Enter to close"
