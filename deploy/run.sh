#!/usr/bin/env bash
# Launch the 1C-training-MCP container with the MCP port exposed.
# The container ships its own Xvfb and clicks "Подключиться" itself, so no host
# X server is required.
#
# Required (via env or flags):
#   BENCH_HOST_ROOT — absolute path on the host pointing at your 1cbench checkout
# Optional (env, with defaults shown):
#   BENCH_MCP_ROOT  — /host/dev   (bind-mount target inside the container; must
#                                  match the env var McpRunner reads)
#   IMAGE_TAG       — onec-training-mcp:latest
#   CONTAINER_NAME  — onec-mcp
#   MCP_PORT        — 6003
#   VNC_PORT        — 5900
#   DETACH          — 0  (set =1 to run with -d instead of foreground --rm)

set -euo pipefail

: "${BENCH_HOST_ROOT:?Set BENCH_HOST_ROOT to your bench checkout's absolute path}"
: "${BENCH_MCP_ROOT:=/host/dev}"
: "${IMAGE_TAG:=onec-training-mcp:latest}"
: "${CONTAINER_NAME:=onec-mcp}"
: "${MCP_PORT:=6003}"
: "${VNC_PORT:=5900}"
: "${DETACH:=0}"

docker rm -f "$CONTAINER_NAME" 2>/dev/null || true

echo "Starting container $CONTAINER_NAME from $IMAGE_TAG (MCP on localhost:$MCP_PORT)..."

MOUNT="${BENCH_HOST_ROOT}:${BENCH_MCP_ROOT}:ro"

if [ "$DETACH" = "1" ]; then
    docker run -d \
        --name "$CONTAINER_NAME" \
        --shm-size=1g \
        -p "${MCP_PORT}:6003" \
        -p "${VNC_PORT}:5900" \
        -v "$MOUNT" \
        "$IMAGE_TAG"
    echo "Detached. Tail logs with: docker logs -f $CONTAINER_NAME"
else
    docker run --rm \
        --name "$CONTAINER_NAME" \
        --shm-size=1g \
        -p "${MCP_PORT}:6003" \
        -p "${VNC_PORT}:5900" \
        -v "$MOUNT" \
        "$IMAGE_TAG"
fi
