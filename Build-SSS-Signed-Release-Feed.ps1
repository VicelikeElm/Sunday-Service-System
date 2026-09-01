$ErrorActionPreference = "Stop"

$Base = "C:\Church\SermonAI"
$Python = Join-Path $Base "venv\Scripts\python.exe"
$ExpectedPackage = Join-Path $Base "update-output\SundayServiceSystem-Update-v3.1.0.sssupdate"

Write-Host ""
Write-Host "================================================================"
Write-Host "SUNDAY SERVICE SYSTEM - BUILD SIGNED ONLINE RELEASE FEED"
Write-Host "================================================================"
Write-Host ""
Write-Host "This creates a static HTTPS-ready release folder."
Write-Host "It does NOT upload anything automatically."
Write-Host ""

# PRE-FLIGHT FIRST: don't ask the user a bunch of questions only to fail later.
if (-not (Test-Path -LiteralPath $ExpectedPackage)) {
    Write-Host "[FIX] The signed v3.1.0 update package has not been built yet:"
    Write-Host "      $ExpectedPackage"
    Write-Host ""
    Write-Host "Run this FIRST:"
    Write-Host "  Build-SSS-Windows-Installer.bat"
    Write-Host ""
    Write-Host "That build must complete successfully and create:"
    Write-Host "  SundayServiceSystem-Update-v3.1.0.sssupdate"
    Write-Host ""
    Write-Host "Then run this release-feed builder again."
    Write-Host ""
    exit 2
}

Write-Host "[READY] Signed v3.1.0 update package found."
Write-Host "        $ExpectedPackage"
Write-Host ""

Write-Host "You may enter either:"
Write-Host "  1. A GitHub repository URL"
Write-Host "  2. The final HTTPS release-folder URL"
Write-Host ""
Write-Host "Example GitHub repository URL:"
Write-Host "  https://github.com/VicelikeElm/Sunday-Service-System.git"
Write-Host ""

$inputUrl = Read-Host "GitHub repository URL OR final HTTPS release base URL"

if ([string]::IsNullOrWhiteSpace($inputUrl)) {
    throw "A repository URL or HTTPS release base URL is required."
}

$channel = Read-Host "Channel [stable] - enter stable or beta ONLY"

if ([string]::IsNullOrWhiteSpace($channel)) {
    $channel = "stable"
}

$channel = $channel.Trim().ToLowerInvariant()

if ($channel -ne "stable" -and $channel -ne "beta") {
    throw "Channel must be stable or beta. Enter only 'stable' or 'beta'."
}

$baseUrl = $inputUrl.Trim().TrimEnd("/")

$githubMatch = [regex]::Match(
    $baseUrl,
    '^https://github\.com/([^/]+)/([^/]+?)(?:\.git)?$',
    [System.Text.RegularExpressions.RegexOptions]::IgnoreCase
)

if ($githubMatch.Success) {
    $owner = $githubMatch.Groups[1].Value
    $repo = $githubMatch.Groups[2].Value

    $baseUrl = "https://$owner.github.io/$repo/$channel"

    Write-Host ""
    Write-Host "[INFO] GitHub repository detected."
    Write-Host "[INFO] Derived GitHub Pages release URL:"
    Write-Host "       $baseUrl"
    Write-Host ""
    Write-Host "Recommended GitHub Pages publishing source:"
    Write-Host "  Branch: main"
    Write-Host "  Folder: /docs"
    Write-Host ""
}

if (-not $baseUrl.StartsWith("https://", [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "The final release base URL must use HTTPS."
}

Write-Host ""
Write-Host "Optional metadata:"
Write-Host "  - Summary: type a short sentence, or press Enter to skip."
Write-Host "  - Release notes: paste a REAL https:// URL, or press Enter to skip."
Write-Host "    Do NOT type yes/no for either field."
Write-Host ""

$summary = Read-Host "Short release summary [press Enter to skip]"
$notesUrl = Read-Host "HTTPS release-notes URL [press Enter to skip]"

if (-not [string]::IsNullOrWhiteSpace($notesUrl)) {
    if (-not $notesUrl.StartsWith("https://", [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Release-notes URL must be a real HTTPS URL, or leave it blank."
    }
}

$args = @(
    "build_sss_release_feed.py",
    "--base-url", $baseUrl,
    "--channel", $channel
)

if (-not [string]::IsNullOrWhiteSpace($summary)) {
    $args += @("--summary", $summary)
}

if (-not [string]::IsNullOrWhiteSpace($notesUrl)) {
    $args += @("--release-notes-url", $notesUrl)
}

Push-Location $Base
try {
    & $Python @args

    if ($LASTEXITCODE -ne 0) {
        throw "Signed release feed build failed."
    }
}
finally {
    Pop-Location
}

Write-Host ""
Write-Host "[READY] Signed feed output:"
Write-Host "        C:\Church\SermonAI\release-feed-output\$channel"
Write-Host ""
Write-Host "Final public feed URL:"
Write-Host "  $baseUrl/latest.json"
Write-Host ""
Write-Host "For GitHub Pages, put the generated files under:"
Write-Host "  docs\$channel"
Write-Host "in the repository, then publish GitHub Pages from main /docs."
Write-Host ""
Write-Host "Next helper:"
Write-Host "  Stage-SSS-GitHub-Pages-Feed.bat"
Write-Host ""
