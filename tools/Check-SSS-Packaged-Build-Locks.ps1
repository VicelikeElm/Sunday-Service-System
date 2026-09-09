$ErrorActionPreference = "Stop"

$Root = "C:\Church\SermonAI\dist\"

try {
    $processes = @(
        Get-CimInstance Win32_Process |
            Where-Object {
                $_.ExecutablePath -and
                $_.ExecutablePath.StartsWith(
                    $Root,
                    [System.StringComparison]::OrdinalIgnoreCase
                )
            }
    )

    if ($processes.Count -gt 0) {
        foreach ($process in $processes) {
            Write-Host ("[FIX] Still running: {0} PID {1}" -f $process.Name, $process.ProcessId)
            Write-Host ("      {0}" -f $process.ExecutablePath)
        }

        exit 11
    }

    Write-Host "[READY] No old packaged SSS EXE is running."
    exit 0
}
catch {
    Write-Host "[FIX] Packaged-build lock check failed:"
    Write-Host $_.Exception.Message
    exit 2
}
