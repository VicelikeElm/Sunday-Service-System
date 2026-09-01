$ErrorActionPreference = "Stop"

$Base = "C:\Church\SermonAI"
$Python = Join-Path $Base "venv\Scripts\python.exe"

Write-Host ""
Write-Host "================================================================"
Write-Host "SUNDAY SERVICE SYSTEM - ONLINE UPDATE FEED"
Write-Host "================================================================"
Write-Host ""
Write-Host "Feed URL must be HTTPS and normally ends in:"
Write-Host "  /latest.json"
Write-Host ""
Write-Host "SSS automatically expects the detached signature at:"
Write-Host "  <feed-url>.p7s"
Write-Host ""

$url = Read-Host "HTTPS feed URL"

if ([string]::IsNullOrWhiteSpace($url)) {
    throw "Feed URL is required."
}

$channel = Read-Host "Channel [stable]"

if ([string]::IsNullOrWhiteSpace($channel)) {
    $channel = "stable"
}

& $Python -c "from sss_update_feed import save_feed_config; import sys; c=save_feed_config(feed_url=sys.argv[1],channel=sys.argv[2],enabled=True); print('Feed saved:',c['feed_url']); print('Channel:',c['channel'])" $url $channel

if ($LASTEXITCODE -ne 0) {
    throw "Could not save online update feed."
}

Write-Host ""
Write-Host "[READY] Feed configured."
Write-Host ""
Write-Host "Next:"
Write-Host "  Check-SSS-Online-Update-Feed.bat"
Write-Host ""
