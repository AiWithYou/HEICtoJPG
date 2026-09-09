param(
    [Parameter(Mandatory = $true)][string]$Python,
    [Parameter(Mandatory = $true)][string]$Exe,
    [Parameter(Mandatory = $true)][string]$ReportDir
)
$ErrorActionPreference = 'Stop'
# This script only creates/formats its own NEW virtual disk, never a physical disk.
$Work = Join-Path ([IO.Path]::GetTempPath()) ('heic-exfat-' + [guid]::NewGuid())
New-Item -ItemType Directory -Path $Work | Out-Null
$Vhd = Join-Path $Work 'test.vhd'
$ReportDir = [IO.Path]::GetFullPath($ReportDir)
New-Item -ItemType Directory -Force -Path $ReportDir | Out-Null
$Drive = @('Z', 'Y', 'X', 'W', 'V') | Where-Object {
    -not (Test-Path "${_}:\") -and -not (Get-PSDrive -Name $_ -ErrorAction SilentlyContinue)
} | Select-Object -First 1
if (-not $Drive) { throw 'No unused test drive letter is available.' }
if (Test-Path -LiteralPath $Vhd) { throw 'Refusing to reuse an existing disk image.' }

function Invoke-TestDiskpart([string]$Text, [string]$Name) {
    $Script = Join-Path $Work "$Name.txt"
    $Text | Set-Content -LiteralPath $Script -Encoding ascii
    & diskpart /s $Script | Tee-Object -FilePath (Join-Path $ReportDir "$Name.log")
    if ($LASTEXITCODE -ne 0) { throw "Diskpart failed: $Name" }
}

try {
    Invoke-TestDiskpart -Name 'create-exfat-vhd' -Text @"
create vdisk file="$Vhd" maximum=256 type=expandable
select vdisk file="$Vhd"
attach vdisk
create partition primary
format fs=exfat quick label=HEIC_TEST
assign letter=$Drive
"@
    $Image = Get-DiskImage -ImagePath $Vhd
    if (-not $Image.Attached) { throw 'The test VHD is not attached.' }
    $Disk = $Image | Get-Disk
    $Partition = Get-Partition -DriveLetter $Drive
    if ($Partition.DiskNumber -ne $Disk.Number) { throw 'Drive is not backed by the test VHD.' }
    $Volume = Get-Volume -DriveLetter $Drive
    if ($Volume.FileSystem -ne 'exFAT' -or $Volume.FileSystemLabel -ne 'HEIC_TEST') {
        throw 'The test volume is not the expected exFAT filesystem.'
    }
    $Volume | Select-Object DriveLetter, FileSystem, FileSystemLabel, Size |
        ConvertTo-Json | Set-Content (Join-Path $ReportDir 'volume.json')
    & $Python -m pytest tests/test_converter_safety.py -q -ra -k 'not symlink' `
        --basetemp "${Drive}:\pytest" --junitxml (Join-Path $ReportDir 'exfat-tests.xml')
    if ($LASTEXITCODE -ne 0) { throw 'exFAT safety regression tests failed.' }
    & $Python scripts/verify_release.py --exe $Exe --report-dir $ReportDir `
        --workspace-base "${Drive}:\"
    if ($LASTEXITCODE -ne 0) { throw 'exFAT GUI/EXE smoke tests failed.' }
}
finally {
    if (Test-Path -LiteralPath $Vhd) {
        Invoke-TestDiskpart -Name 'detach-exfat-vhd' -Text @"
select vdisk file="$Vhd"
detach vdisk
"@
        if ((Get-DiskImage -ImagePath $Vhd).Attached) { throw 'Test VHD did not detach.' }
    }
    Remove-Item -LiteralPath $Work -Recurse -Force
}
