#!/usr/bin/env bash
set -Eeuo pipefail
source "$(dirname -- "$0")/common.sh"
require_env
dc ps
bad=0
for s in postgres redis ollama n8n whatsapp dashboard; do
  cid=$(dc ps -q "$s" 2>/dev/null || true)
  if [[ -z "$cid" ]]; then echo "FAIL: $s not created"; bad=1; continue; fi
  state=$(docker inspect -f '{{.State.Status}}' "$cid")
  health=$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}no-healthcheck{{end}}' "$cid")
  echo "$s: $state / $health"
  if [[ "$state" != running || "$health" != healthy ]]; then bad=1; fi
done
cid=$(dc ps -q postgres)
root_user=$(env_value POSTGRES_USER)
db=$(env_value CS_DB_NAME)
docker exec "$cid" psql -U "$root_user" -d "$db" -Atc "SELECT extname FROM pg_extension WHERE extname='vector';" | grep -qx vector || { echo 'FAIL: pgvector missing'; bad=1; }
ollama_cid=$(dc ps -q ollama || true)
if [[ -n "$ollama_cid" && "$(docker inspect -f '{{json .HostConfig.DeviceRequests}}' "$ollama_cid")" != *gpu* ]]; then
  echo 'FAIL: ollama container has no GPU reservation (silent CPU fallback)'; bad=1
fi
if (( bad != 0 )); then exit 1; fi
echo 'Container, pgvector and GPU-reservation checks passed; they do not prove model inference or customer workflow behavior.'
