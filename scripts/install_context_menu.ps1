param(
    [Parameter(Mandatory = $true)]
    [string]$PythonwPath
)

$ErrorActionPreference = 'Stop'

$ResolvedPythonw = (Resolve-Path -LiteralPath $PythonwPath).Path
if (-not (Test-Path -LiteralPath $ResolvedPythonw -PathType Leaf)) {
    throw "pythonw.exe was not found: $ResolvedPythonw"
}

$QuotedPythonw = '"' + $ResolvedPythonw + '"'
$ConvertCommand = $QuotedPythonw + ' -m heictojpg context-convert "%1"'
$SettingsCommand = $QuotedPythonw + ' -m heictojpg settings'
$Icon = "$env:SystemRoot\System32\imageres.dll,-70"
$SourceExtensions = @(
    '.apng',
    '.avif',
    '.bmp',
    '.dib',
    '.gif',
    '.heic',
    '.heif',
    '.hif',
    '.jfif',
    '.jpe',
    '.jpeg',
    '.jpg',
    '.png',
    '.tif',
    '.tiff',
    '.webp'
)

function Invoke-ShellAssociationChanged {
    if (-not ('HEICtoJPGShellNotify' -as [type])) {
        Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;

public static class HEICtoJPGShellNotify
{
    [DllImport("shell32.dll")]
    public static extern void SHChangeNotify(int wEventId, uint uFlags, IntPtr dwItem1, IntPtr dwItem2);
}
'@
    }

    [HEICtoJPGShellNotify]::SHChangeNotify(0x08000000, 0, [IntPtr]::Zero, [IntPtr]::Zero)
}

function Set-MenuCommand {
    param(
        [Parameter(Mandatory = $true)]
        [string]$KeyPath,
        [Parameter(Mandatory = $true)]
        [string]$MenuText,
        [Parameter(Mandatory = $true)]
        [string]$Command
    )

    $CommandKey = Join-Path $KeyPath 'command'
    New-Item -Path $KeyPath -Force | Out-Null
    New-ItemProperty -Path $KeyPath -Name 'MUIVerb' -Value $MenuText -PropertyType String -Force | Out-Null
    New-ItemProperty -Path $KeyPath -Name 'Icon' -Value $Icon -PropertyType String -Force | Out-Null
    New-ItemProperty -Path $KeyPath -Name 'MultiSelectModel' -Value 'Document' -PropertyType String -Force | Out-Null
    New-ItemProperty -Path $KeyPath -Name 'NoWorkingDirectory' -Value '' -PropertyType String -Force | Out-Null
    New-Item -Path $CommandKey -Force | Out-Null
    Set-Item -Path $CommandKey -Value $Command
}

foreach ($Extension in $SourceExtensions) {
    $BaseKey = "HKCU:\Software\Classes\SystemFileAssociations\$Extension\shell"
    Set-MenuCommand `
        -KeyPath (Join-Path $BaseKey 'HEICtoJPGConvert') `
        -MenuText 'Convert with HEIC Converter' `
        -Command $ConvertCommand
    Set-MenuCommand `
        -KeyPath (Join-Path $BaseKey 'HEICtoJPGSettings') `
        -MenuText 'HEIC Converter Settings' `
        -Command $SettingsCommand
}

Invoke-ShellAssociationChanged
Write-Host 'Installed HEIC Converter right-click menu for supported image files.'
