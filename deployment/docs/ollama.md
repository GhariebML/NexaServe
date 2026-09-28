# Ollama service

Ollama is an internal service with a persistent named model volume and GPU assignment in the GPU overlay. Workflow exports call `http://cs-ollama:11434`; embedding size is 768. Initialize with `scripts/13_initialize_models.sh`, then test representative Arabic/English generation and observe `nvidia-smi`.

The health probe `ollama list` proves only that the daemon answers. The runtime audit previously observed the Qwen llama-server being OOM-killed; target acceptance must include successful generation, stable memory and controlled concurrency. Keep model/API ports private.

All maintenance scripts go through `scripts/common.sh` `dc()`, which always applies `compose/docker-compose.gpu.yml`; `scripts/healthcheck.sh` fails if the Ollama container lacks its GPU reservation. Do not run bare `docker compose` commands against the stack without the GPU overlay: Compose would recreate Ollama on CPU.
