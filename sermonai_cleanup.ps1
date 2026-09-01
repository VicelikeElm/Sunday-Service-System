param(
    [switch]$Apply,
    [switch]$UndoLast
)

$ErrorActionPreference = "Stop"

$Base = "C:\Church\SermonAI"
$ArchiveRoot = Join-Path $Base "Cleanup_Archive"
$ManifestRoot = Join-Path $ArchiveRoot "_Manifests"

function Write-Header {
    param([string]$Title)
    Write-Host ""
    Write-Host ("=" * 72)
    Write-Host (" " + $Title)
    Write-Host ("=" * 72)
    Write-Host ""
}

function Normalize-RelativePath {
    param([string]$FullPath)

    $baseFull = [System.IO.Path]::GetFullPath($Base).TrimEnd("\")
    $itemFull = [System.IO.Path]::GetFullPath($FullPath)

    if (-not $itemFull.StartsWith($baseFull, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing path outside SermonAI: $FullPath"
    }

    return $itemFull.Substring($baseFull.Length).TrimStart("\")
}

function Is-ProtectedPath {
    param([string]$RelativePath)

    $rel = $RelativePath.Replace("/", "\")

    $protectedExact = @(
        ".env",
        "gmail_credentials.json",
        "gmail_token.json",
        "sermon_plan.json",
        "sermon_plan.example.json",
        "planning_update_status.json",
        "sunday_config.json",
        "sunday_mode.py",
        "sunday_common.py",
        "sunday_action.py",
        "chapter_bridge.py",
        "gmail_sermon_importer.py",
        "planning_update_sermon.py",
        "sync_sermon_plan_to_lower_thirds.py",
        "obs_startup_cleanup.py",
        "clean_current_sermon_plan.py",
        "control-panel-v15-template.html",
        "start_sunday_mode.bat",
        "start_sunday_mode_hidden.vbs",
        "Import-Latest-Sermon-Email.bat",
        "Sync-Current-Sermon-Plan.bat",
        "Check-Chapter-Bridge.bat",
        "Check-Chapter-Bridge.ps1",
        "Clean-Current-Sermon-Plan.bat",
        "Setup-Gmail-Sermon-Import.bat",
        "Setup-Planning-Automation.bat",
        "Planning-Update-Sermon.bat",
        "Planning-Update-Sermon-Show.bat",
        "Planning-Update-Sermon-Dry-Run.bat",
        "Install-Lower-Third-Sermon-Sync-v15.bat",
        "Install-Lower-Third-Sermon-Sync-v15.ps1",
        "Restore-Pre-v15-Control-Panel.bat",
        "Restore-Pre-v15-Control-Panel.ps1",
        "README_SETUP.txt",
        "README_V17_PLANNING.txt",
        "README_V16_OBS_AUTOSTART.txt",
        "VOLUNTEER_SUNDAY_GUIDE.txt",
        "install_desktop_shortcut.ps1",
        "StreamDeck_EMERGENCY_MUTE.bat",
        "StreamDeck_MANUAL_CHAPTER.bat",
        "StreamDeck_START_RECORDING.bat",
        "StreamDeck_START_STREAM.bat",
        "StreamDeck_STOP_RECORDING.bat",
        "StreamDeck_STOP_STREAM.bat"
    )

    if ($protectedExact -contains $rel) {
        return $true
    }

    $protectedPrefixes = @(
        "venv\",
        "WorshipTools_Planning_Profile\",
        "Cleanup_Archive\",
        "Plugin_Backups\"
    )

    foreach ($prefix in $protectedPrefixes) {
        if ($rel.StartsWith($prefix, [System.StringComparison]::OrdinalIgnoreCase)) {
            return $true
        }
    }

    return $false
}

function Add-Candidate {
    param(
        [System.Collections.ArrayList]$List,
        [string]$Path,
        [string]$Reason,
        [string]$Category
    )

    if (-not (Test-Path -LiteralPath $Path)) {
        return
    }

    $item = Get-Item -LiteralPath $Path -Force

    $relative = Normalize-RelativePath $item.FullName

    if (Is-ProtectedPath $relative) {
        return
    }

    foreach ($existing in $List) {
        if ($existing.FullPath -ieq $item.FullName) {
            return
        }
    }

    [void]$List.Add([PSCustomObject]@{
        FullPath = $item.FullName
        RelativePath = $relative
        Reason = $Reason
        Category = $Category
        IsDirectory = $item.PSIsContainer
        LastWriteTime = $item.LastWriteTime
        SizeBytes = if ($item.PSIsContainer) { 0 } else { $item.Length }
    })
}

function Get-CleanupCandidates {
    $items = New-Object System.Collections.ArrayList

    # ------------------------------------------------------------
    # 1. Known obsolete SermonAI generations
    # ------------------------------------------------------------
    $legacyExact = @(
        "Install-Lower-Third-Sermon-Loader.bat",
        "install_sermon_plan_loader.py",
        "sermon_plan_loader.js",
        "sermon_plan_server.py",
        "README_V8_SERMON_EMAIL.txt",
        "README_V11.txt",
        "README_V12.txt",
        "README_V13.txt",
        "README_V14.txt",
        "README_V15.txt",
        "Restore-Pre-v12-Control-Panel.bat",
        "Restore-Pre-v12-Control-Panel.ps1",
        "control-panel-v10-template.html",
        "control-panel-v11-template.html",
        "control-panel-v12-template.html",
        "control-panel-v13-template.html",
        "control-panel-v14-template.html",
        "sermon-plan-data.js"
    )

    foreach ($name in $legacyExact) {
        Add-Candidate `
            -List $items `
            -Path (Join-Path $Base $name) `
            -Reason "Obsolete pre-v17 component or documentation" `
            -Category "Legacy SermonAI"
    }

    # ------------------------------------------------------------
    # 2. Planning diagnostics used only to build/test the updater
    # ------------------------------------------------------------
    $diagnosticExact = @(
        "planning_diagnostic.py",
        "planning_edit_diagnostic.py",
        "planning_service_discovery.py",
        "Planning-Diagnostic.bat",
        "Planning-Edit-Diagnostic.bat",
        "Planning-Service-Discovery.bat",
        "Setup-Planning-Diagnostic.bat",
        "Planning_Diagnostic.txt",
        "Planning_Diagnostic.png",
        "Planning_Edit_Diagnostic.txt",
        "Planning_Edit_Diagnostic.png",
        "Planning_Service_Discovery.txt",
        "Planning_Service_Discovery.png",
        "Planning_Service_Discovery_Error.txt"
    )

    foreach ($name in $diagnosticExact) {
        Add-Candidate `
            -List $items `
            -Path (Join-Path $Base $name) `
            -Reason "Development diagnostic no longer required by production SSS" `
            -Category "Diagnostics"
    }

    # ------------------------------------------------------------
    # 3. Old package ZIP files copied into SermonAI
    # ------------------------------------------------------------
    $zipPatterns = @(
        "Sunday_Mode_*.zip",
        "SundayMode_*.zip",
        "WorshipTools_Planning_Diagnostic*.zip",
        "WorshipTools_Planning_Edit_Diagnostic*.zip",
        "WorshipTools_Planning_Service_Discovery*.zip",
        "Lower_Third_Sermon_Plan_Inline*.zip",
        "OBS_Browser_Cache_Refresh*.zip",
        "Restore_Lower_Third_Control_Panel*.zip"
    )

    foreach ($pattern in $zipPatterns) {
        Get-ChildItem -LiteralPath $Base -File -Filter $pattern -ErrorAction SilentlyContinue |
            ForEach-Object {
                Add-Candidate `
                    -List $items `
                    -Path $_.FullName `
                    -Reason "Old installation/download package" `
                    -Category "Old packages"
            }
    }

    # ------------------------------------------------------------
    # 4. Temporary Python/cache files
    # ------------------------------------------------------------
    Get-ChildItem -LiteralPath $Base -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue |
        ForEach-Object {
            Add-Candidate `
                -List $items `
                -Path $_.FullName `
                -Reason "Python cache; recreated automatically" `
                -Category "Cache"
        }

    Get-ChildItem -LiteralPath $Base -File -ErrorAction SilentlyContinue |
        Where-Object {
            $_.Name -match '\.(tmp|temp)$' -or
            $_.Name -match '~$'
        } |
        ForEach-Object {
            Add-Candidate `
                -List $items `
                -Path $_.FullName `
                -Reason "Temporary file" `
                -Category "Temporary"
        }

    # ------------------------------------------------------------
    # 5. Old LowerThird backups.
    # Keep newest 5 in LowerThird_Backups; archive the rest.
    # ------------------------------------------------------------
    $ltBackupDir = Join-Path $Base "LowerThird_Backups"

    if (Test-Path -LiteralPath $ltBackupDir) {
        $backups = @(
            Get-ChildItem -LiteralPath $ltBackupDir -File -ErrorAction SilentlyContinue |
                Sort-Object LastWriteTime -Descending
        )

        if ($backups.Count -gt 5) {
            $oldBackups = $backups | Select-Object -Skip 5

            foreach ($backup in $oldBackups) {
                Add-Candidate `
                    -List $items `
                    -Path $backup.FullName `
                    -Reason "Older LowerThird backup; newest 5 are retained" `
                    -Category "Old backups"
            }
        }
    }

    # ------------------------------------------------------------
    # 6. Very old one-off diagnostics / debug text by naming pattern
    #    Only files older than 14 days, and never active logs/status.
    # ------------------------------------------------------------
    $cutoff = (Get-Date).AddDays(-14)

    Get-ChildItem -LiteralPath $Base -File -ErrorAction SilentlyContinue |
        Where-Object {
            $_.LastWriteTime -lt $cutoff -and
            (
                $_.Name -match '(?i)debug.*\.(txt|log)$' -or
                $_.Name -match '(?i)diagnostic.*\.(txt|log|png)$' -or
                $_.Name -match '(?i)test.*\.(txt|log|png)$'
            )
        } |
        ForEach-Object {
            Add-Candidate `
                -List $items `
                -Path $_.FullName `
                -Reason "Old diagnostic/test output (14+ days)" `
                -Category "Old diagnostic output"
        }

    return @(
        $items |
            Sort-Object Category, RelativePath
    )
}

function Format-Size {
    param([long]$Bytes)

    if ($Bytes -ge 1GB) {
        return ("{0:N2} GB" -f ($Bytes / 1GB))
    }

    if ($Bytes -ge 1MB) {
        return ("{0:N2} MB" -f ($Bytes / 1MB))
    }

    if ($Bytes -ge 1KB) {
        return ("{0:N1} KB" -f ($Bytes / 1KB))
    }

    return "$Bytes B"
}

function Undo-LastCleanup {
    Write-Header "SERMON AI CLEANUP - UNDO LAST CLEANUP"

    if (-not (Test-Path -LiteralPath $ManifestRoot)) {
        Write-Host "No cleanup manifests were found."
        return
    }

    $manifest = Get-ChildItem -LiteralPath $ManifestRoot -Filter "*.json" -File |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1

    if (-not $manifest) {
        Write-Host "No cleanup manifests were found."
        return
    }

    $data = Get-Content -LiteralPath $manifest.FullName -Raw | ConvertFrom-Json

    Write-Host "Restoring cleanup:"
    Write-Host "  $($data.ArchiveFolder)"
    Write-Host ""

    $restored = 0
    $skipped = 0

    foreach ($entry in $data.Items) {
        $archivedPath = Join-Path $data.ArchiveFolder $entry.RelativePath
        $originalPath = Join-Path $Base $entry.RelativePath

        if (-not (Test-Path -LiteralPath $archivedPath)) {
            Write-Host "SKIP (archive missing): $($entry.RelativePath)" -ForegroundColor Yellow
            $skipped++
            continue
        }

        if (Test-Path -LiteralPath $originalPath) {
            Write-Host "SKIP (already exists): $($entry.RelativePath)" -ForegroundColor Yellow
            $skipped++
            continue
        }

        $parent = Split-Path -Parent $originalPath

        if ($parent) {
            New-Item -ItemType Directory -Path $parent -Force | Out-Null
        }

        Move-Item -LiteralPath $archivedPath -Destination $originalPath -Force

        Write-Host "RESTORED: $($entry.RelativePath)" -ForegroundColor Green
        $restored++
    }

    Write-Host ""
    Write-Host "Restored: $restored"
    Write-Host "Skipped:  $skipped"
    Write-Host ""
    Write-Host "The archive manifest was left in place for reference."
}

if (-not (Test-Path -LiteralPath $Base)) {
    Write-Host "SermonAI folder was not found:"
    Write-Host "  $Base"
    exit 1
}

if ($UndoLast) {
    Undo-LastCleanup
    exit 0
}

Write-Header "SERMON AI CLEANUP"

$candidates = @(Get-CleanupCandidates)

if ($candidates.Count -eq 0) {
    Write-Host "Nothing matched the safe cleanup rules."
    Write-Host ""
    Write-Host "No files were changed."
    exit 0
}

$totalBytes = (
    $candidates |
        Measure-Object -Property SizeBytes -Sum
).Sum

if (-not $totalBytes) {
    $totalBytes = 0
}

$grouped = $candidates | Group-Object Category

foreach ($group in $grouped) {
    Write-Host "[$($group.Name)]" -ForegroundColor Cyan

    foreach ($item in $group.Group) {
        $sizeText = if ($item.IsDirectory) {
            "<folder>"
        } else {
            Format-Size $item.SizeBytes
        }

        Write-Host ("  {0,-62} {1,10}" -f $item.RelativePath, $sizeText)
        Write-Host ("      -> " + $item.Reason) -ForegroundColor DarkGray
    }

    Write-Host ""
}

Write-Host "Candidates: $($candidates.Count)"
Write-Host "Known file size: $(Format-Size $totalBytes)"
Write-Host ""

if (-not $Apply) {
    Write-Host "PREVIEW ONLY - nothing was changed." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Run Run-SermonAI-Cleanup.bat to archive these files."
    Write-Host ""
    Write-Host "Cleanup does NOT touch:"
    Write-Host "  venv"
    Write-Host "  .env"
    Write-Host "  Gmail credentials/token"
    Write-Host "  WorshipTools Planning login profile"
    Write-Host "  sermon_plan.json"
    Write-Host "  current v17 production scripts"
    Write-Host "  Plugin_Backups"
    Write-Host "  newest 5 LowerThird backups"
    exit 0
}

$stamp = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
$archive = Join-Path $ArchiveRoot $stamp

New-Item -ItemType Directory -Path $archive -Force | Out-Null
New-Item -ItemType Directory -Path $ManifestRoot -Force | Out-Null

$manifestItems = @()

foreach ($item in $candidates) {
    # Re-check right before moving.
    if (Is-ProtectedPath $item.RelativePath) {
        Write-Host "PROTECTED - skipped: $($item.RelativePath)" -ForegroundColor Yellow
        continue
    }

    if (-not (Test-Path -LiteralPath $item.FullPath)) {
        continue
    }

    $destination = Join-Path $archive $item.RelativePath
    $destParent = Split-Path -Parent $destination

    if ($destParent) {
        New-Item -ItemType Directory -Path $destParent -Force | Out-Null
    }

    Move-Item -LiteralPath $item.FullPath -Destination $destination -Force

    Write-Host "ARCHIVED: $($item.RelativePath)" -ForegroundColor Green

    $manifestItems += [PSCustomObject]@{
        RelativePath = $item.RelativePath
        Reason = $item.Reason
        Category = $item.Category
        WasDirectory = $item.IsDirectory
    }
}

$manifest = [PSCustomObject]@{
    CleanupVersion = "1.0"
    Created = (Get-Date).ToString("o")
    BaseFolder = $Base
    ArchiveFolder = $archive
    Items = $manifestItems
}

$manifestPath = Join-Path $ManifestRoot ("cleanup_" + $stamp + ".json")
$manifest | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $manifestPath -Encoding UTF8

Write-Host ""
Write-Host ("=" * 72)
Write-Host " CLEANUP COMPLETE"
Write-Host ("=" * 72)
Write-Host ""
Write-Host "Nothing was permanently deleted."
Write-Host ""
Write-Host "Archived to:"
Write-Host "  $archive"
Write-Host ""
Write-Host "Manifest:"
Write-Host "  $manifestPath"
Write-Host ""
Write-Host "If anything is unexpectedly missing, run:"
Write-Host "  Undo-Last-SermonAI-Cleanup.bat"
Write-Host ""
