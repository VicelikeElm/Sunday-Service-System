$ErrorActionPreference = "Stop"

$File = "C:\Church\SermonAI\dist\SundayServiceSystem\SundayServiceSystem.exe"

Write-Host ""
Write-Host "================================================================"
Write-Host "SSS - BUILT EXE AUTHENTICODE CHECK"
Write-Host "================================================================"
Write-Host ""

if (-not (Test-Path -LiteralPath $File)) {
    throw "Built Main EXE does not exist: $File"
}

$sig = Get-AuthenticodeSignature -LiteralPath $File

Write-Host ("Status:         {0}" -f $sig.Status)
Write-Host ("StatusMessage:  {0}" -f $sig.StatusMessage)

if ($sig.SignerCertificate) {
    Write-Host ("Signer:         {0}" -f $sig.SignerCertificate.Subject)
    Write-Host ("Thumbprint:     {0}" -f $sig.SignerCertificate.Thumbprint)
}

if ($sig.TimeStamperCertificate) {
    Write-Host ("Timestamp CA:   {0}" -f $sig.TimeStamperCertificate.Subject)
}

Write-Host ""
Write-Host "This diagnostic is READ-ONLY."
Write-Host ""
