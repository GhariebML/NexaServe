# Isolated Candidate Runtime Readiness

**Status: PREPARED ON PAPER / NOT DEPLOYED.** No candidate services were started and no network traffic was routed.

## Existing candidate configuration is not isolated

`docker-compose.candidate.yml` is unsuitable for acceptance testing as currently written. It points at `test_uat_candidate`, resolves `postgres`, `redis`, `n8n`, `ollama`, and `whatsapp` on the shared `cs-network`, calls shared n8n webhooks, and exposes the dashboard on `192.168.1.3:8091`. It therefore cannot demonstrate a separate candidate execution path and includes a WhatsApp health dependency.

The staged candidate workflow exports are not independently deployable as a complete stack: only session, intent, and FAQ workflow files are present; live Postgres credential binding has not been verified; and the gateway chain does not have a separately provisioned candidate endpoint or credentials. The local Ollama generation path is currently failing.

## Candidate configuration requirements

A future isolated local runtime should:

1. Run candidate n8n and dashboard under separate container names, with separate internal n8n state and a separately generated n8n encryption key/API key. Bind any UI/API ports to `127.0.0.1` only.
2. Use `nexaserve_final` as the read target only after a dedicated least-privilege candidate Postgres credential is created and verified. Do not reuse the active n8n credential. No ingestion or database writes are authorized by this readiness work.
3. Use an explicitly provisioned candidate Ollama runtime and only configure generation after a controlled resource check succeeds. The embedding model and dimensions must be checked separately.
4. Keep WhatsApp endpoints, webhook URLs, credentials, and outbound messaging absent from the candidate configuration.
5. Keep candidate workflows inactive in the shared n8n instance. Import only into the isolated n8n after the full workflow chain and its credential references have been reviewed.
6. Record pre/post snapshots for `customerservice`, active workflow IDs/statuses, and WhatsApp before any future candidate execution that could affect shared components.

A separate n8n container on the current Docker network would still have network reachability to shared services. Therefore, candidate launch should wait until the network policy is explicitly constrained or a dedicated network and candidate dependencies are available. Static configuration alone does not meet runtime isolation.

## Readiness decision

**Not ready for candidate chats.** Preconditions missing: validated source approvals (current approved count is zero), a healthy isolated generation endpoint, a complete isolated workflow chain, and independently verified read-only database credential binding. No runtime candidate request or knowledge import was attempted.
