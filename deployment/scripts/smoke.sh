#!/usr/bin/env bash
set -Eeuo pipefail
source "$(dirname -- "$0")/common.sh"
require_env
dc ps --status running
cid=$(dc ps -q postgres)
root_user=$(grep '^POSTGRES_USER=' "$ENV_FILE" | cut -d= -f2-)
db=$(grep '^CS_DB_NAME=' "$ENV_FILE" | cut -d= -f2-)
docker exec "$cid" psql -U "$root_user" -d "$db" -v ON_ERROR_STOP=1 -c "SELECT extname FROM pg_extension WHERE extname IN ('vector','pg_trgm','uuid-ossp') ORDER BY 1;" -c "SELECT count(*) AS knowledge_rows, count(embedding) AS embedded_rows FROM knowledge_base WHERE is_active;" -c "SELECT version FROM nexaserve_schema_migrations ORDER BY version;"
docker exec "$(dc ps -q ollama)" ollama list
echo 'Infrastructure smoke checks only. Run RAG webhook, dashboard login, HITL, generation and approved WhatsApp tests before launch.'
