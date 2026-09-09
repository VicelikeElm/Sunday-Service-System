$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "================================================================"
Write-Host "SSS DEVELOPMENT CODE-SIGNING CERTIFICATE"
Write-Host "================================================================"
Write-Host ""
Write-Host "WARNING:"
Write-Host "This creates a SELF-SIGNED certificate for LOCAL TESTING only."
Write-Host "It is NOT suitable for public distribution or a real online update feed."
Write-Host ""
Write-Host "It will be trusted only for the CURRENT WINDOWS USER on this PC."
Write-Host ""

$answer = Read-Host "Type TEST to continue"

if ($answer -ne "TEST") {
    Write-Host "Cancelled."
    exit 0
}

$subject = "CN=Sunday Service System Development"

$cert = New-SelfSignedCertificate `
    -Type CodeSigningCert `
    -Subject $subject `
    -CertStoreLocation "Cert:\CurrentUser\My" `
    -HashAlgorithm SHA256 `
    -KeyAlgorithm RSA `
    -KeyLength 3072 `
    -KeyExportPolicy NonExportable `
    -NotAfter (Get-Date).AddYears(2)

$tempCer = Join-Path $env:TEMP "SSS-Development-Code-Signing.cer"

Export-Certificate `
    -Cert $cert `
    -FilePath $tempCer `
    -Force | Out-Null

Import-Certificate `
    -FilePath $tempCer `
    -CertStoreLocation "Cert:\CurrentUser\TrustedPeople" | Out-Null

Import-Certificate `
    -FilePath $tempCer `
    -CertStoreLocation "Cert:\CurrentUser\TrustedPublisher" | Out-Null

Remove-Item -LiteralPath $tempCer -Force -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "[READY] Development certificate created:"
Write-Host ("Subject:    {0}" -f $cert.Subject)
Write-Host ("Thumbprint: {0}" -f $cert.Thumbprint)
Write-Host ("Expires:    {0}" -f $cert.NotAfter)
Write-Host ""
Write-Host "The public certificate was added to CurrentUser\TrustedPeople so this"
Write-Host "machine can validate the development Authenticode signature."
Write-Host ""
Write-Host "NEXT:"
Write-Host "  powershell -ExecutionPolicy Bypass -File Configure-SSS-Code-Signing.ps1"
Write-Host ""
Write-Host "DO NOT use this self-signed certificate for public distribution."
Write-Host ""
