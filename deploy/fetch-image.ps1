# Fetch the onec-training-mcp:latest image tar from Google Drive and
# load it into the local Docker daemon. Idempotent: if the image is
# already present locally, exits without re-downloading.
#
# Usage: .\fetch-image.ps1 [-TarPath <path>]
#   -TarPath defaults to .\onec-training-mcp.tar (next to this script)

param(
    [string]$TarPath = (Join-Path $PSScriptRoot 'onec-training-mcp.tar')
)

$ErrorActionPreference = 'Stop'
$GDriveFileId = '1Z6ZG5p80Fen_vqRvV6XnlAuvSLrjcfL4'
$ImageTag     = 'onec-training-mcp:latest'

$existing = docker image inspect $ImageTag 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "[fetch-image] $ImageTag already present locally — nothing to do."
    Write-Host "[fetch-image] To force a redownload, remove the image first:"
    Write-Host "[fetch-image]   docker rmi $ImageTag"
    exit 0
}

$gdown = Get-Command gdown -ErrorAction SilentlyContinue
if (-not $gdown) {
    Write-Host "[fetch-image] gdown not found; installing into the current Python env..."
    python -m pip install --user gdown
    # gdown installs to %APPDATA%\Python\Python3xx\Scripts which may not be on PATH
    $userScripts = Join-Path $env:APPDATA "Python\Scripts"
    if (Test-Path $userScripts) { $env:PATH = "$userScripts;$env:PATH" }
}

Write-Host "[fetch-image] Downloading image tar from Google Drive (~3.3 GB)..."
gdown $GDriveFileId -O $TarPath

Write-Host "[fetch-image] Loading into Docker..."
docker load -i $TarPath

Write-Host "[fetch-image] Removing tar..."
Remove-Item -Force $TarPath

Write-Host "[fetch-image] Done. Verify with: docker images $ImageTag"
