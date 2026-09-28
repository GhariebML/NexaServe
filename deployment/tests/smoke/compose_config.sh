#!/usr/bin/env bash
set -Eeuo pipefail
here="$(cd -- "$(dirname -- "$0")/../.." && pwd)"
docker compose --project-directory "$here" --env-file "$here/.env" -f "$here/compose/docker-compose.yml" config --quiet
docker compose --project-directory "$here" --env-file "$here/.env" -f "$here/compose/docker-compose.yml" -f "$here/compose/docker-compose.gpu.yml" config --quiet
docker compose --project-directory "$here" --env-file "$here/.env" -f "$here/compose/docker-compose.yml" -f "$here/compose/docker-compose.gpu.yml" -f "$here/compose/docker-compose.offline.yml" config --quiet
echo 'Compose variants parsed successfully.'
