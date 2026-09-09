$ErrorActionPreference = "Stop"

$Base = "C:\Church\SermonAI"
$ArchiveRoot = Join-Path $Base "Cleanup_Archive"
$Stamp = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
$Archive = Join-Path $ArchiveRoot ("v22_legacy_" + $Stamp)

$Legacy = @(
    "README_V8_SERMON_EMAIL.txt",
    "README_V11.txt",
    "README_V12.txt",
    "README_V13.txt",
    "README_V14.txt",
    "README_V15.txt",
    "README_V16_OBS_AUTOSTART.txt",
    "README_V17_PLANNING.txt",
    "README_V18_STABILITY.txt",
    "README_V19_AUTO_LAUNCH.txt",
    "README_V20_YOUTUBE_UPLOAD.txt",
    "README_V21_YOUTUBE_STUDIO.txt",
    "Install-Lower-Third-Sermon-Loader.bat",
    "install_sermon_plan_loader.py",
    "sermon_plan_loader.js",
    "sermon_plan_server.py",
    "Restore-Pre-v12-Control-Panel.bat",
    "Restore-Pre-v12-Control-Panel.ps1",
    "youtube_upload_worker.py",
    "planning_diagnostic.py",
    "planning_edit_diagnostic.py",
    "planning_service_discovery.py",
    "Planning-Diagnostic.bat",
    "Planning-Edit-Diagnostic.bat",
    "Planning-Service-Discovery.bat",
    "Planning_Diagnostic.txt",
    "Planning_Diagnostic.png",
    "Planning_Edit_Diagnostic.txt",
    "Planning_Edit_Diagnostic.png",
    "Planning_Service_Discovery.txt",
    "Planning_Service_Discovery.png",
    "Planning_Service_Discovery_Error.txt",
    "control-panel-v10-template.html",
    "control-panel-v11-template.html",
    "control-panel-v12-template.html",
    "control-panel-v13-template.html",
    "control-panel-v14-template.html",
    "sermon-plan-data.js"
)

$Moved = 0

foreach ($Name in $Legacy) {
    $Source = Join-Path $Base $Name

    if (-not (Test-Path -LiteralPath $Source)) {
        continue
    }

    if (-not (Test-Path -LiteralPath $Archive)) {
        New-Item -ItemType Directory -Path $Archive -Force | Out-Null
    }

    Move-Item -LiteralPath $Source -Destination (Join-Path $Archive $Name) -Force
    $Moved++
}

if ($Moved -gt 0) {
    Write-Host ""
    Write-Host "Archived $Moved obsolete pre-v22 file(s) to:" -ForegroundColor Green
    Write-Host "  $Archive"
    Write-Host ""
} else {
    Write-Host ""
    Write-Host "No obsolete pre-v22 files needed archiving."
    Write-Host ""
}
