# Candidate Isolation Matrix and Proposed Architecture

**Status: design only; nothing deployed or reconfigured.**

## Current coupling matrix

| Component | Current candidate path | Shared baseline resource | Isolation assessment / risk |
|---|---|---|---|
| Dashboard | `dashboard-candidate` in `docker-compose.candidate.yml`; published on `192.168.1.3:8091` | Shared `cs-network`; configured to reach `postgres`, `redis`, `n8n`, `ollama`, and `whatsapp` | Not isolated. Config names `test_uat_candidate`, but dependencies and workflow endpoint resolve to baseline services. LAN bind is broader than necessary. |
| Knowledge database | `test_uat_candidate` | Existing `cs-postgres` and shared data volume | Logical database separation only; same PostgreSQL process, disk, backups, and resource pool. No candidate-only role/credential verified. |
| n8n workflows | Dashboard invokes `http://n8n:5678` | Baseline `cs-n8n`, its workflow/credential store and encryption key | Not isolated. Candidate traffic could execute shared workflows; imported workflow state would share baseline n8n. |
| n8n admin/API | Internal service name `n8n:5678`; baseline host port binds loopback in main compose | Baseline n8n service and credential store | Candidate points at baseline API. Existing loopback host binding is not public, but candidate should have no route to it. |
| PostgreSQL | Candidate compose uses `postgres` | Baseline PostgreSQL instance, roles, disks and service capacity | Shared infrastructure. Do not treat database-name separation as full runtime isolation. |
| Redis | Candidate compose uses `redis` | Baseline Redis service and capacity | The inspected dashboard code uses Redis for health/readiness probes; no Redis-backed dashboard session storage was found. Still avoid the shared service to prevent dependency and resource coupling. |
| Ollama/model cache | `http://ollama:11434`, default `qwen2.5:3b` | Baseline `cs-ollama`, model files and compute/memory capacity | Directly shared; model failure already observed. Concurrent candidate traffic risks baseline resource stability. |
| WhatsApp | Candidate sets `WHATSAPP_HEALTH_URL=http://whatsapp:8080/health` | Baseline `cs-whatsapp`, auth/session volume and processing path | Candidate has reachability and health dependency. The dashboard backend also probes its configured WhatsApp health URL; candidate build/config must disable this probe or keep it on candidate-local loopback with no baseline network route. No candidate message dispatcher. |
| Network | Candidate declares `cs-network` | Existing `customer-service-network` aliases include baseline services | Shared service discovery allows accidental calls to baseline. |
| External ports | Candidate dashboard `192.168.1.3:8091` | Host LAN | Wider than needed for local acceptance. Infrastructure/admin ports must not be published. |

## Proposed reversible candidate architecture

1. **Separate Compose project and private network.** Use unique `candidate-*` service/container/volume names and a dedicated user-defined network. Do not attach any candidate container to `customer-service-network`. No network route or alias to baseline services. Keep the candidate network internal where outbound access is unnecessary.
2. **Dedicated PostgreSQL instance and data volume.** Create candidate-only database service/storage for both `candidate_n8n` metadata and `candidate_knowledge`, with separate roles: n8n metadata role, dashboard read-only retrieval role, and a disabled/not-provisioned ingestion role until separately authorized. Do not mount or reuse baseline `data/postgres`; candidate DB may be discarded after preserving review artifacts.
3. **Dedicated n8n.** Use a separate n8n instance, metadata database, volume, encryption key, user/JWT secret, and API key. Import reviewed candidate-only workflow files there, with dedicated candidate Postgres credential. No baseline credentials or workflow IDs. Publish no n8n admin/API port; dashboard and test harness call its internal webhook. Any later local admin access must be a separately approved loopback-only temporary mapping with authentication.
4. **Candidate dashboard/chat path.** Bind only dashboard/test UI to `127.0.0.1`. Point it only to candidate n8n's internal webhook and candidate read-only knowledge role. Disable WhatsApp health probing in a candidate-specific dashboard build/configuration (the current backend probes the configured URL); exclude WhatsApp bridge URLs, sender credentials, and outbound messaging nodes. Start from direct browser/test-harness traffic.
5. **Dedicated cache/session store.** Use a candidate-only Redis and namespace/credentials, or disable Redis for a single-process candidate if the dashboard supports it. Never reuse baseline session/cache keys or sessions.
6. **Intentional model isolation.** Use a separately provisioned candidate Ollama container, model storage volume, and endpoint on the candidate network. Do not mount the baseline `data/ollama` volume or contact `cs-ollama`. Reuse the same installed model artifact only after its license/artifact identity and local disk availability are checked; no model pull in this phase. Candidate container isolation does **not** isolate host RAM/CPU. The current Docker VM has a 3.251 GiB memory limit and Windows had about 1.88 GiB free in the observed snapshot, so candidate inference must wait for a measured headroom window or a separate host. Stop on memory pressure.
7. **No public infrastructure ports.** PostgreSQL, Redis, Ollama, and n8n have no host port mappings. Only candidate dashboard/test UI may bind to loopback. Avoid LAN/public binding and avoid publishing n8n administration.
8. **Rollback.** Candidate-only volumes and project name make teardown reversible; first preserve test traces and reviewed artifacts, then remove only candidate project resources. Baseline data and services remain untouched.

## Residual coupling and safeguards

Under this design, candidate databases, workflows, credentials, sessions, model files, network aliases, and WhatsApp state are separate. The remaining coupling is the Windows host/Docker Desktop CPU, RAM, disk I/O, and available space. Mitigate with a measured preflight snapshot, low-concurrency test, memory stop threshold, a bounded test window, and use of a separate machine if host headroom is inadequate. A separate database inside baseline PostgreSQL or shared Ollama/Redis is not an acceptable substitute for this design.

## Readiness status

**Not ready to launch.** Source approvals remain zero; generation failure has no confirmed cause; dedicated compose design/credentials/workflow package are not deployed; and host resource headroom is inadequate/unverified for a second model runtime. This document proposes no configuration edits to the existing Compose files.
