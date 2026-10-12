# Local Generation Runtime Diagnosis

**Date:** 2026-10-12  
**Status:** BLOCKED — generation failure reproduced; cause not conclusively attributed.

## Observed behavior

A small direct generation request to the local Ollama endpoint (`qwen2.5:3b`, `/api/generate`) returned HTTP 500 with `llama-server process has terminated: signal: killed`. No later generation request was made. An earlier embedding smoke test succeeded for Arabic and English inputs and returned 768-dimensional vectors using `nomic-embed-text`.

The `qwen2.5:3b` model is installed (about 1.9 GB); `qwen2.5:1.5b` (about 986 MB), `qwen2.5:7b` (about 4.7 GB), and `nomic-embed-text` are also installed. A prior `ollama ps` observation listed the 1.5b model and embedder on CPU; it does not establish their memory or performance under the failed request.

## Resource evidence and limits

- Docker daemon reported about 3.25 GiB total memory; the Windows host reported about 1.78 GiB free at the time of inspection.
- Ollama container was running, had `OOMKilled=true` in its state, `RestartCount=0`, and no explicit container memory limit. Its cgroup `memory.events` showed four `oom_kill` events over the container lifetime, while `oom` was zero.
- Container logs near the inspected period showed successful `/api/tags` health probes but no runner crash or request-specific OOM detail. Docker events showed health-check executions and no event that tied an OOM kill to this generation request.

These observations make memory pressure plausible, but do not prove that the failed `qwen2.5:3b` request was killed by the kernel or identify the process that received SIGKILL. No safe low-concurrency isolation experiment was run against the shared Ollama container.

## Disposition

Do not mark generation healthy, switch models, or run candidate chat acceptance cases yet. Preserve the current model configuration while the failure cause remains unverified. Resolution requires a dedicated candidate Ollama runtime with measured memory headroom, a controlled minimal generation check, and captured Ollama/container diagnostics. Until then, generation-dependent RAG acceptance is blocked.
