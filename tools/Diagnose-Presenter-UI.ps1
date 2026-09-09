$ErrorActionPreference = "Continue"

$Base = "C:\Church\SermonAI"
$Out = Join-Path $Base "presenter_ui_diagnostic.txt"

Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes

function Write-Line([string]$Text) {
    Add-Content -Path $Out -Value $Text -Encoding UTF8
}

if (Test-Path $Out) {
    Remove-Item $Out -Force -ErrorAction SilentlyContinue
}

Write-Line "PRESENTER UI DIAGNOSTIC"
Write-Line ("Generated: " + (Get-Date -Format "yyyy-MM-dd HH:mm:ss"))
Write-Line ("=" * 90)
Write-Line ""

Write-Line "PROCESS INFORMATION"
Write-Line ("-" * 90)

$processes = Get-CimInstance Win32_Process | Where-Object {
    $_.Name -match "(?i)Presenter"
}

if (-not $processes) {
    Write-Line "No Presenter process found."
}
else {
    foreach ($p in $processes) {
        Write-Line ("Name: " + $p.Name)
        Write-Line ("PID: " + $p.ProcessId)
        Write-Line ("Executable: " + $p.ExecutablePath)
        Write-Line ("CommandLine: " + $p.CommandLine)
        Write-Line ""
    }
}

Write-Line ""
Write-Line "TOP-LEVEL WINDOWS"
Write-Line ("-" * 90)

try {
    $desktop = [System.Windows.Automation.AutomationElement]::RootElement
    $children = $desktop.FindAll(
        [System.Windows.Automation.TreeScope]::Children,
        [System.Windows.Automation.Condition]::TrueCondition
    )

    $presenterWindows = @()

    foreach ($child in $children) {
        try {
            $name = [string]$child.Current.Name
            $class = [string]$child.Current.ClassName
            $pid = [int]$child.Current.ProcessId

            $isPresenterPid = $false
            foreach ($proc in $processes) {
                if ([int]$proc.ProcessId -eq $pid) {
                    $isPresenterPid = $true
                    break
                }
            }

            if (
                $isPresenterPid -or
                $name -match "(?i)Presenter" -or
                $class -match "(?i)Presenter"
            ) {
                $presenterWindows += $child
                Write-Line ("Window Name: " + $name)
                Write-Line ("Class: " + $class)
                Write-Line ("PID: " + $pid)
                Write-Line ("ControlType: " + $child.Current.ControlType.ProgrammaticName)
                Write-Line ("IsOffscreen: " + $child.Current.IsOffscreen)
                Write-Line ""
            }
        }
        catch {}
    }

    Write-Line ""
    Write-Line "UI AUTOMATION DESCENDANTS"
    Write-Line ("-" * 90)

    if ($presenterWindows.Count -eq 0) {
        Write-Line "No Presenter top-level UI Automation window found."
    }

    $index = 0

    foreach ($window in $presenterWindows) {
        try {
            $elements = $window.FindAll(
                [System.Windows.Automation.TreeScope]::Descendants,
                [System.Windows.Automation.Condition]::TrueCondition
            )
        }
        catch {
            Write-Line ("Could not enumerate descendants: " + $_.Exception.Message)
            continue
        }

        Write-Line ("Descendant count: " + $elements.Count)
        Write-Line ""

        foreach ($element in $elements) {
            $index++

            try {
                $name = [string]$element.Current.Name
                $type = [string]$element.Current.ControlType.ProgrammaticName
                $class = [string]$element.Current.ClassName
                $autoId = [string]$element.Current.AutomationId
                $off = [string]$element.Current.IsOffscreen
                $focus = [string]$element.Current.IsKeyboardFocusable

                # Write named elements plus useful interactive containers.
                if (
                    -not [string]::IsNullOrWhiteSpace($name) -or
                    $type -match "ListItem|Button|TreeItem|TabItem|Hyperlink|Edit|Pane"
                ) {
                    Write-Line (
                        ("{0:D4} | Name='{1}' | Type={2} | Class='{3}' | AutomationId='{4}' | Offscreen={5} | Focusable={6}" -f
                        $index,
                        $name,
                        $type,
                        $class,
                        $autoId,
                        $off,
                        $focus)
                    )
                }
            }
            catch {}
        }
    }
}
catch {
    Write-Line ("UI Automation diagnostic failed: " + $_.Exception.Message)
}

Write-Line ""
Write-Line ("=" * 90)
Write-Line "SEARCH CHECK"
Write-Line ("-" * 90)

try {
    $content = Get-Content -Path $Out -Raw -ErrorAction SilentlyContinue

    if ($content -match "(?i)Matthew\s+12:43-50") {
        Write-Line "FOUND Matthew 12:43-50 in Windows UI Automation."
    }
    elseif ($content -match "(?i)Ezra\s+3:4-13") {
        Write-Line "FOUND another visible Scripture item (Ezra 3:4-13), but not Matthew 12:43-50."
    }
    else {
        Write-Line "NO visible Scripture text was exposed through Windows UI Automation."
    }
}
catch {}

Write-Line ""
Write-Line "END OF DIAGNOSTIC"

Start-Process notepad.exe -ArgumentList $Out
