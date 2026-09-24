[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$projectRoot = Split-Path -Parent $PSScriptRoot
$toolsDirectory = Join-Path $projectRoot ".tools"
$runtimeDirectory = Join-Path $toolsDirectory "python312"
$python = Join-Path $runtimeDirectory "python.exe"
$archive = Join-Path $toolsDirectory "python-3.12.10-embed-amd64.zip"
$getPip = Join-Path $toolsDirectory "get-pip.py"

if (-not [Environment]::Is64BitOperatingSystem) {
    throw "KAIRO bootstrap currently requires 64-bit Windows."
}

New-Item -ItemType Directory -Force -Path $toolsDirectory | Out-Null

if (-not (Test-Path $python)) {
    Invoke-WebRequest `
        -Uri "https://www.python.org/ftp/python/3.12.10/python-3.12.10-embed-amd64.zip" `
        -OutFile $archive
    Expand-Archive -LiteralPath $archive -DestinationPath $runtimeDirectory -Force

    $pathFile = Join-Path $runtimeDirectory "python312._pth"
    @(
        "python312.zip"
        "."
        "..\.."
        "import site"
    ) | Set-Content -Path $pathFile -Encoding ascii
}

if (-not (Test-Path $getPip)) {
    Invoke-WebRequest `
        -Uri "https://bootstrap.pypa.io/get-pip.py" `
        -OutFile $getPip
}

& $python $getPip --no-warn-script-location
& $python -m pip install --disable-pip-version-check -r (Join-Path $projectRoot "requirements.txt")

Write-Host "KAIRO runtime is ready."
Write-Host "Run: $python -m src validate"
