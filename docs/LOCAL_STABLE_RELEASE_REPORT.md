# NexaServe Local Stable Release Report

**Audit date:** 2026-10-06 (Africa/Cairo)  
**Scope:** This Windows development machine and repository only. No Ministry server, production credentials, public exposure, GitHub push, or production WhatsApp account was used.  
**Decision:** **LOCAL STABLE RELEASE CANDIDATE — BLOCKED**

## Executive decision

This checkout is not a verified local release candidate. Docker Desktop's Linux engine did not start, so no Compose service was running or reachable during this audit. A previous synthetic local webhook request returned HTTP 500, and the available n8n log evidence points to an `isBenefits` JavaScript error plus legacy workflows competing for the `customer-service` webhook path. Source fixes and unit tests exist, but they are not deployed to a currently running stack. A successful native Windows Ollama request does not establish that the NexaServe containerized AI path works.

No local release commit or tag was created because critical acceptance gates failed. Existing workspace changes and local data were preserved.

## 1. Local environment

| Item | Evidence | Result |
|---|---|---|
| Repository | `E:\NexaServe` | Inspected |
| Branch / commit | `master`, `a7e6a9b7912553021f2055d150e5acb5897a62d2` | Identified |
| Git worktree | `git status --short` | Already modified before release freeze; see section 26 |
| Docker CLI / Compose | Docker CLI 29.7.2, Compose v5.5.0 | Installed |
| Docker Engine | `docker version` cannot open `npipe:////./pipe/dockerDesktopLinuxEngine` | **BLOCKED** |
| WSL | WslService running; WSL 2.6.3; `docker-desktop` distro was stopped during discovery | Engine unavailable |
| Docker Desktop | App/backend processes exist; backend startup log reports it cannot access/rename `sailor-ingest.sock` and `.stale` | **BLOCKED** |
| Native Windows Ollama | `127.0.0.1:11434/api/tags` returned HTTP 200 | Responding, but not the Compose AI path |
| Current runtime containers | `docker ps` cannot query the daemon | Unknown; not verifiable |
| Ministry/remote environment | No remote connection attempted | Out of scope |

The socket entries were Windows reparse points. Attempts to inspect/move them failed with Windows error 1920. Docker data, WSL registrations, volumes, and databases were not reset or deleted. Docker Desktop was restarted once; the same engine failure remained. No further destructive recovery was attempted.

## 2. Ports and services

A TCP check from Windows found ports **5678, 8080, 8090, 5432, 6379, and 11435 closed**. Port **11434** was listening for native Windows Ollama. Consequently:

- n8n, WhatsApp gateway, Dashboard, PostgreSQL, Redis, and containerized Ollama host access were unavailable.
- No Docker-internal service-to-service connectivity could be proven.
- The requested health URLs and Dashboard login/data views could not be checked against a running stack.
- “Closed” describes the checked local TCP listeners at audit time, not whether Compose configuration intends to publish each port.

## 3. Docker and reproducibility

`docker compose config --quiet` exited 0 for the repository Compose configuration. The deployment bundle also passed Compose parsing with `deployment/.env.example`. This validates syntax and variable interpolation only; it does not validate image builds, mounts, container startup, health, or network connectivity.

The local Ollama port collision/routing defect was corrected in source: root Compose now defaults host Ollama publication to `127.0.0.1:11435`, while n8n and WhatsApp use the Compose service at `http://ollama:11434`. Canonical workflow exports were updated to the Compose service DNS name. This avoids routing those nodes to the host-gateway alias/native Ollama and leaves native Ollama's existing port 11434 untouched. Compose parsing passed after these edits. The source change is **not runtime-verified** because Docker is unavailable.

No clean checkout/image build was performed: the Engine was not available. Repository reproducibility therefore remains unproven.

## 4. Ollama and models

The **native Windows** Ollama service responded at `127.0.0.1:11434`. Its model list included `qwen2.5:3b`, `llama3.1:8b`, and `gemma2:2b`; `nomic-embed-text` was absent. The qwen model reported embedding length 2048 in its model metadata, which is not evidence that the project embedding model is installed or that stored pgvector dimensions match it.

Two short native Windows `qwen2.5:3b` generation calls completed (one in 5.916 seconds with a deliberately short token cap; another returned the exact `LOCAL_MODEL_OK` sentinel in 3.2 seconds). These establish only that native local generation can respond. The first answer was truncated by the test token cap. Native `POST /api/embed` for `nomic-embed-text` returned HTTP 404 because the model was unavailable. The Compose/containerized Ollama generation and embedding paths were not run. GPU usage and VRAM behavior were not verified (`nvidia-smi` was unavailable on PATH).

**Result:** Containerized AI / embeddings **BLOCKED**; native generation **PARTIAL PASS**; embedding model **FAIL / MISSING**; GPU **UNVERIFIED**.

## 5. PostgreSQL, Redis, knowledge, and memory

Neither PostgreSQL nor Redis was reachable on its checked local port. No SQL was run, no migration applied, and no database was reset. Current database/schema health, pgvector extensions, active KB row count, embedding coverage, conversation/memory persistence, and database credentials in use are **UNVERIFIED** for this audit. Historical counts or earlier reports are not treated as current evidence.

## 6. n8n and workflows

Static inspection found 20 workflow JSON exports in `infra/n8n/workflows`. There are three exported owners of the `customer-service` webhook path (`01_gateway_dispatcher.json`, `Master_Workflow.json`, and `Master_Workflow_Enterprise.json`); legacy Master exports also conflict on `agent-response`. The deployment bundle has a canonical gateway owner and canonical modular agent-response owner. Import/publish helpers were adjusted to exclude `Master_*` legacy exports and publish only canonical ingress workflow `CSWF000000000001`.

Runtime evidence available from the earlier controlled local run:

- `POST http://127.0.0.1:5678/webhook/customer-service` with synthetic, non-PII content returned HTTP 500 and `{"message":"Error in workflow"}`.
- n8n logs reported `ReferenceError: isBenefits is not defined`, then webhook failure before a response was sent.
- n8n logs also reported activation failure for `MASTER_001` and `MASTER_PROFESSIONAL_001` because the `customer-service` path was already taken.
- The user denied access to execution 6195 in the browser. That execution was not accessed through another channel.

The canonical 04B workflow source now declares topic matchers at a shared scope and recognizes Arabic plural scholarship terms. Direct JavaScript node tests covered DEPI scholarship, Digilians eligibility, and ambiguous Arabic input. However, current n8n activation state, activeVersionId, credentials, actual node execution, database calls, Ollama calls, and post-fix webhook replay are **UNVERIFIED** because Docker is down. No claim of a repaired live workflow is made.

## 7. Dashboard integration

The Dashboard backend/frontend code and runtime observability tests exist in the repository. `tests/test_dashboard_runtime_observability.py` passed (6 tests), including a check that a disconnected WhatsApp bridge is not reported as fully healthy. The Dashboard service was not running on port 8090, so login, authorization, real PostgreSQL metrics, messages, tickets/HITL, workflow data, or customer interaction visibility were not checked end to end.

**Result:** Dashboard source/unit test **PARTIAL PASS**; Dashboard-to-live-database integration **UNVERIFIED**.

## 8. RAG, response quality, memory, and program isolation

The program detector source tests passed for three focused cases, but retrieval against the actual local database, source provenance, embedding consistency, top-k relevance, context construction, model prompt, validator, and customer answer were not tested end to end. There is no current evidence that official FAQ/scraped records are loaded or retrieved by the running system.

Memory continuity, DEPI/Digilians zero-leakage, ambiguous-question clarification, unknown-answer fallback, and persistence after restart were not tested in this run because the stack was unavailable. No RAG quality or isolation pass is claimed.

## 9. WhatsApp gateway

The gateway source now accepts a reply only from successful workflow response fields (`response`, `final_reply`, or `reply`) and does not forward a generic HTTP 500 `message` as a customer answer. Simulation reports failure/fallback explicitly. `tests/test_whatsapp_error_response.mjs` passed all 4 tests, and `node --check` passed for gateway JavaScript files.

No WhatsApp container was running at audit time. No test number was supplied, no account was paired, and no real delivery was attempted. Prior local logs had intermittent DNS failures for `web.whatsapp.com`. Local inbound/outbound gateway behavior, retry, timeout, fallback delivery, and correlated logging are therefore **UNVERIFIED** at runtime.

## 10. Error handling and security

The code-level WhatsApp response-envelope test covers successful response selection, rejection of error envelopes, malformed bodies, and two program detection inputs. Controlled failure tests for PostgreSQL, Redis, Ollama, timeouts, inactive subworkflow, and recovery were not run.

The repository secret scanner initially flagged `deployment/.env.example` because its whitespace matcher could cross a newline after an intentionally empty `N8N_API_KEY=` assignment. The matcher now accepts horizontal whitespace only; rerunning `python scripts/secret_scan.py` passed and reported no configured credential patterns in scanned source files. The scan suppresses matched values and excludes local `.env`, backups, and data. The live security regression suite was not run because it sends prompts to the unavailable n8n webhook. No secrets were printed or copied into this report.

## 11. Tests actually run

| Check | Result | Evidence / limit |
|---|---|---|
| Root Compose config parse | PASS | `docker compose config --quiet`, exit 0; no daemon required |
| Deployment Compose config parse | PASS | Compose config with `deployment/.env.example`, exit 0; no daemon required |
| Dashboard runtime observability unit tests | PASS | 6 passed |
| WhatsApp error-response and program detector tests | PASS | Node test runner: 4 passed |
| WhatsApp JavaScript syntax | PASS | `node --check` for `server.js` and `n8n-response.js` |
| Workflow JSON connection target static scan | PASS | All exported connection targets resolved in static workflow exports |
| Synthetic customer webhook | FAIL | HTTP 500, `Error in workflow`; logs identified `isBenefits` reference error |
| Native qwen generation | PARTIAL PASS | Two short responses; one deliberately truncated |
| Native nomic embedding | FAIL | HTTP 404; model missing |
| Docker Engine | FAIL | Linux engine named pipe unavailable |
| Secret scan | PASS | Scanner regex fixed to remain on one assignment line; rerun found no configured credential patterns |
| Infrastructure / memory / isolation / WhatsApp resilience / full security suites | NOT RUN | Require the unavailable running stack; no partial result reported as pass |
| Full E2E and restart/persistence | NOT RUN | Docker runtime unavailable |
| Clean image build | NOT RUN | Docker Engine unavailable |

## 12. Source fixes and runtime status

| Issue | Source code fixed | Local runtime fixed | Automated check |
|---|---:|---:|---|
| 04B topic matcher scope and Arabic scholarship plural matching | Yes | No; workflow export not imported | Focused direct-node coverage in 4-test Node suite passed |
| Duplicate legacy workflow import/publish behavior | Yes | Unverified; no live n8n | Static export inventory only |
| WhatsApp forwarding generic workflow error as answer | Yes | No; gateway container not rebuilt/restarted | 4 Node tests passed |
| Dashboard treats HTTP-200 disconnected WhatsApp as healthy | Yes | No live dashboard | 6 Python tests passed |
| n8n/WhatsApp target host Ollama instead of Compose service; host port collision | Yes in root Compose/workflow exports | No; Docker unavailable | Compose syntax passed; no container connectivity test |
| Docker Desktop `sailor-ingest.sock` access failure | No source fix; Windows/Docker Desktop issue | No | Relaunch reproduced failure |
| Security scanner newline false positive | Yes; whitespace matching now stays on the assignment line | N/A | Secret scan passed after fix |

## 13. Existing changes and release freeze

The checkout was not clean. Existing modifications include `README.md`, `dashboard/frontend/app.js`, and six tracked test-result JSON files, in addition to stabilization source edits listed above. These were preserved; the test-result JSON files were not regenerated in this audit. No unrelated cleanup was performed. `git diff --check` reported a trailing blank line in the deployment Compose file; that extra blank line was removed. A clean final diff review remains necessary after the runtime blockers are resolved.

No commit or local tag was created because the user's release-freeze instructions require the critical test gates to pass first. Nothing was pushed.

## 14. Remaining blockers

1. Restore Docker Desktop Engine without resetting WSL, unregistering distros, removing volumes, or deleting data; investigate the inaccessible `sailor-ingest.sock` reparse points using a supported Docker Desktop repair path.
2. Start the official local Compose stack and prove health, port publication, and container-to-container Postgres/Redis/Ollama connectivity.
3. Rebuild/redeploy source workflow and gateway changes locally, resolve canonical active workflow ownership, then run a new synthetic webhook and inspect its execution through the authorized UI path.
4. Install/load the configured embedding model in the **containerized** Ollama and verify embedding dimensions against active KB rows; inspect and repair only affected records if required.
5. Run all repository regression suites, RAG/source replay, program isolation, memory, safe WhatsApp simulation/resilience, dashboard-to-DB journey, error injection/recovery, restart persistence, and repeated latency tests.
6. Build the deployment images from clean source and confirm no manual/out-of-repository state is needed.
7. Review all changes, preserve user edits, rerun diff checks, and create a local-only release commit/tag only after all acceptance gates pass.

## Final release gate

**LOCAL STABLE RELEASE CANDIDATE — BLOCKED**

This status is based on actual Docker Engine unavailability, a previously reproduced local webhook HTTP 500, missing native embedding model (and unverified container model), no live database/dashboard access, and unrun integration/regression gates. The repository has useful source-level fixes and passing focused tests, but the complete local system has not been proven stable, integrated, persistent, or reproducible.
