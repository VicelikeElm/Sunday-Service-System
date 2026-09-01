$ErrorActionPreference = "Stop"

$ConfigPath = "C:\Church\SermonAI\sss_signing_config.json"

Write-Host ""
Write-Host "================================================================"
Write-Host "SSS - REPAIR DEVELOPMENT CODE-SIGNING TRUST"
Write-Host "================================================================"
Write-Host ""
Write-Host "LOCAL DEVELOPMENT CERTIFICATE ONLY."
Write-Host ""
Write-Host "This adds the PUBLIC development certificate to:"
Write-Host "  CurrentUser\TrustedPeople"
Write-Host "  CurrentUser\TrustedPublisher"
Write-Host ""
Write-Host "It does NOT add the self-signed certificate to Trusted Root."
Write-Host "It does NOT export the private key."
Write-Host ""

if (-not (Test-Path -LiteralPath $ConfigPath)) {
    throw "Signing config not found: $ConfigPath"
}

$config = Get-Content -LiteralPath $ConfigPath -Raw | ConvertFrom-Json
$thumb = ([string]$config.certificate_thumbprint).Replace(" ","").ToUpper()

if ([string]::IsNullOrWhiteSpace($thumb)) {
    throw "Signing config has no certificate_thumbprint."
}

$cert = Get-Item -LiteralPath "Cert:\CurrentUser\My\$thumb" -ErrorAction SilentlyContinue

if (-not $cert) {
    throw "Configured development certificate was not found in CurrentUser\My: $thumb"
}

if ($cert.Subject -ne "CN=Sunday Service System Development") {
    throw "Configured certificate is not the SSS Development certificate. No trust stores were changed."
}

if (-not $cert.HasPrivateKey) {
    throw "Configured development certificate has no accessible private key."
}

$tempCer = Join-Path $env:TEMP "SSS-Development-Code-Signing-$thumb.cer"

Export-Certificate `
    -Cert $cert `
    -FilePath $tempCer `
    -Force | Out-Null

foreach ($store in @("TrustedPeople","TrustedPublisher")) {
    $target = "Cert:\CurrentUser\$store\$thumb"
    $existing = Get-Item -LiteralPath $target -ErrorAction SilentlyContinue

    if ($existing) {
        Write-Host ("[READY] Already present in CurrentUser\{0}" -f $store)
    }
    else {
        Import-Certificate `
            -FilePath $tempCer `
            -CertStoreLocation "Cert:\CurrentUser\$store" | Out-Null

        Write-Host ("[READY] Added public certificate to CurrentUser\{0}" -f $store)
    }
}

Remove-Item -LiteralPath $tempCer -Force -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "Certificate:"
Write-Host ("  {0}" -f $cert.Subject)
Write-Host ("  {0}" -f $cert.Thumbprint)
Write-Host ""
Write-Host "Private key exported: NO"
Write-Host ""
Write-Host "[READY] Development publisher trust repaired."
Write-Host ""
Write-Host "Now run:"
Write-Host "  Build-SSS-Windows-Installer.bat"
Write-Host ""
