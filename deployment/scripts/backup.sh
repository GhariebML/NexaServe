#!/usr/bin/env bash
set -Eeuo pipefail
source "$(dirname -- "$0")/common.sh"
require_env
base="${NEXASERVE_DATA_ROOT:-/var/lib/nexaserve}/backups"; install -d -m 0700 "$base"
stamp=$(date -u +%Y%m%dT%H%M%SZ); out="$base/$stamp"; install -d -m 0700 "$out"
root_user=$(grep '^POSTGRES_USER=' "$ENV_FILE"|cut -d= -f2-)
dc exec -T postgres pg_dump -U "$root_user" -d "$(grep '^CS_DB_NAME=' "$ENV_FILE"|cut -d= -f2-)" --format=custom > "$out/customerservice.dump"
dc exec -T postgres pg_dump -U "$root_user" -d "$(grep '^N8N_DB_NAME=' "$ENV_FILE"|cut -d= -f2-)" --format=custom > "$out/n8n.dump"
cp "$ENV_FILE" "$out/env.secret"; chmod 600 "$out/env.secret"
echo "Backups saved in $out. Protect as secret-bearing. Back up named volumes during a coordinated stopped/consistent window."
