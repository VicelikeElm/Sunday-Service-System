$Base = "C:\Church\SermonAI"
$Desktop = [Environment]::GetFolderPath("Desktop")
$ShortcutPath = Join-Path $Desktop "Sunday Mode.lnk"

$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = "wscript.exe"
$Shortcut.Arguments = "`"$Base\start_sunday_mode_hidden.vbs`""
$Shortcut.WorkingDirectory = $Base
$Shortcut.Description = "Church Sunday Mode dashboard"
$Shortcut.Save()

Write-Host ""
Write-Host "Created:"
Write-Host $ShortcutPath
Write-Host ""
Read-Host "Press Enter to close"
