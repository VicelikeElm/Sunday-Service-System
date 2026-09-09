param(
    [switch]$PreviewOnly
)

$ErrorActionPreference = "Stop"

$Base = "C:\Church\SermonAI"
$Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$ArchiveRoot = Join-Path $Base "SSS Archive\$Stamp"

Write-Host ""
Write-Host "================================================================"
Write-Host "SUNDAY SERVICE SYSTEM - SAFE WORKSPACE TRIM"
Write-Host "================================================================"
Write-Host ""
Write-Host "This trims DEVELOPMENT / BUILD clutter only."
Write-Host ""
Write-Host "It does NOT touch:"
Write-Host "  .env"
Write-Host "  sunday_config.json"
Write-Host "  sermon_plan.json"
Write-Host "  ptz_camera_config.json"
Write-Host "  gmail credentials/tokens"
Write-Host "  YouTube credentials/tokens"
Write-Host "  Windows Credential Manager"
Write-Host "  Profiles"
Write-Host "  recordings / SRT / shorts"
Write-Host "  OBS"
Write-Host "  Presenter"
Write-Host "  current dist / update-output / release-feed-output / installer-output"
Write-Host "  current runtime .py files"
Write-Host ""
Write-Host "Recording and Streaming are never started/stopped by this tool."
Write-Host ""

if (-not (Test-Path -LiteralPath $Base)) {
    throw "SSS folder not found: $Base"
}

$ProtectedExact = @(
    ".env",
    "sunday_config.json",
    "sermon_plan.json",
    "ptz_camera_config.json",
    "gmail_credentials.json",
    "gmail_token.json",
    "youtube_token.json",
    "youtube_oauth_token.json",
    "sss_signing_config.json",
    "active_profile.json"
)

$ProtectedFolders = @(
    "venv",
    "Profiles",
    "Diagnostics",
    "Event History",
    "Plugin_Backups",
    "dist",
    "update-output",
    "release-feed-output",
    "installer-output",
    "CUDA"
)

$DeleteFolders = @(
    "build",
    "installer-payload",
    ".sss-build-tools",
    "__pycache__"
)

$DeleteFilePatterns = @(
    "*.pyc",
    "*.pyo",
    "*.tmp",
    "*.download"
)

# Old development documentation is archived, not deleted.
$ArchivePatterns = @(
    "README_SSS_v*.txt"
)

# Old version-specific apply helpers are archived. Keep the current v3.1 helper.
$ArchiveExact = @(
    "Apply-Built-v3.0-Update.bat"
)

# Superseded troubleshooting/hotfix helpers. Current equivalents remain.
$ArchiveSuperseded = @(
    "Fix-SSS-Timestamp-URL.bat",
    "Fix-SSS-Timestamp-URL.ps1",
    "Repair-SSS-Development-Certificate-Trust.bat",
    "Repair-SSS-Development-Certificate-Trust.ps1",
    "Check-SSS-Built-EXE-Signature.bat",
    "Check-SSS-Built-EXE-Signature.ps1"
)

function Is-ProtectedName {
    param([string]$Name)

    foreach ($protected in $ProtectedExact) {
        if ($Name.Equals($protected, [System.StringComparison]::OrdinalIgnoreCase)) {
            return $true
        }
    }

    return $false
}

function Ensure-ArchiveFolder {
    if (-not $PreviewOnly) {
        New-Item -ItemType Directory -Path $ArchiveRoot -Force | Out-Null
    }
}

function Archive-File {
    param(
        [System.IO.FileInfo]$File,
        [string]$Category
    )

    if (-not $File -or -not $File.Exists) {
        return
    }

    if (Is-ProtectedName $File.Name) {
        Write-Host ("[KEEP] Protected: {0}" -f $File.FullName)
        return
    }

    $destinationDir = Join-Path $ArchiveRoot $Category
    $destination = Join-Path $destinationDir $File.Name

    if ($PreviewOnly) {
        Write-Host ("[ARCHIVE] {0}" -f $File.FullName)
        return
    }

    New-Item -ItemType Directory -Path $destinationDir -Force | Out-Null

    # Avoid collisions.
    if (Test-Path -LiteralPath $destination) {
        $stem = [System.IO.Path]::GetFileNameWithoutExtension($File.Name)
        $ext = $File.Extension
        $destination = Join-Path $destinationDir ("{0}_{1}{2}" -f $stem, $Stamp, $ext)
    }

    Move-Item -LiteralPath $File.FullName -Destination $destination
    Write-Host ("[ARCHIVED] {0}" -f $File.Name)
}

function Remove-RebuildableFolder {
    param([string]$Name)

    if ($ProtectedFolders -contains $Name) {
        Write-Host ("[KEEP] Protected folder: {0}" -f $Name)
        return
    }

    $path = Join-Path $Base $Name

    if (-not (Test-Path -LiteralPath $path)) {
        return
    }

    if ($PreviewOnly) {
        Write-Host ("[DELETE REBUILDABLE] {0}" -f $path)
        return
    }

    Remove-Item -LiteralPath $path -Recurse -Force
    Write-Host ("[DELETED REBUILDABLE] {0}" -f $Name)
}

Write-Host "Planned cleanup:"
Write-Host ""

# Rebuildable build/cache folders.
foreach ($folder in $DeleteFolders) {
    Remove-RebuildableFolder $folder
}

# Nested __pycache__ folders outside protected heavyweight trees.
Get-ChildItem -LiteralPath $Base -Directory -Recurse -Force -ErrorAction SilentlyContinue |
    Where-Object {
        $_.Name -eq "__pycache__" -and
        $_.FullName -notlike "$Base\venv\*" -and
        $_.FullName -notlike "$Base\dist\*" -and
        $_.FullName -notlike "$Base\SSS Archive\*"
    } |
    ForEach-Object {
        if ($PreviewOnly) {
            Write-Host ("[DELETE REBUILDABLE] {0}" -f $_.FullName)
        }
        else {
            Remove-Item -LiteralPath $_.FullName -Recurse -Force -ErrorAction SilentlyContinue
            Write-Host ("[DELETED REBUILDABLE] {0}" -f $_.FullName)
        }
    }

# Loose temp/compiler files only at top level and known build-output temp areas.
foreach ($pattern in $DeleteFilePatterns) {
    Get-ChildItem -LiteralPath $Base -File -Filter $pattern -Force -ErrorAction SilentlyContinue |
        ForEach-Object {
            if (-not (Is-ProtectedName $_.Name)) {
                if ($PreviewOnly) {
                    Write-Host ("[DELETE REBUILDABLE] {0}" -f $_.FullName)
                }
                else {
                    Remove-Item -LiteralPath $_.FullName -Force -ErrorAction SilentlyContinue
                    Write-Host ("[DELETED REBUILDABLE] {0}" -f $_.Name)
                }
            }
        }
}

# Archive version-history README files.
foreach ($pattern in $ArchivePatterns) {
    Get-ChildItem -LiteralPath $Base -File -Filter $pattern -Force -ErrorAction SilentlyContinue |
        Sort-Object Name |
        ForEach-Object {
            Archive-File -File $_ -Category "Old Version Documentation"
        }
}

# Archive explicitly superseded helpers.
foreach ($name in ($ArchiveExact + $ArchiveSuperseded)) {
    $path = Join-Path $Base $name

    if (Test-Path -LiteralPath $path) {
        Archive-File -File (Get-Item -LiteralPath $path) -Category "Superseded Helpers"
    }
}

# Remove abandoned temporary signing work folders under update-output only.
$UpdateOutput = Join-Path $Base "update-output"

if (Test-Path -LiteralPath $UpdateOutput) {
    Get-ChildItem -LiteralPath $UpdateOutput -Directory -Filter ".signing_*" -ErrorAction SilentlyContinue |
        ForEach-Object {
            if ($PreviewOnly) {
                Write-Host ("[DELETE REBUILDABLE] {0}" -f $_.FullName)
            }
            else {
                Remove-Item -LiteralPath $_.FullName -Recurse -Force
                Write-Host ("[DELETED REBUILDABLE] {0}" -f $_.Name)
            }
        }

    Get-ChildItem -LiteralPath $UpdateOutput -File -Filter "*.download" -ErrorAction SilentlyContinue |
        ForEach-Object {
            if ($PreviewOnly) {
                Write-Host ("[DELETE REBUILDABLE] {0}" -f $_.FullName)
            }
            else {
                Remove-Item -LiteralPath $_.FullName -Force
                Write-Host ("[DELETED REBUILDABLE] {0}" -f $_.Name)
            }
        }
}

Write-Host ""
Write-Host "Protected current release outputs:"
foreach ($folder in @("dist","update-output","release-feed-output","installer-output")) {
    $path = Join-Path $Base $folder
    if (Test-Path -LiteralPath $path) {
        Write-Host ("  [KEEP] {0}" -f $path)
    }
}

Write-Host ""

if ($PreviewOnly) {
    Write-Host "================================================================"
    Write-Host "PREVIEW COMPLETE - NOTHING WAS CHANGED"
    Write-Host "================================================================"
    Write-Host ""
    Write-Host "Run Trim-SSS-Workspace.bat to perform this cleanup."
}
else {
    Write-Host "================================================================"
    Write-Host "[READY] SSS WORKSPACE TRIM COMPLETE"
    Write-Host "================================================================"
    Write-Host ""
    if (Test-Path -LiteralPath $ArchiveRoot) {
        Write-Host "Archived old documentation/helpers to:"
        Write-Host "  $ArchiveRoot"
        Write-Host ""
    }
    Write-Host "Current runtime, configs, profiles, secrets, and release outputs were kept."
    Write-Host ""
    Write-Host "If you build another Windows release later, the build script will recreate"
    Write-Host "the deleted build / installer-payload / .sss-build-tools folders."
    Write-Host ""
}
