$ErrorActionPreference = 'Stop'
$taskExecutable = Join-Path $PSScriptRoot 'Local Voice Studio.exe'
if (-not (Test-Path -LiteralPath $taskExecutable)) { throw 'Keep this script beside Local Voice Studio.exe.' }
$taskDesktop = [Environment]::GetFolderPath('Desktop')
$taskShell = New-Object -ComObject WScript.Shell
$taskShortcut = $taskShell.CreateShortcut((Join-Path $taskDesktop 'Local Voice Studio.lnk'))
$taskShortcut.TargetPath = $taskExecutable
$taskShortcut.WorkingDirectory = $PSScriptRoot
$taskShortcut.Description = 'Private local voice cloning with Chatterbox Turbo and Qwen'
$taskShortcut.Save()
Write-Host 'Desktop shortcut created. Run this again if you move the app folder.'
