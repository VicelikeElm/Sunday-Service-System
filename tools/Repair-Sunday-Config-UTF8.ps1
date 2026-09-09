$ErrorActionPreference = "Stop"

$Path = "C:\Church\SermonAI\sunday_config.json"

if (-not (Test-Path -LiteralPath $Path)) {
    Write-Host "sunday_config.json was not found." -ForegroundColor Red
    Read-Host "Press Enter to close"
    exit 1
}

$Text = [System.IO.File]::ReadAllText($Path)

# U+FEFF is the decoded UTF-8 BOM character if present.
$Text = $Text.TrimStart([char]0xFEFF)

# Validate JSON before rewriting.
$null = $Text | ConvertFrom-Json

$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($Path, $Text, $Utf8NoBom)

Write-Host ""
Write-Host "sunday_config.json repaired as UTF-8 without BOM." -ForegroundColor Green
Write-Host ""
Read-Host "Press Enter to close"
