$ErrorActionPreference = "Stop"

$ConfigPath = "C:\Church\SermonAI\sss_signing_config.json"
$Correct = "http://timestamp.digicert.com"

Write-Host ""
Write-Host "================================================================"
Write-Host "SSS - FIX RFC3161 TIMESTAMP URL"
Write-Host "================================================================"
Write-Host ""

if (-not (Test-Path -LiteralPath $ConfigPath)) {
    throw "Signing config not found: $ConfigPath"
}

$config = Get-Content -LiteralPath $ConfigPath -Raw | ConvertFrom-Json

$old = [string]$config.timestamp_url

Write-Host "Current:"
Write-Host "  $old"
Write-Host ""
Write-Host "DigiCert RFC3161 SignTool endpoint:"
Write-Host "  $Correct"
Write-Host ""

$config.timestamp_url = $Correct

$config |
    ConvertTo-Json -Depth 10 |
    Set-Content -LiteralPath $ConfigPath -Encoding UTF8

Write-Host "[READY] Updated:"
Write-Host "        $ConfigPath"
Write-Host ""
Write-Host "Now run:"
Write-Host "  Build-SSS-Windows-Installer.bat"
Write-Host ""
