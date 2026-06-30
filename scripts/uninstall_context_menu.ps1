$ErrorActionPreference = 'Stop'
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

foreach ($Extension in $SourceExtensions) {
    $BaseKey = "HKCU:\Software\Classes\SystemFileAssociations\$Extension\shell"
    foreach ($Name in @('HEICtoJPGConvert', 'HEICtoJPGSettings')) {
        $KeyPath = Join-Path $BaseKey $Name
        $CommandKey = Join-Path $KeyPath 'command'
        if (Test-Path -LiteralPath $CommandKey) {
            Remove-Item -LiteralPath $CommandKey -Force
        }
        if (Test-Path -LiteralPath $KeyPath) {
            Remove-Item -LiteralPath $KeyPath -Force
        }
    }
}

$Programs = [Environment]::GetFolderPath('Programs')
foreach ($ShortcutName in @('HEIC Converter Settings.lnk', 'HEIC to JPG Settings.lnk')) {
    $ShortcutPath = Join-Path $Programs $ShortcutName
    if (Test-Path -LiteralPath $ShortcutPath -PathType Leaf) {
        Remove-Item -LiteralPath $ShortcutPath -Force
    }
}

Invoke-ShellAssociationChanged
Write-Host 'Removed HEIC Converter right-click menu and Start Menu shortcut.'
