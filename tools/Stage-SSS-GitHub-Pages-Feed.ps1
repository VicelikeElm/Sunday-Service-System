param(
    [string]$RepoPath = "",
    [ValidateSet("stable","beta")]
    [string]$Channel = "stable"
)

$ErrorActionPreference = "Stop"

$Base = "C:\Church\SermonAI"
$Source = Join-Path $Base "release-feed-output\$Channel"
$DefaultCloneRoot = Join-Path $Base "GitHub"

Write-Host ""
Write-Host "================================================================"
Write-Host "SSS - STAGE RELEASE FEED FOR GITHUB PAGES"
Write-Host "================================================================"
Write-Host ""

if (-not (Test-Path -LiteralPath (Join-Path $Source "latest.json"))) {
    throw "Signed release feed not found. Run Build-SSS-Signed-Release-Feed.bat first."
}

if ([string]::IsNullOrWhiteSpace($RepoPath)) {
    Write-Host "You may enter either:"
    Write-Host "  1. The LOCAL cloned repository folder"
    Write-Host "     Example: C:\Users\Vicel\Documents\GitHub\Sunday-Service-System"
    Write-Host ""
    Write-Host "  2. The GitHub repository URL"
    Write-Host "     Example: https://github.com/VicelikeElm/Sunday-Service-System.git"
    Write-Host ""
    $RepoPath = Read-Host "Local repo folder OR GitHub repository URL"
}

if ([string]::IsNullOrWhiteSpace($RepoPath)) {
    throw "Repository path or GitHub URL is required."
}

$RepoPath = $RepoPath.Trim()

# If the operator pasted the GitHub URL instead of a local Windows path,
# derive a safe local clone path and clone only after explicit confirmation.
$githubMatch = [regex]::Match(
    $RepoPath,
    '^https://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$',
    [System.Text.RegularExpressions.RegexOptions]::IgnoreCase
)

if ($githubMatch.Success) {
    $owner = $githubMatch.Groups[1].Value
    $repo = $githubMatch.Groups[2].Value

    $cloneRoot = $DefaultCloneRoot
    $localRepo = Join-Path $cloneRoot $repo

    Write-Host ""
    Write-Host "[INFO] GitHub repository URL detected:"
    Write-Host "       $RepoPath"
    Write-Host ""
    Write-Host "[INFO] Local repository location:"
    Write-Host "       $localRepo"
    Write-Host ""

    if (-not (Test-Path -LiteralPath $localRepo)) {
        $git = Get-Command git.exe -ErrorAction SilentlyContinue

        if (-not $git) {
            throw @"
GitHub URL was entered, but the repository is not cloned locally and Git was
not found.

Either:
  - install Git for Windows, then rerun this helper, or
  - clone the repository yourself and enter its LOCAL folder path.
"@
        }

        $answer = Read-Host "Clone the repository there now? [Y/n]"

        if ([string]::IsNullOrWhiteSpace($answer)) {
            $answer = "Y"
        }

        if ($answer.Trim().ToUpperInvariant() -ne "Y") {
            throw "Repository clone cancelled. Enter an existing LOCAL repository folder instead."
        }

        New-Item -ItemType Directory -Path $cloneRoot -Force | Out-Null

        Write-Host ""
        Write-Host "Cloning repository..."
        Write-Host ""

        & $git.Source clone $RepoPath $localRepo

        if ($LASTEXITCODE -ne 0) {
            throw "git clone failed."
        }
    }

    $RepoPath = $localRepo
}

# From here on, RepoPath MUST be a local filesystem path.
if ($RepoPath -match '^[a-zA-Z]+://') {
    throw "Repository staging requires a LOCAL filesystem path, not a web URL."
}

if (-not (Test-Path -LiteralPath $RepoPath)) {
    throw "Local repository folder does not exist: $RepoPath"
}

$RepoPath = (Resolve-Path -LiteralPath $RepoPath).Path

$gitFolder = Join-Path $RepoPath ".git"

if (-not (Test-Path -LiteralPath $gitFolder)) {
    Write-Host ""
    Write-Host "[CHECK] This folder does not contain a .git directory:"
    Write-Host "        $RepoPath"
    Write-Host ""
    $continue = Read-Host "Stage the GitHub Pages files there anyway? [y/N]"

    if ($continue.Trim().ToUpperInvariant() -ne "Y") {
        throw "Staging cancelled. Choose the local cloned repository folder."
    }
}

$Docs = Join-Path $RepoPath "docs"
$Destination = Join-Path $Docs $Channel

New-Item -ItemType Directory -Path $Destination -Force | Out-Null

# Remove only old release files in this channel folder, never arbitrary repo data.
Get-ChildItem -LiteralPath $Destination -File -ErrorAction SilentlyContinue |
    Where-Object {
        $_.Name -eq "latest.json" -or
        $_.Name -eq "latest.json.p7s" -or
        $_.Extension -eq ".sssupdate"
    } |
    Remove-Item -Force

Copy-Item `
    -LiteralPath (Join-Path $Source "latest.json") `
    -Destination $Destination `
    -Force

Copy-Item `
    -LiteralPath (Join-Path $Source "latest.json.p7s") `
    -Destination $Destination `
    -Force

$package = Get-ChildItem -LiteralPath $Source -Filter "*.sssupdate" |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1

if (-not $package) {
    throw "No .sssupdate package was found in $Source"
}

Copy-Item `
    -LiteralPath $package.FullName `
    -Destination $Destination `
    -Force

New-Item `
    -ItemType File `
    -Path (Join-Path $Docs ".nojekyll") `
    -Force | Out-Null

$index = Join-Path $Docs "index.html"

if (-not (Test-Path -LiteralPath $index)) {
    @'
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Sunday Service System Updates</title>
</head>
<body>
  <h1>Sunday Service System Updates</h1>
  <p>This site hosts signed Sunday Service System release metadata and packages.</p>
</body>
</html>
'@ | Set-Content -LiteralPath $index -Encoding UTF8
}

Write-Host ""
Write-Host "================================================================"
Write-Host "[READY] GITHUB PAGES FILES STAGED"
Write-Host "================================================================"
Write-Host ""
Write-Host "Local repository:"
Write-Host "  $RepoPath"
Write-Host ""
Write-Host "Staged release folder:"
Write-Host "  $Destination"
Write-Host ""
Write-Host "Files:"
Get-ChildItem -LiteralPath $Destination -File |
    ForEach-Object {
        Write-Host ("  {0}" -f $_.Name)
    }

Write-Host ""
Write-Host "Nothing was committed or pushed automatically."
Write-Host ""

$git = Get-Command git.exe -ErrorAction SilentlyContinue

if ($git -and (Test-Path -LiteralPath $gitFolder)) {
    Write-Host "Current git status:"
    Write-Host ""

    Push-Location $RepoPath
    try {
        & $git.Source status --short
    }
    finally {
        Pop-Location
    }

    Write-Host ""
    Write-Host "When ready, from the repository folder run:"
    Write-Host ""
    Write-Host "  git add docs"
    Write-Host ('  git commit -m "Publish SSS {0} update feed"' -f $Channel)
    Write-Host "  git push"
    Write-Host ""
}

Write-Host "Then on GitHub:"
Write-Host "  Settings -> Pages"
Write-Host "  Source: Deploy from a branch"
Write-Host "  Branch: main"
Write-Host "  Folder: /docs"
Write-Host ""
