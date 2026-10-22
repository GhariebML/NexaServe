#!/usr/bin/env bash
set -Eeuo pipefail
source "$(dirname -- "$0")/common.sh"
here="$(cd -- "$(dirname -- "$0")/.." && pwd)"
python3 "$here/checks/validate_n8n_release.py"
require_env
echo 'Bundle intentionally contains no n8n credentials. Verify credential bindings, endpoints and subworkflow IDs before activation.'
dc exec n8n n8n import:workflow --separate --input=/opt/nexaserve/workflows
echo 'Import command completed. Verify target state with the isolated acceptance procedure; this script does not publish workflows.'
