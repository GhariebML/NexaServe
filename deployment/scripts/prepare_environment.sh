#!/usr/bin/env bash
set -Eeuo pipefail
here="$(cd -- "$(dirname -- "$0")/.." && pwd)"; target="$here/.env"
[[ ! -e "$target" ]] || { echo "Refusing to overwrite $target" >&2; exit 1; }
cp "$here/.env.example" "$target"
set_env(){ sed -i "s|^$1=.*$|$1=$2|" "$target"; }
random_hex(){ openssl rand -hex 32; }
set_env POSTGRES_PASSWORD "$(random_hex)"
set_env N8N_DB_PASSWORD "$(random_hex)"
set_env CS_DB_PASSWORD "$(random_hex)"
set_env REDIS_PASSWORD "$(random_hex)"
set_env N8N_ENCRYPTION_KEY "$(random_hex)"
set_env N8N_USER_MANAGEMENT_JWT_SECRET "$(random_hex)"
set_env DASHBOARD_JWT_SECRET "$(random_hex)"
chmod 600 "$target"
echo 'Created .env with fresh random credentials; values were not printed. Store a protected recovery copy.'
