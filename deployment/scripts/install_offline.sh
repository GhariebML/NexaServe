#!/usr/bin/env bash
set -Eeuo pipefail
source "$(dirname -- "$0")/common.sh"
require_env
im="$DEPLOY_DIR/assets/offline/images"
[[ -f "$im/nexaserve-images.tar" && -f "$im/nexaserve-app-images.tar" ]] || { echo 'Offline image archives missing.' >&2; exit 1; }
docker load -i "$im/nexaserve-images.tar"
docker load -i "$im/nexaserve-app-images.tar"
docker compose --project-directory "$DEPLOY_DIR" --env-file "$ENV_FILE" -f "$COMPOSE_FILE" -f "$DEPLOY_DIR/compose/docker-compose.gpu.yml" -f "$DEPLOY_DIR/compose/docker-compose.offline.yml" up -d --no-build
archive="$DEPLOY_DIR/assets/offline/models/ollama-models.tar.gz"
if [[ -f "$archive" ]]; then
  docker compose --project-directory "$DEPLOY_DIR" --env-file "$ENV_FILE" -f "$COMPOSE_FILE" -f "$DEPLOY_DIR/compose/docker-compose.gpu.yml" -f "$DEPLOY_DIR/compose/docker-compose.offline.yml" stop ollama
  volume=$(docker volume ls --filter label=com.docker.compose.project=nexaserve --filter label=com.docker.compose.volume=ollama-data -q | head -n 1)
  [[ -n "$volume" ]] || { echo 'Compose Ollama data volume not found.' >&2; exit 1; }
  docker run --rm -v "$volume:/root/.ollama" -v "$DEPLOY_DIR/assets/offline/models:/restore:ro" alpine:3.21@sha256:ce64758a109eb420d874a118f87920e625e12d3634e03b4a5573fd9f6e5d3507 tar -xzf /restore/ollama-models.tar.gz -C /root/.ollama
  docker compose --project-directory "$DEPLOY_DIR" --env-file "$ENV_FILE" -f "$COMPOSE_FILE" -f "$DEPLOY_DIR/compose/docker-compose.gpu.yml" -f "$DEPLOY_DIR/compose/docker-compose.offline.yml" start ollama
  docker compose --project-directory "$DEPLOY_DIR" --env-file "$ENV_FILE" -f "$COMPOSE_FILE" -f "$DEPLOY_DIR/compose/docker-compose.gpu.yml" -f "$DEPLOY_DIR/compose/docker-compose.offline.yml" exec -T ollama ollama list
fi
echo 'Services started. Verify generation and GPU inference, not only model-list output.'
