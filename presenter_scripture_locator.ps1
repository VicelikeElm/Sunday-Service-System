param(
    [Parameter(Mandatory=$true)]
    [string]$Reference
)

$ErrorActionPreference = "Stop"

Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
Add-Type -AssemblyName System.Windows.Forms

function Normalize-Text([string]$Value) {
    if ($null -eq $Value) {
        return ""
    }

    $v = $Value.ToLowerInvariant()

    # ASCII-only source so Windows PowerShell 5.1 cannot misread this file.
    # These regex escapes normalize en dash, em dash, and minus sign.
    $v = [regex]::Replace(
        $v,
        "[\u2013\u2014\u2212]",
        "-"
    )

    $v = [regex]::Replace(
        $v,
        "\s+",
        " "
    )

    return $v.Trim()
}

function Get-ControlTypeName($Element) {
    try {
        return [string]$Element.Current.ControlType.ProgrammaticName
    }
    catch {
        return ""
    }
}

function Try-ActivateElement($Element) {
    $attempts = @()

    $walker = [System.Windows.Automation.TreeWalker]::ControlViewWalker
    $current = $Element

    for ($depth = 0; $depth -lt 7 -and $null -ne $current; $depth++) {
        $attempts += $current

        try {
            $current = $walker.GetParent($current)
        }
        catch {
            $current = $null
        }
    }

    foreach ($candidate in $attempts) {
        try {
            $pattern = $null
            $ok = $candidate.TryGetCurrentPattern(
                [System.Windows.Automation.SelectionItemPattern]::Pattern,
                [ref]$pattern
            )

            if ($ok) {
                $pattern.Select()
                Start-Sleep -Milliseconds 150

                return @{
                    success = $true
                    method = "SelectionItem"
                    name = [string]$candidate.Current.Name
                    control_type = Get-ControlTypeName $candidate
                }
            }
        }
        catch {}

        try {
            $pattern = $null
            $ok = $candidate.TryGetCurrentPattern(
                [System.Windows.Automation.InvokePattern]::Pattern,
                [ref]$pattern
            )

            if ($ok) {
                $pattern.Invoke()
                Start-Sleep -Milliseconds 150

                return @{
                    success = $true
                    method = "Invoke"
                    name = [string]$candidate.Current.Name
                    control_type = Get-ControlTypeName $candidate
                }
            }
        }
        catch {}

        try {
            if ($candidate.Current.IsKeyboardFocusable) {
                $candidate.SetFocus()
                Start-Sleep -Milliseconds 100
                [System.Windows.Forms.SendKeys]::SendWait("{ENTER}")
                Start-Sleep -Milliseconds 150

                return @{
                    success = $true
                    method = "Focus+Enter"
                    name = [string]$candidate.Current.Name
                    control_type = Get-ControlTypeName $candidate
                }
            }
        }
        catch {}
    }

    return @{
        success = $false
        method = ""
        name = ""
        control_type = ""
    }
}

try {
    $referenceNorm = Normalize-Text $Reference

    if ([string]::IsNullOrWhiteSpace($referenceNorm)) {
        throw "Scripture reference is blank."
    }

    $desktop = [System.Windows.Automation.AutomationElement]::RootElement

    $children = $desktop.FindAll(
        [System.Windows.Automation.TreeScope]::Children,
        [System.Windows.Automation.Condition]::TrueCondition
    )

    $presenterWindows = @()

    foreach ($child in $children) {
        try {
            $name = [string]$child.Current.Name
            $className = [string]$child.Current.ClassName

            $isPresenter = (
                $name.IndexOf(
                    "Presenter",
                    [System.StringComparison]::OrdinalIgnoreCase
                ) -ge 0
            )

            if (-not $isPresenter) {
                $isPresenter = (
                    $className.IndexOf(
                        "Presenter",
                        [System.StringComparison]::OrdinalIgnoreCase
                    ) -ge 0
                )
            }

            if ($isPresenter) {
                $presenterWindows += $child
            }
        }
        catch {}
    }

    if ($presenterWindows.Count -eq 0) {
        @{
            success = $false
            reason = "Presenter window was not found."
            reference = $Reference
        } | ConvertTo-Json -Compress

        exit 2
    }

    $best = $null
    $bestScore = -1
    $bestName = ""

    foreach ($window in $presenterWindows) {
        try {
            $elements = $window.FindAll(
                [System.Windows.Automation.TreeScope]::Descendants,
                [System.Windows.Automation.Condition]::TrueCondition
            )
        }
        catch {
            continue
        }

        foreach ($element in $elements) {
            try {
                $name = [string]$element.Current.Name

                if ([string]::IsNullOrWhiteSpace($name)) {
                    continue
                }

                $nameNorm = Normalize-Text $name
                $score = -1

                if ($nameNorm -eq $referenceNorm) {
                    $score = 1000
                }
                elseif (
                    $nameNorm.StartsWith($referenceNorm + " ") -or
                    $nameNorm.StartsWith($referenceNorm + "(")
                ) {
                    $score = 900
                }
                elseif ($nameNorm.Contains($referenceNorm)) {
                    $score = 700
                }

                if ($score -lt 0) {
                    continue
                }

                $typeName = Get-ControlTypeName $element

                if ($typeName -match "ListItem") {
                    $score += 80
                }
                elseif ($typeName -match "Button") {
                    $score += 60
                }
                elseif ($typeName -match "Text") {
                    $score += 10
                }

                try {
                    if (-not $element.Current.IsOffscreen) {
                        $score += 20
                    }
                }
                catch {}

                if ($score -gt $bestScore) {
                    $bestScore = $score
                    $best = $element
                    $bestName = $name
                }
            }
            catch {}
        }
    }

    if ($null -eq $best) {
        @{
            success = $false
            reason = "The Scripture item was not visible in Presenter."
            reference = $Reference
        } | ConvertTo-Json -Compress

        exit 3
    }

    $activated = Try-ActivateElement $best

    if (-not $activated.success) {
        @{
            success = $false
            reason = "Found the Scripture item but could not select it."
            reference = $Reference
            found_name = $bestName
        } | ConvertTo-Json -Compress

        exit 4
    }

    Start-Sleep -Milliseconds 250

    @{
        success = $true
        reference = $Reference
        found_name = $bestName
        method = $activated.method
        activated_name = $activated.name
        control_type = $activated.control_type
    } | ConvertTo-Json -Compress

    exit 0
}
catch {
    @{
        success = $false
        reason = [string]$_.Exception.Message
        reference = $Reference
    } | ConvertTo-Json -Compress

    exit 1
}
