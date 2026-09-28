#!/usr/bin/env bash
set -Eeuo pipefail
source "$(dirname -- "$0")/common.sh"
require_env
mode="${1:-gpu}"
# gpu and online are equivalent: dc() always applies the GPU overlay (no CPU fallback).
if [[ "$mode" == gpu || "$mode" == online ]]; then dc pull; dc build; dc up -d
elif [[ "$mode" == offline ]]; then "$DEPLOY_DIR/scripts/install_offline.sh"
else echo 'Usage: deploy.sh [gpu|online|offline]' >&2; exit 2; fi
echo 'Services started. Verify health, workflows, model generation, dashboard admin, and WhatsApp separately.'
