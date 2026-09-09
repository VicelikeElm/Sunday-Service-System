$ErrorActionPreference = "Stop"

$Base = "C:\Church\SermonAI"
$ConfigPath = Join-Path $Base "sss_signing_config.json"

Write-Host ""
Write-Host "================================================================"
Write-Host "SUNDAY SERVICE SYSTEM - ONE-CLICK DEVELOPMENT SIGNING SETUP"
Write-Host "================================================================"
Write-Host ""
Write-Host "LOCAL TESTING ONLY - not a public/commercial signing identity."
Write-Host ""

$answer = Read-Host "Type TEST to continue"

if ($answer -ne "TEST") {
    Write-Host "Cancelled."
    exit 0
}

$subject = "CN=Sunday Service System Development"
$ekuCodeSigning = "1.3.6.1.5.5.7.3.3"

$certs = Get-ChildItem -Path "Cert:\CurrentUser\My" |
    Where-Object {
        $_.Subject -eq $subject -and
        $_.HasPrivateKey -and
        ($_.EnhancedKeyUsageList.ObjectId.Value -contains $ekuCodeSigning)
    } |
    Sort-Object NotAfter -Descending

$cert = $certs | Select-Object -First 1

if (-not $cert) {
    $cert = New-SelfSignedCertificate `
        -Type CodeSigningCert `
        -Subject $subject `
        -CertStoreLocation "Cert:\CurrentUser\My" `
        -HashAlgorithm SHA256 `
        -KeyAlgorithm RSA `
        -KeyLength 3072 `
        -KeyExportPolicy NonExportable `
        -NotAfter (Get-Date).AddYears(2)

    Write-Host "[READY] Development certificate created."
} else {
    Write-Host "[READY] Existing development certificate found."
}

$tempCer = Join-Path $env:TEMP "SSS-Development-Code-Signing.cer"

Export-Certificate `
    -Cert $cert `
    -FilePath $tempCer `
    -Force | Out-Null

foreach ($store in @("TrustedPeople","TrustedPublisher")) {
    $target = "Cert:\CurrentUser\$store\$($cert.Thumbprint)"
    $existing = Get-Item -LiteralPath $target -ErrorAction SilentlyContinue

    if (-not $existing) {
        Import-Certificate `
            -FilePath $tempCer `
            -CertStoreLocation "Cert:\CurrentUser\$store" | Out-Null

        Write-Host ("[READY] Public certificate added to CurrentUser\{0}" -f $store)
    }
    else {
        Write-Host ("[READY] Public certificate already in CurrentUser\{0}" -f $store)
    }
}

Remove-Item -LiteralPath $tempCer -Force -ErrorAction SilentlyContinue

$signtool = Get-Command signtool.exe -ErrorAction SilentlyContinue
$signtoolPath = $null

if ($signtool) {
    $signtoolPath = $signtool.Source
    if ([string]::IsNullOrWhiteSpace([string]$signtoolPath)) {
        $signtoolPath = $signtool.Path
    }
}

if ([string]::IsNullOrWhiteSpace([string]$signtoolPath)) {
    $roots = @(
        "${env:ProgramFiles(x86)}\Windows Kits\10\bin",
        "${env:ProgramFiles}\Windows Kits\10\bin"
    )

    $candidates = @()

    foreach ($root in $roots) {
        if (Test-Path -LiteralPath $root) {
            $candidates += Get-ChildItem `
                -Path $root `
                -Filter signtool.exe `
                -Recurse `
                -ErrorAction SilentlyContinue |
                Where-Object { $_.FullName -match '\\x64\\signtool\.exe$' }
        }
    }

    if ($candidates) {
        $signtoolPath = (
            $candidates |
            Sort-Object FullName -Descending |
            Select-Object -First 1
        ).FullName
    }
}

if ([string]::IsNullOrWhiteSpace([string]$signtoolPath)) {
    Write-Host "[FIX] Microsoft SignTool was not found."
    exit 2
}

# DigiCert's documented RFC3161 SignTool endpoint.
$timestamp = "http://timestamp.digicert.com"

$config = [ordered]@{
    certificate_thumbprint = $cert.Thumbprint
    certificate_store = "CurrentUser"
    update_manifest_thumbprint = ""
    timestamp_url = $timestamp
    signtool_path = $signtoolPath
    publisher_name = "Sunday Service System Development"
}

$config |
    ConvertTo-Json -Depth 5 |
    Set-Content -LiteralPath $ConfigPath -Encoding UTF8

Write-Host ""
Write-Host "[READY] Created:"
Write-Host "        $ConfigPath"
Write-Host "[READY] RFC3161 timestamp:"
Write-Host "        $timestamp"
Write-Host "Private key exported: NO"
Write-Host ""

$Checker = Join-Path $Base "tools\Check-SSS-Code-Signing.ps1"

if (Test-Path -LiteralPath $Checker) {
    & powershell.exe `
        -NoProfile `
        -ExecutionPolicy Bypass `
        -File $Checker

    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

Write-Host ""
Write-Host "[READY] DEVELOPMENT SIGNING SETUP COMPLETE"
Write-Host "Now run Build-SSS-Windows-Installer.bat"
Write-Host ""
