#!/usr/bin/env bash
set -Eeuo pipefail
source "$(dirname -- "$0")/common.sh"
require_env
out="${1:-$(dirname "$DEPLOY_DIR")/nexaserve-offline-package}"
case "$(realpath -m "$out")/" in "$(realpath -m "$DEPLOY_DIR")/"*) echo 'Choose an output directory outside the source deployment folder.' >&2; exit 2;; esac
[[ ! -e "$out" ]] || { echo "Refusing to overwrite $out" >&2; exit 2; }
mkdir -p "$out/.staging/images" "$out/.staging/models"
dc pull postgres redis ollama n8n
dc --profile tools build whatsapp dashboard scraper kb-ingest
docker pull alpine:3.21
docker pull nginx:stable-alpine
dc up -d ollama
chat=$(grep '^OLLAMA_MODEL=' "$ENV_FILE"|cut -d= -f2-); embed=$(grep '^EMBED_MODEL=' "$ENV_FILE"|cut -d= -f2-)
dc exec ollama ollama pull "$chat"; dc exec ollama ollama pull "$embed"
docker image save pgvector/pgvector:pg16 redis:7-bookworm ollama/ollama:latest docker.n8n.io/n8nio/n8n:2.38.1 nginx:stable-alpine alpine:3.21 -o "$out/.staging/images/nexaserve-images.tar"
docker image save nexaserve-whatsapp nexaserve-dashboard nexaserve-scraper nexaserve-kb-ingest -o "$out/.staging/images/nexaserve-app-images.tar"
cid=$(dc ps -q ollama)
docker exec "$cid" ollama list >/dev/null
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
docker cp "$cid:/root/.ollama/models" "$tmp/models"
tar -C "$tmp" -czf "$out/.staging/models/ollama-models.tar.gz" models
cp -a "$DEPLOY_DIR" "$out/deployment"
rm -f "$out/deployment/.env"
mkdir -p "$out/deployment/assets/offline/images" "$out/deployment/assets/offline/models"
cp "$out/.staging/images/"* "$out/deployment/assets/offline/images/"
cp "$out/.staging/models/"* "$out/deployment/assets/offline/models/"
(cd "$out/deployment" && find . -type f ! -name MANIFEST.sha256 ! -path './.env' -print0 | sort -z | xargs -0 sha256sum > MANIFEST.sha256)
rm -rf "$out/.staging"
echo "Offline deployment folder created at $out/deployment. OS/NVIDIA packages must come from Ministry-approved repositories; no secrets or WhatsApp auth are bundled."
