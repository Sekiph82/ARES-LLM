$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$ExePath = Join-Path $RepoRoot "dist\Ares.exe"
$IconPath = Join-Path $RepoRoot "assets\ares_desktop.ico"
$ShortcutPath = Join-Path ([Environment]::GetFolderPath("Desktop")) "Ares.lnk"

if (-not (Test-Path $ExePath)) {
    throw "Ares.exe was not found at $ExePath"
}

$Shell = New-Object -ComObject WScript.Shell
$Shortcut = $Shell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = $ExePath
$Shortcut.WorkingDirectory = $RepoRoot
$Shortcut.IconLocation = "$IconPath,0"
$Shortcut.Description = "Ares local LLM coding agent"
$Shortcut.Save()

Write-Host "Created desktop shortcut at $ShortcutPath"
