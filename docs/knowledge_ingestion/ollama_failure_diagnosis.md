# Ollama Failure Diagnosis — Read-only Evidence

**Collection date:** 2026-10-12  
**Finding:** The generation failure is confirmed; its cause is **unresolved**. No corrective action or generation retry was performed.

## Evidence collected

- Prior direct request to `http://ollama:11434/api/generate` using `qwen2.5:3b` returned HTTP 500 with `llama-server process has terminated: signal: killed`. The request timestamp and request-level Ollama log entry are not available in the retained evidence.
- On this read-only collection, `cs-ollama` was running and healthy, `RestartCount=0`, and had `OOMKilled=true` in Docker state. Its current container start time was `2026-10-11T23:50:20Z`. The flag is container lifecycle evidence, not proof that this particular model runner was killed by OOM.
- Container has no configured memory limit (`HostConfig.Memory=0`; cgroup `memory.max=max`). Current cgroup counters read `oom 0`, `oom_kill 4`, `oom_group_kill 0`. This proves OOM-kill events occurred somewhere in the cgroup lifetime, but does not identify the process, event time, or relation to the generation request.
- Docker's current daemon memory limit was 3.251 GiB. `docker stats` at collection showed Ollama using 42.5 MiB, 0% CPU, with no model loaded (`ollama ps` empty). This is an idle snapshot and does not describe peak usage during generation.
- Windows memory at collection: 16,020,772 KB visible total and 1,966,404 KB free. This is also a point-in-time observation, not telemetry from the failed request.
- `ollama list` showed `qwen2.5:3b` (1.9 GB), `qwen2.5:1.5b` (986 MB), `qwen2.5:7b` (4.7 GB), and `nomic-embed-text:latest` (274 MB) installed.
- The last 24 hours of accessible Ollama logs contained no matching generation request, runner termination, or OOM text. Docker events in that window showed health-check `ollama list` execs, not a container OOM/die event. The request time may fall outside the retained diagnostic window or request details may not have been logged.

## Hypothesis assessment

| Explanation | Evidence assessment |
|---|---|
| OOM termination | Possible, not attributed. Four cgroup `oom_kill` events and Docker `OOMKilled=true` establish historical OOM-related lifecycle evidence; no timestamp/process tie to the failed inference exists. |
| Container or host process termination | Runner received SIGKILL according to the HTTP error. No evidence identifies who sent the signal or whether the Ollama container/host terminated it. Container was running during this collection. |
| Model-load failure | Not established. Model is installed; no request-time logs or runner diagnostics were retained. |
| Timeout/request handling | Not established. HTTP 500 includes runner process termination, but there is no timeout trace or duration evidence. |
| Other cause | Cannot be ruled out from available telemetry. |

## Smallest useful next experiment (later, after explicit authorization)

Use a **dedicated candidate Ollama instance**, separate from the baseline model service and with its own model volume, under a controlled single-request window. Before the request, record host and candidate-container memory; capture container/cgroup OOM counters, Docker events, Ollama logs, request start/end time, HTTP response, and runner exit status. Use the already installed `qwen2.5:3b` artifact only; do not pull another model. A one-token deterministic prompt with concurrency 1 and a short timeout is sufficient to distinguish a successful model load/generation from a repeat runner termination. Stop the experiment on memory exhaustion. Do not use the shared baseline Ollama endpoint for this test.

This experiment is a recommendation only. This phase did not start, stop, restart, or reconfigure services, change models, or issue generation requests.
