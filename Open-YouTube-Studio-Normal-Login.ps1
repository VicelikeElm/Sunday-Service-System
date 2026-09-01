$ErrorActionPreference = "Stop"

$Profile = "C:\Church\SermonAI\YouTube_Studio_Profile"
$Url = "https://studio.youtube.com/channel/UCXwqRxA_JKNM3g6JDe76DcQ?c=UCXwqRxA_JKNM3g6JDe76DcQ"

$Candidates = @(
    "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
    "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
    "$env:LocalAppData\Google\Chrome\Application\chrome.exe",
    "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe",
    "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe"
)

$Browser = $Candidates |
    Where-Object { $_ -and (Test-Path -LiteralPath $_) } |
    Select-Object -First 1

if (-not $Browser) {
    Write-Host "Chrome or Edge was not found." -ForegroundColor Red
    Read-Host "Press Enter to close"
    exit 1
}

New-Item -ItemType Directory -Path $Profile -Force | Out-Null

Write-Host ""
Write-Host "Opening the dedicated YouTube Studio profile normally."
Write-Host ""
Write-Host "Expected channel:"
Write-Host "  Baptist Church of Perry"
Write-Host "  @baptistchurchofperry"
Write-Host ""
Write-Host "Studio should also show:"
Write-Host "  You're a manager"
Write-Host ""
Write-Host "Close ALL dedicated Studio browser windows when finished."
Write-Host ""

Start-Process -FilePath $Browser -ArgumentList @(
    "--user-data-dir=$Profile",
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-background-mode",
    $Url
)

Read-Host "Press Enter after closing the dedicated Studio browser"
