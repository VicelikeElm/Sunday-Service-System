$ErrorActionPreference = "Continue"

$Base = "C:\Church\SermonAI"
$ConfigPath = Join-Path $Base "sss_signing_config.json"

Write-Host ""
Write-Host "================================================================"
Write-Host "SUNDAY SERVICE SYSTEM - CODE SIGNING CHECK"
Write-Host "================================================================"
Write-Host ""

if (-not (Test-Path -LiteralPath $ConfigPath)) {
    Write-Host "[FIX] Signing config missing:"
    Write-Host "      $ConfigPath"
    Write-Host ""
    Write-Host "Run:"
    Write-Host "  powershell -ExecutionPolicy Bypass -File Configure-SSS-Code-Signing.ps1"
    exit 1
}

$config = Get-Content -LiteralPath $ConfigPath -Raw | ConvertFrom-Json

$thumb = ([string]$config.certificate_thumbprint).Replace(" ","").ToUpper()
$store = [string]$config.certificate_store

if ($store -ne "LocalMachine") {
    $store = "CurrentUser"
}

$certPath = "Cert:\$store\My\$thumb"
$cert = Get-Item -LiteralPath $certPath -ErrorAction SilentlyContinue

if (-not $cert) {
    Write-Host "[FIX] Signing certificate not found:"
    Write-Host "      $certPath"
    exit 1
}

if (-not $cert.HasPrivateKey) {
    Write-Host "[FIX] Certificate exists but its private key is not available."
    exit 1
}

Write-Host "[READY] Certificate:"
Write-Host ("        {0}" -f $cert.Subject)
Write-Host ("        Thumbprint: {0}" -f $cert.Thumbprint)
Write-Host ("        Expires:    {0}" -f $cert.NotAfter)
Write-Host ""

$signtool = Get-Command signtool.exe -ErrorAction SilentlyContinue

if (-not $signtool) {
    $candidates = @()

    $roots = @(
        "${env:ProgramFiles(x86)}\Windows Kits\10\bin",
        "${env:ProgramFiles}\Windows Kits\10\bin"
    )

    foreach ($root in $roots) {
        if (Test-Path $root) {
            $candidates += Get-ChildItem -Path $root -Filter signtool.exe -Recurse -ErrorAction SilentlyContinue |
                Where-Object { $_.FullName -match '\\x64\\signtool\.exe$' } |
                Sort-Object FullName -Descending
        }
    }

    if ($candidates) {
        $signtool = $candidates[0]
    }
}

if (-not $signtool) {
    Write-Host "[FIX] Microsoft SignTool was not found."
    Write-Host "      Install the Windows SDK Signing Tools component."
    exit 1
}

$signtoolPath = $signtool.Source
if ([string]::IsNullOrWhiteSpace([string]$signtoolPath)) {
    $signtoolPath = $signtool.FullName
}

Write-Host "[READY] SignTool:"
Write-Host ("        {0}" -f $signtoolPath)
Write-Host ""

if ([string]::IsNullOrWhiteSpace([string]$config.timestamp_url)) {
    Write-Host "[FIX] timestamp_url is blank."
    Write-Host "      SSS release signing requires RFC 3161 timestamping."
    exit 1
}

Write-Host "[READY] RFC 3161 timestamp URL:"
Write-Host ("        {0}" -f $config.timestamp_url)
Write-Host ""

Write-Host "Signing configuration is READY."
Write-Host "No private key or password was exported by this check."
Write-Host ""
