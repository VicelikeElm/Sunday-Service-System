$ErrorActionPreference = "SilentlyContinue"

$Profile = "C:\Church\SermonAI\YouTube_Studio_Profile"
$escaped = [Regex]::Escape($Profile)

$processes = @(
    Get-CimInstance Win32_Process |
        Where-Object {
            $_.CommandLine -and
            $_.CommandLine -match $escaped -and
            (
                $_.Name -ieq "chrome.exe" -or
                $_.Name -ieq "msedge.exe"
            )
        }
)

Write-Host ""
Write-Host "============================================================"
Write-Host " Close Dedicated YouTube Studio Browser"
Write-Host "============================================================"
Write-Host ""

if ($processes.Count -eq 0) {
    Write-Host "No browser process is using the dedicated Studio profile." -ForegroundColor Green
    Write-Host ""
    Read-Host "Press Enter to close"
    exit 0
}

Write-Host "Only processes using this profile will be closed:" -ForegroundColor Yellow
Write-Host "  $Profile"
Write-Host ""
Write-Host "Your normal Chrome/Edge profile will NOT be targeted."
Write-Host ""

foreach ($p in $processes) {
    Write-Host "Closing $($p.Name) PID $($p.ProcessId)"
    Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
}

Start-Sleep -Seconds 2

$remaining = @(
    Get-CimInstance Win32_Process |
        Where-Object {
            $_.CommandLine -and
            $_.CommandLine -match $escaped -and
            (
                $_.Name -ieq "chrome.exe" -or
                $_.Name -ieq "msedge.exe"
            )
        }
)

Write-Host ""

if ($remaining.Count -eq 0) {
    Write-Host "Dedicated Studio browser is fully closed." -ForegroundColor Green
} else {
    Write-Host "Some dedicated profile processes remain." -ForegroundColor Red
    Write-Host "Restart Windows or close them in Task Manager before running the diagnostic."
}

Write-Host ""
Read-Host "Press Enter to close"
