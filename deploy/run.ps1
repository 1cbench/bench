# Launch the 1C-training-MCP container with port 6003 exposed for MCP clients.
# The container ships its own Xvfb and clicks "Подключиться" itself, so no host
# X server is required.

[CmdletBinding()]
param(
    [string]$Tag     = "onec-training-mcp:latest",
    [string]$Name    = "onec-mcp",
    [int]   $McpPort = 6003,
    [int]   $VncPort = 5900,
    # Bind-mount the project root so the dockerized 1C can open the patched
    # .epf files the bench produces. The container target must match the
    # BENCH_MCP_ROOT env var that McpRunner uses for path translation.
    [string]$HostProjectRoot      = $env:BENCH_HOST_ROOT,
    [string]$ContainerProjectRoot = $(if ($env:BENCH_MCP_ROOT) { $env:BENCH_MCP_ROOT } else { "/host/dev" }),
    [switch]$Detach  # default: foreground with --rm; use -Detach to run in background
)

if (-not $HostProjectRoot) {
    throw "Set -HostProjectRoot or `$env:BENCH_HOST_ROOT (absolute path to your bench checkout)"
}

$ErrorActionPreference = "Stop"

# Remove any previous container with the same name.
docker rm -f $Name 2>$null | Out-Null

Write-Host "Starting container $Name from $Tag (MCP on localhost:$McpPort)..." -ForegroundColor Cyan

$mount = "${HostProjectRoot}:${ContainerProjectRoot}:ro"

if ($Detach) {
    docker run -d `
        --name $Name `
        --shm-size=1g `
        -p "${McpPort}:6003" `
        -p "${VncPort}:5900" `
        -v $mount `
        $Tag
    Write-Host "Detached. Tail logs with: docker logs -f $Name" -ForegroundColor Green
}
else {
    docker run --rm `
        --name $Name `
        --shm-size=1g `
        -p "${McpPort}:6003" `
        -p "${VncPort}:5900" `
        -v $mount `
        $Tag
}
