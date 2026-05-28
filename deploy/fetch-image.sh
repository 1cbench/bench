#!/usr/bin/env bash
# Fetch the onec-training-mcp:latest image tar from Google Drive and
# load it into the local Docker daemon. Idempotent: if the image is
# already present locally, exits without re-downloading.
#
# Usage: ./fetch-image.sh [target-tar-path]
#   target-tar-path defaults to ./onec-training-mcp.tar (next to this script)

set -euo pipefail

GDRIVE_FILE_ID="1Z6ZG5p80Fen_vqRvV6XnlAuvSLrjcfL4"
IMAGE_TAG="onec-training-mcp:latest"
TAR_PATH="${1:-$(dirname "$0")/onec-training-mcp.tar}"

if docker image inspect "$IMAGE_TAG" >/dev/null 2>&1; then
    echo "[fetch-image] $IMAGE_TAG already present locally — nothing to do."
    echo "[fetch-image] To force a redownload, remove the image first:"
    echo "[fetch-image]   docker rmi $IMAGE_TAG"
    exit 0
fi

if ! command -v gdown >/dev/null 2>&1; then
    echo "[fetch-image] gdown not found; installing into the current Python env..."
    python3 -m pip install --user gdown
    # gdown lands in ~/.local/bin which may not be on PATH yet
    export PATH="$HOME/.local/bin:$PATH"
fi

echo "[fetch-image] Downloading image tar from Google Drive (~3.3 GB)..."
gdown "$GDRIVE_FILE_ID" -O "$TAR_PATH"

echo "[fetch-image] Loading into Docker..."
docker load -i "$TAR_PATH"

echo "[fetch-image] Removing tar..."
rm -f "$TAR_PATH"

echo "[fetch-image] Done. Verify with: docker images $IMAGE_TAG"
