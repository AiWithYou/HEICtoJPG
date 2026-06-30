$ErrorActionPreference = 'Stop'

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$LocalAppData = $env:LOCALAPPDATA
if ([string]::IsNullOrWhiteSpace($LocalAppData)) {
    throw 'LOCALAPPDATA is not set; cannot choose an application install folder.'
}

$InstallRoot = Join-Path $LocalAppData 'Programs\HEICtoJPG'
$VenvDir = Join-Path $InstallRoot '.venv'
$VenvPython = Join-Path $VenvDir 'Scripts\python.exe'
$VenvPythonw = Join-Path $VenvDir 'Scripts\pythonw.exe'

function Invoke-NativeCommand {
    param(
        [Parameter(Mandatory = $true)]
        [string]$FilePath,
        [Parameter(Mandatory = $true)]
        [string[]]$Arguments
    )

    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed with exit code ${LASTEXITCODE}: $FilePath $($Arguments -join ' ')"
    }
}

$PythonCommand = Get-Command python -CommandType Application -ErrorAction Stop
$PythonExe = $PythonCommand.Source
Invoke-NativeCommand `
    -FilePath $PythonExe `
    -Arguments @('-c', 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)')

New-Item -ItemType Directory -Force -Path $InstallRoot | Out-Null

if (-not (Test-Path -LiteralPath $VenvPython -PathType Leaf)) {
    Invoke-NativeCommand -FilePath $PythonExe -Arguments @('-m', 'venv', $VenvDir)
}

Invoke-NativeCommand -FilePath $VenvPython -Arguments @('-m', 'pip', 'install', '--upgrade', 'pip')
Invoke-NativeCommand -FilePath $VenvPython -Arguments @('-m', 'pip', 'install', '--upgrade', '--force-reinstall', $ProjectRoot)
Invoke-NativeCommand -FilePath $VenvPython -Arguments @('-c', 'import heictojpg, pillow_heif')
& (Join-Path $PSScriptRoot 'install_context_menu.ps1') -PythonwPath $VenvPythonw

$Programs = [Environment]::GetFolderPath('Programs')
$OldShortcutPath = Join-Path $Programs 'HEIC to JPG Settings.lnk'
$ShortcutPath = Join-Path $Programs 'HEIC Converter Settings.lnk'
if (Test-Path -LiteralPath $OldShortcutPath -PathType Leaf) {
    Remove-Item -LiteralPath $OldShortcutPath -Force
}
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = $VenvPythonw
$Shortcut.Arguments = '-m heictojpg settings'
$Shortcut.WorkingDirectory = $ProjectRoot
$Shortcut.IconLocation = "$env:SystemRoot\System32\imageres.dll,-70"
$Shortcut.Save()

Write-Host "Created Start Menu shortcut: $ShortcutPath"
Write-Host "Installed runtime: $InstallRoot"
Write-Host 'HEIC Converter is ready on this PC.'
