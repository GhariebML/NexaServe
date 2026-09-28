#!/usr/bin/env bash
set -Eeuo pipefail
export NEXASERVE_OFFLINE=1
source "$(dirname -- "$0")/common.sh"
require_env
im="$DEPLOY_DIR/assets/offline/images"
[[ -f "$im/nexaserve-images.tar" && -f "$im/nexaserve-app-images.tar" ]] || { echo 'Offline image archives missing.' >&2; exit 1; }
docker load -i "$im/nexaserve-images.tar"
docker load -i "$im/nexaserve-app-images.tar"
dc up -d --no-build
archive="$DEPLOY_DIR/assets/offline/models/ollama-models.tar.gz"
if [[ -f "$archive" ]]; then
  dc stop ollama
  volume=$(docker volume ls --filter label=com.docker.compose.project=nexaserve --filter label=com.docker.compose.volume=ollama-data -q | head -n 1)
  [[ -n "$volume" ]] || { echo 'Compose Ollama data volume not found.' >&2; exit 1; }
  docker run --rm -v "$volume:/root/.ollama" -v "$DEPLOY_DIR/assets/offline/models:/restore:ro" alpine:3.21@sha256:ce64758a109eb420d874a118f87920e625e12d3634e03b4a5573fd9f6e5d3507 tar -xzf /restore/ollama-models.tar.gz -C /root/.ollama
  dc start ollama
  dc exec -T ollama ollama list
fi
echo 'Services started. Verify generation and GPU inference with scripts/13_initialize_models.sh, not only model-list output.'
