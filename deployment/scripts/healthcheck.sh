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
root_user=$(grep '^POSTGRES_USER=' "$ENV_FILE" | cut -d= -f2-)
db=$(grep '^CS_DB_NAME=' "$ENV_FILE" | cut -d= -f2-)
docker exec "$cid" psql -U "$root_user" -d "$db" -Atc "SELECT extname FROM pg_extension WHERE extname='vector';" | grep -qx vector || { echo 'FAIL: pgvector missing'; bad=1; }
if (( bad != 0 )); then exit 1; fi
echo 'Container and pgvector checks passed; they do not prove model inference or customer workflow behavior.'
