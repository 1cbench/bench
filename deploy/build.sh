#!/usr/bin/env bash
# Build the 1C-training-MCP image.
# Uses BuildKit named build contexts so the 1.5 GB installer and the .dt dump
# never enter the local docker build context — they're bind-mounted only inside
# the relevant RUN steps.
#
# Required (via env or flags):
#   ONEC_DISTRO_DIR — directory holding setup-training-<ver>-x86_64.run
#   ONEC_DB_DIR     — directory holding 1Cv8_no_users.dt (or your own .dt dump)
# Optional (env, with defaults shown):
#   ONEC_VERSION    — 8.3.27.2130
#   IMAGE_TAG       — onec-training-mcp:latest
#   PYTHON          — python3   (must be able to import struct/zlib — stdlib only)

set -euo pipefail

: "${ONEC_DISTRO_DIR:?Set ONEC_DISTRO_DIR (directory with setup-training-*.run)}"
: "${ONEC_DB_DIR:?Set ONEC_DB_DIR (directory with the .dt dump)}"
: "${ONEC_VERSION:=8.3.27.2130}"
: "${IMAGE_TAG:=onec-training-mcp:latest}"
: "${PYTHON:=python3}"

HERE="$(cd "$(dirname "$0")" && pwd)"

for p in \
    "$ONEC_DISTRO_DIR/setup-training-$ONEC_VERSION-x86_64.run" \
    "$ONEC_DB_DIR/1Cv8_no_users.dt" \
    "$HERE/payload/MCP_Toolkit_linux.epf" \
    "$HERE/payload/MCP_Toolkit_linux/Forms/Форма/Ext/Form/Module.bsl" \
    "$HERE/repack_form_module.py" \
    "$HERE/Dockerfile" \
    "$HERE/entrypoint.sh"
do
    if [ ! -e "$p" ]; then
        echo "Missing required file: $p" >&2
        exit 1
    fi
done

echo "Repacking MCP_Toolkit.epf with headless-autostart Module.bsl..."
"$PYTHON" "$HERE/repack_form_module.py" \
    "$HERE/payload/MCP_Toolkit_linux.epf" \
    "Форма" \
    "$HERE/payload/MCP_Toolkit_linux/Forms/Форма/Ext/Form/Module.bsl" \
    "$HERE/payload/MCP_Toolkit.epf"

export DOCKER_BUILDKIT=1

echo "Building $IMAGE_TAG ..."
echo "  distro = $ONEC_DISTRO_DIR"
echo "  db     = $ONEC_DB_DIR"
echo "  ver    = $ONEC_VERSION"

docker build \
    --progress=plain \
    --tag "$IMAGE_TAG" \
    --build-arg "ONEC_VERSION=$ONEC_VERSION" \
    --build-context "distro=$ONEC_DISTRO_DIR" \
    --build-context "db=$ONEC_DB_DIR" \
    -f "$HERE/Dockerfile" \
    "$HERE"

echo "Built $IMAGE_TAG"
