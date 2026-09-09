#!/bin/bash
set -e

echo "=== Initializing Application Databases and Dedicated Roles ==="

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    -- 1. Provision n8n dedicated role and database
    DO \$\$
    BEGIN
        IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '$N8N_DB_USER') THEN
            CREATE ROLE $N8N_DB_USER WITH LOGIN PASSWORD '$N8N_DB_PASSWORD';
        END IF;
    END
    \$\$;

    SELECT 'CREATE DATABASE $N8N_DB_NAME OWNER $N8N_DB_USER'
    WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$N8N_DB_NAME')\gexec

    GRANT ALL PRIVILEGES ON DATABASE $N8N_DB_NAME TO $N8N_DB_USER;

    -- 2. Provision Customer Service dedicated role and database
    DO \$\$
    BEGIN
        IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '$CS_DB_USER') THEN
            CREATE ROLE $CS_DB_USER WITH LOGIN PASSWORD '$CS_DB_PASSWORD';
        END IF;
    END
    \$\$;

    SELECT 'CREATE DATABASE $CS_DB_NAME OWNER $CS_DB_USER'
    WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$CS_DB_NAME')\gexec

    GRANT ALL PRIVILEGES ON DATABASE $CS_DB_NAME TO $CS_DB_USER;
EOSQL

# Assign schema permissions inside each database
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$N8N_DB_NAME" <<-EOSQL
    GRANT ALL ON SCHEMA public TO $N8N_DB_USER;
    ALTER SCHEMA public OWNER TO $N8N_DB_USER;
EOSQL

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$CS_DB_NAME" <<-EOSQL
    GRANT ALL ON SCHEMA public TO $CS_DB_USER;
    ALTER SCHEMA public OWNER TO $CS_DB_USER;
EOSQL

echo "=== Application Databases and Dedicated Roles Created Successfully ==="
