$ErrorActionPreference = 'Stop'

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$VenvDir = Join-Path $ProjectRoot '.venv'
$VenvPython = Join-Path $VenvDir 'Scripts\python.exe'
$BuildDir = Join-Path $ProjectRoot 'build\pyinstaller'
$WorkDir = Join-Path $BuildDir 'work'
$DistDir = Join-Path $ProjectRoot 'dist'
$PackageDir = Join-Path $DistDir 'HEICConverter'
$ZipPath = Join-Path $DistDir 'HEICConverter.zip'
$LicenseOutputDir = Join-Path $PackageDir 'licenses'
$LegalTemplateDir = Join-Path $ProjectRoot 'licenses'
$EntryPoint = Join-Path $ProjectRoot 'heictojpg\app_main.py'

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

function Assert-PathInside {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ChildPath,
        [Parameter(Mandatory = $true)]
        [string]$ParentPath
    )

    $ParentFullPath = [System.IO.Path]::GetFullPath($ParentPath)
    $ChildFullPath = [System.IO.Path]::GetFullPath($ChildPath)
    $Comparison = [System.StringComparison]::OrdinalIgnoreCase
    $ParentWithSeparator = $ParentFullPath.TrimEnd([System.IO.Path]::DirectorySeparatorChar, [System.IO.Path]::AltDirectorySeparatorChar) + [System.IO.Path]::DirectorySeparatorChar
    if (-not $ChildFullPath.StartsWith($ParentWithSeparator, $Comparison)) {
        throw "Refusing to remove or write outside expected folder: $ChildFullPath"
    }
}

function Remove-DirectoryInside {
    param(
        [Parameter(Mandatory = $true)]
        [string]$TargetPath,
        [Parameter(Mandatory = $true)]
        [string]$ParentPath
    )

    Assert-PathInside -ChildPath $TargetPath -ParentPath $ParentPath
    if (Test-Path -LiteralPath $TargetPath) {
        Remove-Item -LiteralPath $TargetPath -Recurse -Force
    }
}

function Remove-FileInside {
    param(
        [Parameter(Mandatory = $true)]
        [string]$TargetPath,
        [Parameter(Mandatory = $true)]
        [string]$ParentPath
    )

    Assert-PathInside -ChildPath $TargetPath -ParentPath $ParentPath
    if (Test-Path -LiteralPath $TargetPath) {
        Remove-Item -LiteralPath $TargetPath -Force
    }
}

function Copy-RequiredFile {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Source,
        [Parameter(Mandatory = $true)]
        [string]$Destination
    )

    if (-not (Test-Path -LiteralPath $Source -PathType Leaf)) {
        throw "Required license/source file was not found: $Source"
    }
    $DestinationDir = Split-Path -Parent $Destination
    New-Item -ItemType Directory -Force -Path $DestinationDir | Out-Null
    Copy-Item -LiteralPath $Source -Destination $Destination -Force
}

function Get-DistInfoDirectory {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Pattern
    )

    $SitePackages = Join-Path $VenvDir 'Lib\site-packages'
    $Matches = @(Get-ChildItem -LiteralPath $SitePackages -Directory -Filter $Pattern | Sort-Object -Property Name -Descending)
    if ($Matches.Count -eq 0) {
        throw "Could not find installed package metadata matching: $Pattern"
    }
    return $Matches[0].FullName
}

function Invoke-PythonScalar {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Code
    )

    $Output = & $VenvPython -c $Code
    if ($LASTEXITCODE -ne 0) {
        throw "Python metadata command failed: $Code"
    }
    return ($Output | Select-Object -First 1).Trim()
}

function Copy-DistributionLicenses {
    $PillowInfo = Get-DistInfoDirectory -Pattern 'pillow-*.dist-info'
    $PillowHeifInfo = Get-DistInfoDirectory -Pattern 'pillow_heif-*.dist-info'
    $TkinterDndInfo = Get-DistInfoDirectory -Pattern 'tkinterdnd2-*.dist-info'
    $PyInstallerInfo = Get-DistInfoDirectory -Pattern 'pyinstaller-*.dist-info'
    $PythonBase = Invoke-PythonScalar -Code 'import sys; print(sys.base_prefix)'

    Copy-RequiredFile -Source (Join-Path $ProjectRoot 'LICENSE') -Destination (Join-Path $PackageDir 'LICENSE.txt')
    Copy-RequiredFile -Source (Join-Path $LegalTemplateDir 'THIRD_PARTY_NOTICES.txt') -Destination (Join-Path $PackageDir 'THIRD_PARTY_NOTICES.txt')
    Copy-RequiredFile -Source (Join-Path $LegalTemplateDir 'SOURCE_OFFER.txt') -Destination (Join-Path $PackageDir 'SOURCE_OFFER.txt')

    Copy-RequiredFile -Source (Join-Path $ProjectRoot 'LICENSE') -Destination (Join-Path $LicenseOutputDir 'HEICConverter-MIT-LICENSE.txt')
    Copy-RequiredFile -Source (Join-Path $PillowInfo 'licenses\LICENSE') -Destination (Join-Path $LicenseOutputDir 'Pillow-LICENSE.txt')
    Copy-RequiredFile -Source (Join-Path $PillowHeifInfo 'licenses\LICENSE.txt') -Destination (Join-Path $LicenseOutputDir 'pillow-heif-LICENSE.txt')
    Copy-RequiredFile -Source (Join-Path $PillowHeifInfo 'licenses\LICENSES_bundled.txt') -Destination (Join-Path $LicenseOutputDir 'pillow-heif-LICENSES_bundled.txt')
    Copy-RequiredFile -Source (Join-Path $TkinterDndInfo 'licenses\LICENSE') -Destination (Join-Path $LicenseOutputDir 'tkinterdnd2-LICENSE.txt')
    Copy-RequiredFile -Source (Join-Path $PyInstallerInfo 'licenses\COPYING.txt') -Destination (Join-Path $LicenseOutputDir 'PyInstaller-COPYING.txt')
    Copy-RequiredFile -Source (Join-Path $PythonBase 'LICENSE.txt') -Destination (Join-Path $LicenseOutputDir 'Python-LICENSE.txt')
    Copy-RequiredFile -Source (Join-Path $PythonBase 'tcl\tk8.6\license.terms') -Destination (Join-Path $LicenseOutputDir 'Tk-license.terms')
}

function Compress-DistributionPackage {
    Remove-FileInside -TargetPath $ZipPath -ParentPath $DistDir
    Push-Location -LiteralPath $DistDir
    try {
        Compress-Archive -LiteralPath 'HEICConverter' -DestinationPath $ZipPath -Force
    }
    finally {
        Pop-Location
    }
}

if (-not (Test-Path -LiteralPath $VenvPython -PathType Leaf)) {
    $PythonCommands = @(Get-Command python -CommandType Application -ErrorAction Stop)
    if ($PythonCommands.Count -eq 0) {
        throw "Could not find the python executable."
    }
    $PythonCommand = $PythonCommands[0]
    $PythonPath = [string]$PythonCommand.Path
    if (-not $PythonPath) {
        $PythonPath = [string]$PythonCommand.Source
    }
    if (-not $PythonPath) {
        throw "Could not resolve the python executable path."
    }
    Invoke-NativeCommand -FilePath $PythonPath -Arguments @('-m', 'venv', $VenvDir)
}

Invoke-NativeCommand -FilePath $VenvPython -Arguments @('-m', 'pip', 'install', '--upgrade', 'pip')
Invoke-NativeCommand -FilePath $VenvPython -Arguments @('-m', 'pip', 'install', '--upgrade', '-e', "$ProjectRoot[dev]")

New-Item -ItemType Directory -Force -Path $DistDir | Out-Null
Remove-DirectoryInside -TargetPath $PackageDir -ParentPath $DistDir
Remove-FileInside -TargetPath $ZipPath -ParentPath $DistDir
New-Item -ItemType Directory -Force -Path $PackageDir | Out-Null

Invoke-NativeCommand -FilePath $VenvPython -Arguments @(
    '-m',
    'PyInstaller',
    '--noconfirm',
    '--clean',
    '--onefile',
    '--windowed',
    '--name',
    'HEICConverter',
    '--specpath',
    $BuildDir,
    '--workpath',
    $WorkDir,
    '--distpath',
    $PackageDir,
    '--collect-data',
    'tkinterdnd2',
    $EntryPoint
)

Copy-DistributionLicenses

$ExePath = Join-Path $PackageDir 'HEICConverter.exe'
foreach ($RequiredFile in @(
    $ExePath,
    (Join-Path $PackageDir 'LICENSE.txt'),
    (Join-Path $PackageDir 'THIRD_PARTY_NOTICES.txt'),
    (Join-Path $PackageDir 'SOURCE_OFFER.txt'),
    (Join-Path $LicenseOutputDir 'pillow-heif-LICENSES_bundled.txt'),
    (Join-Path $LicenseOutputDir 'PyInstaller-COPYING.txt')
)) {
    if (-not (Test-Path -LiteralPath $RequiredFile -PathType Leaf)) {
        throw "Distribution package is incomplete; missing: $RequiredFile"
    }
}

Compress-DistributionPackage
if (-not (Test-Path -LiteralPath $ZipPath -PathType Leaf)) {
    throw "Distribution zip was not created: $ZipPath"
}

Write-Host "Created EXE package: $PackageDir"
Write-Host "Created EXE package zip: $ZipPath"
Write-Host "Distribute HEICConverter.zip, not just HEICConverter.exe."
