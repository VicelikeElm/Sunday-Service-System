$ErrorActionPreference = "Continue"

$Panel = "C:\Users\Vicel\Documents\Animated-Lower-Thirds\lower thirds\control-panel.html"
$Plan = "C:\Church\SermonAI\sermon_plan.json"

Write-Host ""
Write-Host "============================================================"
Write-Host " Lower Third Sermon Sync v12 - Diagnostic"
Write-Host "============================================================"
Write-Host ""

if (-not (Test-Path $Panel)) {
    Write-Host "control-panel.html missing." -ForegroundColor Red
    pause
    exit
}

if (-not (Test-Path $Plan)) {
    Write-Host "sermon_plan.json missing." -ForegroundColor Red
    pause
    exit
}

$json = Get-Content $Plan -Raw | ConvertFrom-Json
$html = Get-Content $Panel -Raw

Write-Host "Plan title:"
Write-Host "  $($json.title)"
Write-Host ""

Write-Host "v12 markers present:"
if (
    $html.Contains("// SERMON_AI_PLAN_START") -and
    $html.Contains("// SERMON_AI_PLAN_END")
) {
    Write-Host "  YES" -ForegroundColor Green
}
else {
    Write-Host "  NO" -ForegroundColor Red
}

Write-Host ""
Write-Host "Current sermon title physically embedded in control-panel.html:"
if ($html.Contains($json.title)) {
    Write-Host "  YES" -ForegroundColor Green
}
else {
    Write-Host "  NO" -ForegroundColor Red
}

Write-Host ""
Write-Host "Current Scripture physically embedded:"
if ($html.Contains($json.scripture)) {
    Write-Host "  YES" -ForegroundColor Green
}
else {
    Write-Host "  NO" -ForegroundColor Red
}

Write-Host ""
Read-Host "Press Enter to close"
