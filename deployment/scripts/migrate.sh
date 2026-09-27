#!/usr/bin/env bash
set -Eeuo pipefail
source "$(dirname -- "$0")/common.sh"
require_env
root_user=$(grep '^POSTGRES_USER=' "$ENV_FILE"|cut -d= -f2-)
db=$(grep '^CS_DB_NAME=' "$ENV_FILE"|cut -d= -f2-)
app_user=$(grep '^CS_DB_USER=' "$ENV_FILE"|cut -d= -f2-)
dc exec -T postgres psql -v ON_ERROR_STOP=1 -U "$root_user" -d "$db" -f /opt/nexaserve/001_professional_support.sql
dc exec -T postgres psql -v ON_ERROR_STOP=1 -U "$root_user" -d "$db" -f /opt/nexaserve/002_dashboard_admin_users.sql
dc exec -T postgres psql -v ON_ERROR_STOP=1 -U "$root_user" -d "$db" -c "GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO $app_user; GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO $app_user;"
echo 'Additive migrations applied; this script does not reset or delete data.'
