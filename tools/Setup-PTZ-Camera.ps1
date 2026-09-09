$ErrorActionPreference = "Stop"

$Base = "C:\Church\SermonAI"
$ConfigPath = Join-Path $Base "ptz_camera_config.json"

Write-Host ""
Write-Host "============================================================"
Write-Host " PTZ CAMERA SETUP"
Write-Host "============================================================"
Write-Host ""
Write-Host "The camera address is now stored separately in:"
Write-Host ""
Write-Host "  C:\Church\SermonAI\ptz_camera_config.json"
Write-Host ""
Write-Host "That file is NOT part of normal SSS update ZIPs, so future updates"
Write-Host "will not erase the camera IP/presets."
Write-Host ""

$Existing = $null

if (Test-Path -LiteralPath $ConfigPath) {
    try {
        $Existing = Get-Content -LiteralPath $ConfigPath -Raw | ConvertFrom-Json
    } catch {
        $Existing = $null
    }
}

$OldIP = ""
$OldWorship = 1
$OldPastor = 2

if ($Existing) {
    if ($Existing.ptz_camera_ip) {
        $OldIP = [string]$Existing.ptz_camera_ip
    }

    if ($Existing.ptz_worship_preset -ne $null) {
        $OldWorship = [int]$Existing.ptz_worship_preset
    }

    if ($Existing.ptz_pastor_preset -ne $null) {
        $OldPastor = [int]$Existing.ptz_pastor_preset
    }
}

$PromptIP = "PTZ camera IP/address"
if ($OldIP) {
    $PromptIP += " [$OldIP]"
}

$CameraIP = Read-Host $PromptIP

if ([string]::IsNullOrWhiteSpace($CameraIP)) {
    $CameraIP = $OldIP
}

if ([string]::IsNullOrWhiteSpace($CameraIP)) {
    Write-Host ""
    Write-Host "Camera IP cannot be blank." -ForegroundColor Red
    Read-Host "Press Enter to close"
    exit 1
}

$Worship = Read-Host "Worship preset [$OldWorship]"
if ([string]::IsNullOrWhiteSpace($Worship)) {
    $Worship = [string]$OldWorship
}

$Pastor = Read-Host "Pastor preset [$OldPastor]"
if ([string]::IsNullOrWhiteSpace($Pastor)) {
    $Pastor = [string]$OldPastor
}

$data = [ordered]@{
    ptz_camera_enabled = $true
    ptz_camera_ip = $CameraIP.Trim()
    ptz_camera_scheme = "http"
    ptz_camera_http_port = ""
    ptz_camera_username = ""
    ptz_camera_password = ""
    ptz_camera_timeout_seconds = 4
    ptz_auto_recall_on_sss_start = $true
    ptz_startup_preset = [int]$Pastor
    ptz_worship_preset = [int]$Worship
    ptz_pastor_preset = [int]$Pastor
}

$Json = $data | ConvertTo-Json -Depth 10
$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)

[System.IO.File]::WriteAllText(
    $ConfigPath,
    $Json,
    $Utf8NoBom
)

Write-Host ""
Write-Host "PTZ settings saved permanently." -ForegroundColor Green
Write-Host ""
Write-Host "Camera:           $CameraIP"
Write-Host "Startup position: Pastor preset $Pastor"
Write-Host "Worship button:   Preset $Worship"
Write-Host "Pastor button:    Preset $Pastor"
Write-Host ""
Write-Host "Would you like to TEST the Pastor preset now?"
Write-Host "This WILL MOVE THE CAMERA." -ForegroundColor Yellow
Write-Host ""

$Test = Read-Host "Type YES to test"

if ($Test -eq "YES") {
    & "$Base\venv\Scripts\python.exe" "$Base\ptz_camera_control.py" pastor
    Write-Host ""
}

Read-Host "Press Enter to close"
