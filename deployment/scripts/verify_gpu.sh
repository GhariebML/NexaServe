#!/usr/bin/env bash
set -Eeuo pipefail
nvidia-smi
docker run --rm --gpus all ubuntu:24.04 nvidia-smi
echo 'Container GPU passthrough passed. Verify Ollama GPU use by observing nvidia-smi during generation.'
