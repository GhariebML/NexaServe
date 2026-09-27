#!/usr/bin/env bash
set -Eeuo pipefail
here="$(cd -- "$(dirname -- "$0")/../.." && pwd)"
test -f "$here/DEPLOYMENT.md"
test -f "$here/compose/docker-compose.yml"
test -f "$here/assets/postgres/schema.sql"
test -f "$here/assets/n8n/workflows/01_gateway_dispatcher.json"
"$here/scripts/verify_bundle.sh"
"$here/checks/verify_secrets.sh"
echo 'Static package checks passed.'
