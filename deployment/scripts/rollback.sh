#!/usr/bin/env bash
set -Eeuo pipefail
source "$(dirname -- "$0")/common.sh"; require_env
[[ $# -eq 1 && -d "$1" ]] || { echo 'Usage: rollback.sh /path/to/previous/deployment'; exit 2; }
echo 'Stop ingress; retain current volumes; deploy the previous approved bundle. Restore a verified pre-upgrade backup only after assessing schema/data changes. This script never removes volumes.'
echo "Previous bundle: $1"
