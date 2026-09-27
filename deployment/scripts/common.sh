#!/usr/bin/env bash
set -Eeuo pipefail
DEPLOY_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="$DEPLOY_DIR/compose/docker-compose.yml"
ENV_FILE="$DEPLOY_DIR/.env"
dc() { docker compose --project-directory "$DEPLOY_DIR" --env-file "$ENV_FILE" -f "$COMPOSE_FILE" "$@"; }
require_env() { [[ -f "$ENV_FILE" ]] || { echo "Missing $ENV_FILE. Run scripts/prepare_environment.sh first." >&2; exit 2; }; }
