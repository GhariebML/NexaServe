#!/usr/bin/env bash
set -Eeuo pipefail
[[ -r /etc/os-release ]] || exit 1
. /etc/os-release
[[ "$ID" == ubuntu && "$VERSION_ID" == 24.04 ]] || { echo 'Only Ubuntu 24.04 is supported.' >&2; exit 1; }
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg lsb-release jq openssl rsync tar gzip acl ufw
