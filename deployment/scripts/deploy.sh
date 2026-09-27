#!/usr/bin/env bash
set -Eeuo pipefail
source "$(dirname -- "$0")/common.sh"
require_env
mode="${1:-gpu}"
if [[ "$mode" == online ]]; then dc pull; dc build; dc up -d
elif [[ "$mode" == gpu ]]; then
  docker compose --project-directory "$DEPLOY_DIR" --env-file "$ENV_FILE" -f "$COMPOSE_FILE" -f "$DEPLOY_DIR/compose/docker-compose.gpu.yml" pull
  docker compose --project-directory "$DEPLOY_DIR" --env-file "$ENV_FILE" -f "$COMPOSE_FILE" -f "$DEPLOY_DIR/compose/docker-compose.gpu.yml" build
  docker compose --project-directory "$DEPLOY_DIR" --env-file "$ENV_FILE" -f "$COMPOSE_FILE" -f "$DEPLOY_DIR/compose/docker-compose.gpu.yml" up -d
elif [[ "$mode" == offline ]]; then "$DEPLOY_DIR/scripts/install_offline.sh"
else echo 'Usage: deploy.sh [gpu|online|offline]' >&2; exit 2; fi
echo 'Services started. Verify health, workflows, model generation, dashboard admin, and WhatsApp separately.'
