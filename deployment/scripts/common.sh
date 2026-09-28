#!/usr/bin/env bash
set -Eeuo pipefail
DEPLOY_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="$DEPLOY_DIR/compose/docker-compose.yml"
ENV_FILE="$DEPLOY_DIR/.env"
# The GPU overlay is always applied: CPU inference is not certified, and any
# compose call without it (e.g. `run` of a tools service) would recreate Ollama
# without the GPU reservation. Set NEXASERVE_OFFLINE=1 to add the offline overlay.
COMPOSE_FILES=(-f "$COMPOSE_FILE" -f "$DEPLOY_DIR/compose/docker-compose.gpu.yml")
if [[ "${NEXASERVE_OFFLINE:-0}" == 1 ]]; then COMPOSE_FILES+=(-f "$DEPLOY_DIR/compose/docker-compose.offline.yml"); fi
dc() { docker compose --project-directory "$DEPLOY_DIR" --env-file "$ENV_FILE" "${COMPOSE_FILES[@]}" "$@"; }
require_env() { [[ -f "$ENV_FILE" ]] || { echo "Missing $ENV_FILE. Run scripts/prepare_environment.sh first." >&2; exit 2; }; }
env_value() { grep "^$1=" "$ENV_FILE" | cut -d= -f2-; }
