# Build the 1C-training-MCP image.
# Uses BuildKit named build contexts so we don't copy the 1.5 GB installer or
# the .dt dump into the local docker build context — they're bind-mounted
# only inside the relevant RUN steps.
#
# REQUIRED inputs (supply via -DistroDir / -DbDir or environment):
#   ONEC_DISTRO_DIR — directory holding setup-training-<ver>-x86_64.run
#   ONEC_DB_DIR     — directory holding 1Cv8_no_users.dt (or your own .dt dump)
#
# Usage:
#   $env:ONEC_DISTRO_DIR = "C:\path\to\1c\linux"
#   $env:ONEC_DB_DIR     = "C:\path\to\db-dir"
#   .\build.ps1
# or:
#   .\build.ps1 -DistroDir C:\path\to\1c\linux -DbDir C:\path\to\db-dir

[CmdletBinding()]
param(
    [string]$Tag       = "onec-training-mcp:latest",
    [string]$DistroDir = $env:ONEC_DISTRO_DIR,
    [string]$DbDir     = $env:ONEC_DB_DIR,
    [string]$OnecVer   = "8.3.27.2130",
    [string]$Python    = (Get-Command python -ErrorAction SilentlyContinue).Source
)

if (-not $DistroDir) { throw "Set -DistroDir or `$env:ONEC_DISTRO_DIR (directory with setup-training-*.run)" }
if (-not $DbDir)     { throw "Set -DbDir or `$env:ONEC_DB_DIR (directory with the .dt dump)" }
if (-not $Python)    { throw "Python not found on PATH; pass -Python <path-to-python.exe>" }

$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path

# Sanity checks
foreach ($p in @(
    (Join-Path $DistroDir "setup-training-$OnecVer-x86_64.run"),
    (Join-Path $DbDir     "1Cv8_no_users.dt"),
    (Join-Path $here      "payload\MCP_Toolkit_linux.epf"),
    (Join-Path $here      "payload\MCP_Toolkit_linux\Forms\Форма\Ext\Form\Module.bsl"),
    (Join-Path $here      "repack_form_module.py"),
    (Join-Path $here      "Dockerfile"),
    (Join-Path $here      "entrypoint.sh"),
    $Python
)) {
    if (-not (Test-Path -LiteralPath $p)) { throw "Missing required file: $p" }
}

# Repack the .epf with our headless-autostart form module before docker build.
Write-Host "Repacking MCP_Toolkit.epf with headless-autostart Module.bsl..." -ForegroundColor Cyan
& $Python (Join-Path $here "repack_form_module.py") `
    (Join-Path $here "payload\MCP_Toolkit_linux.epf") `
    "Форма" `
    (Join-Path $here "payload\MCP_Toolkit_linux\Forms\Форма\Ext\Form\Module.bsl") `
    (Join-Path $here "payload\MCP_Toolkit.epf")
if ($LASTEXITCODE -ne 0) { throw "repack_form_module.py failed (exit $LASTEXITCODE)" }

$env:DOCKER_BUILDKIT = "1"

Write-Host "Building $Tag ..." -ForegroundColor Cyan
Write-Host "  distro = $DistroDir"
Write-Host "  db     = $DbDir"
Write-Host "  ver    = $OnecVer"

# `--progress=plain` keeps the long install log visible for debugging.
docker build `
    --progress=plain `
    --tag $Tag `
    --build-arg "ONEC_VERSION=$OnecVer" `
    --build-context "distro=$DistroDir" `
    --build-context "db=$DbDir" `
    -f (Join-Path $here "Dockerfile") `
    $here

if ($LASTEXITCODE -ne 0) { throw "docker build failed (exit $LASTEXITCODE)" }
Write-Host "`nBuilt $Tag" -ForegroundColor Green
