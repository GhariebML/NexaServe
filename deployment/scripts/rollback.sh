#!/usr/bin/env bash
set -Eeuo pipefail
source "$(dirname -- "$0")/common.sh"; require_env
[[ $# -ge 1 && $# -le 2 && -d "$1" ]] || { echo 'Usage: rollback.sh /path/to/previous/deployment [online|offline]'; exit 2; }
previous=$(cd -- "$1" && pwd)
[[ -f "$previous/compose/docker-compose.yml" ]] || { echo 'Previous deployment Compose file not found.' >&2; exit 2; }
mode="${2:-online}"
read -r -p 'Stop public ingress first. Type ROLLBACK to recreate application services from the previous bundle while preserving volumes: ' ack
[[ "$ack" == ROLLBACK ]] || exit 1
args=(docker compose -p nexaserve --project-directory "$previous" --env-file "$ENV_FILE" -f "$previous/compose/docker-compose.yml" -f "$previous/compose/docker-compose.gpu.yml")
if [[ "$mode" == offline ]]; then args+=( -f "$previous/compose/docker-compose.offline.yml" ); elif [[ "$mode" != online ]]; then echo 'Mode must be online or offline.' >&2; exit 2; fi
"${args[@]}" up -d --no-build
echo 'Previous application images started; current volumes were preserved. Validate compatibility before reopening ingress. Restore a verified pre-upgrade DB backup only if the schema/data rollback plan requires it.'
