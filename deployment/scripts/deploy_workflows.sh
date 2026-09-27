#!/usr/bin/env bash
set -Eeuo pipefail
source "$(dirname -- "$0")/common.sh"
require_env
echo 'Bundle intentionally contains no n8n credentials. Verify credential bindings, endpoints and subworkflow IDs before activation.'
dc exec n8n n8n import:workflow --separate --input=/opt/nexaserve/workflows
echo 'Inspect imported workflows in n8n; activate only reviewed canonical workflows after credential setup.'
