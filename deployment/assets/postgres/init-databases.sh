#!/usr/bin/env bash
set -Eeuo pipefail
for name in "$N8N_DB_NAME" "$N8N_DB_USER" "$CS_DB_NAME" "$CS_DB_USER"; do
  [[ "$name" =~ ^[a-zA-Z_][a-zA-Z0-9_]{0,62}$ ]] || { echo 'Unsafe database/user identifier.' >&2; exit 1; }
done
for secret in "$N8N_DB_PASSWORD" "$CS_DB_PASSWORD"; do
  [[ "$secret" =~ ^[a-f0-9]{64}$ ]] || { echo 'Expected generated 64-character hex password.' >&2; exit 1; }
done
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<SQL
CREATE ROLE $N8N_DB_USER LOGIN PASSWORD '$N8N_DB_PASSWORD';
CREATE DATABASE $N8N_DB_NAME OWNER $N8N_DB_USER;
CREATE ROLE $CS_DB_USER LOGIN PASSWORD '$CS_DB_PASSWORD';
CREATE DATABASE $CS_DB_NAME OWNER $CS_DB_USER;
SQL
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$N8N_DB_NAME" -c "GRANT ALL ON SCHEMA public TO $N8N_DB_USER; ALTER SCHEMA public OWNER TO $N8N_DB_USER;"
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$CS_DB_NAME" -c "GRANT ALL ON SCHEMA public TO $CS_DB_USER; ALTER SCHEMA public OWNER TO $CS_DB_USER;"
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$CS_DB_NAME" -f /opt/nexaserve/schema.sql
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$CS_DB_NAME" -f /opt/nexaserve/001_professional_support.sql
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$CS_DB_NAME" -f /opt/nexaserve/002_dashboard_admin_users.sql
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$CS_DB_NAME" -c "GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO $CS_DB_USER; GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO $CS_DB_USER; ALTER DEFAULT PRIVILEGES FOR ROLE $POSTGRES_USER IN SCHEMA public GRANT ALL ON TABLES TO $CS_DB_USER; ALTER DEFAULT PRIVILEGES FOR ROLE $POSTGRES_USER IN SCHEMA public GRANT ALL ON SEQUENCES TO $CS_DB_USER; INSERT INTO nexaserve_schema_migrations(version) VALUES ('001_professional_support'),('002_dashboard_admin_users') ON CONFLICT DO NOTHING;"
