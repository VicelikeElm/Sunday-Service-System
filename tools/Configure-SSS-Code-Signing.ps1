param(
    [ValidateSet("CurrentUser","LocalMachine")]
    [string]$Store = "CurrentUser"
)

$ErrorActionPreference = "Stop"

$Base = "C:\Church\SermonAI"
$ConfigPath = Join-Path $Base "sss_signing_config.json"

Write-Host ""
Write-Host "================================================================"
Write-Host "SUNDAY SERVICE SYSTEM - CODE SIGNING CONFIGURATION"
Write-Host "================================================================"
Write-Host ""
Write-Host "This writes PUBLIC certificate selection metadata only."
Write-Host "It does NOT export or copy the private key."
Write-Host ""

$storePath = "Cert:\$Store\My"

$certs = Get-ChildItem -Path $storePath |
    Where-Object {
        $_.HasPrivateKey -and
        ($_.EnhancedKeyUsageList.ObjectId.Value -contains "1.3.6.1.5.5.7.3.3")
    } |
    Sort-Object NotAfter -Descending

if (-not $certs) {
    Write-Host "[FIX] No code-signing certificate with an accessible private key was found in:"
    Write-Host "      $storePath"
    Write-Host ""
    Write-Host "For local TESTING only, you can run:"
    Write-Host "  Create-SSS-Development-Signing-Certificate.ps1"
    Write-Host ""
    Write-Host "For production/public distribution, use a certificate from a trusted"
    Write-Host "code-signing certificate provider."
    exit 1
}

Write-Host "Available code-signing certificates:"
Write-Host ""

for ($i = 0; $i -lt $certs.Count; $i++) {
    $cert = $certs[$i]
    Write-Host ("[{0}] {1}" -f ($i + 1), $cert.Subject)
    Write-Host ("    Thumbprint: {0}" -f $cert.Thumbprint)
    Write-Host ("    Expires:    {0}" -f $cert.NotAfter)
    Write-Host ""
}

$selection = Read-Host "Choose certificate number"
$index = 0

if (-not [int]::TryParse($selection, [ref]$index)) {
    throw "Invalid certificate selection."
}

$index--

if ($index -lt 0 -or $index -ge $certs.Count) {
    throw "Certificate selection is out of range."
}

$selected = $certs[$index]

$timestamp = Read-Host "RFC 3161 timestamp URL [http://timestamp.digicert.com]"

if ([string]::IsNullOrWhiteSpace($timestamp)) {
    $timestamp = "http://timestamp.digicert.com"
}

$config = [ordered]@{
    certificate_thumbprint = $selected.Thumbprint
    certificate_store = $Store
    update_manifest_thumbprint = ""
    timestamp_url = $timestamp
    signtool_path = ""
    publisher_name = "Sunday Service System"
}

$config |
    ConvertTo-Json -Depth 5 |
    Set-Content -LiteralPath $ConfigPath -Encoding UTF8

Write-Host ""
Write-Host "[READY] Wrote:"
Write-Host "        $ConfigPath"
Write-Host ""
Write-Host "Certificate:"
Write-Host ("  {0}" -f $selected.Subject)
Write-Host ("  {0}" -f $selected.Thumbprint)
Write-Host ""
Write-Host "Private key exported: NO"
Write-Host ""
Write-Host "Next run:"
Write-Host "  Check-SSS-Code-Signing.bat"
Write-Host "then:"
Write-Host "  Build-SSS-Windows-Installer.bat"
Write-Host ""
