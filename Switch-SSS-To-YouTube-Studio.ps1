$ErrorActionPreference = "Stop"

$Config = "C:\Church\SermonAI\sunday_config.json"

if (-not (Test-Path -LiteralPath $Config)) {
    Write-Host "sunday_config.json was not found:" -ForegroundColor Red
    Write-Host "  $Config"
    Read-Host "Press Enter to close"
    exit 1
}

$data = Get-Content -LiteralPath $Config -Raw | ConvertFrom-Json

$data.auto_upload_youtube = $false

if ($data.PSObject.Properties.Name -contains "youtube_upload_mode") {
    $data.youtube_upload_mode = "studio"
} else {
    $data | Add-Member -NotePropertyName "youtube_upload_mode" -NotePropertyValue "studio"
}

if ($data.PSObject.Properties.Name -contains "youtube_expected_handle") {
    $data.youtube_expected_handle = "@baptistchurchofperry"
} else {
    $data | Add-Member -NotePropertyName "youtube_expected_handle" -NotePropertyValue "@baptistchurchofperry"
}

if ($data.PSObject.Properties.Name -contains "youtube_expected_channel_name") {
    $data.youtube_expected_channel_name = "Baptist Church of Perry"
} else {
    $data | Add-Member -NotePropertyName "youtube_expected_channel_name" -NotePropertyValue "Baptist Church of Perry"
}

if ($data.PSObject.Properties.Name -contains "youtube_studio_profile_folder") {
    $data.youtube_studio_profile_folder = "C:\Church\SermonAI\YouTube_Studio_Profile"
} else {
    $data | Add-Member -NotePropertyName "youtube_studio_profile_folder" -NotePropertyValue "C:\Church\SermonAI\YouTube_Studio_Profile"
}

$data | ConvertTo-Json -Depth 20 |
    Set-Content -LiteralPath $Config -Encoding UTF8

Write-Host ""
Write-Host "SSS YouTube mode changed to STUDIO." -ForegroundColor Green
Write-Host ""
Write-Host "The v20 YouTube API auto-uploader is disabled."
Write-Host "Expected channel:"
Write-Host "  Baptist Church of Perry"
Write-Host "  @baptistchurchofperry"
Write-Host ""
Write-Host "This is the safe transition state while the Studio browser"
Write-Host "automation is being mapped."
Write-Host ""
Read-Host "Press Enter to close"
