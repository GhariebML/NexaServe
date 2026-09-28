#!/usr/bin/env bash
set -Eeuo pipefail
source "$(dirname -- "$0")/common.sh"
require_env
[[ $# -eq 2 ]] || { echo 'Usage: restore.sh CUSTOMER_SERVICE.dump N8N.dump'; exit 2; }
read -r -p 'Restore may replace database objects and data. Type RESTORE to continue: ' ack
[[ "$ack" == RESTORE ]] || exit 1
root_user=$(grep '^POSTGRES_USER=' "$ENV_FILE"|cut -d= -f2-)
dc exec -T postgres pg_restore --clean --if-exists --no-owner -U "$root_user" -d "$(grep '^CS_DB_NAME=' "$ENV_FILE"|cut -d= -f2-)" < "$1"
dc exec -T postgres pg_restore --clean --if-exists --no-owner -U "$root_user" -d "$(grep '^N8N_DB_NAME=' "$ENV_FILE"|cut -d= -f2-)" < "$2"
echo 'Restore complete. Validate app/workflows/knowledge before reopening traffic.'
