# NexaServe deployment bundle build report

**Bundle version:** 0.1.0 (deployment candidate)  
**Build time:** 2026-09-28 00:21 Africa/Cairo  
**Repository commit:** `72f6e684dfcb3d6f8335ee23a2097e0d667a1f17`  
**Git state:** already dirty before this task; all pre-existing modifications were preserved. This task did not commit or push.

## Repository audit and architecture

The actual root Compose file contains PostgreSQL/pgvector, n8n, Ollama, Redis, and a Node/Baileys WhatsApp bridge. Existing workflow exports provide gateway, session, intent, order, FAQ/RAG, escalation, agent bridge, logger, and output dispatch. PostgreSQL schema defines the application tables and `knowledge_base.embedding vector(768)`. The dashboard exists as FastAPI plus static frontend but was not in root Compose and had no dependency manifest or `admin_users` schema. The scraper targets seven official DEPI URLs and outputs FAQ/page JSON. There was no existing Ministry/Linux deployment package.

The bundle adds the existing dashboard as a sixth service, an optional Nginx TLS proxy, and opt-in scraper/ingestion tools. It includes only the ten selected canonical workflow JSON exports; all are inactive, and n8n credentials are omitted. The selected `02_customer_session.json` and `06_output_dispatcher.json` files use the current IDs. Linux deployment workflow copies use Docker DNS for Ollama.

## Included services and versions

| Service | Image/build | Exposure |
|---|---|---|
| PostgreSQL + pgvector | `pgvector/pgvector:pg16`, pinned registry digest | Private only |
| Redis | `redis:7-bookworm`, pinned registry digest | Private only |
| Ollama | `ollama/ollama`, pinned registry digest; local runtime observed 0.34.0 | Private only; GPU overlay |
| n8n | 2.38.1, pinned registry digest | 127.0.0.1:5678 |
| WhatsApp | Build from included Node 20/Baileys source | 127.0.0.1:8080 |
| Dashboard | Build from included FastAPI/static source | 127.0.0.1:8090 |
| Nginx | Stable Alpine, pinned registry digest, optional profile | 80/443 |
| Scraper / KB ingestion | Included source-built tools, optional `tools` profile | No host ports |

The chat model defaults to `qwen2.5:3b`; embeddings use `nomic-embed-text` at 768 dimensions. Online deployments pull these models; offline preparation exports their local Ollama model store. No model archive is present in the source bundle until the operator runs the offline preparation script.

Persistent Compose volumes are `postgres-data`, `redis-data`, `ollama-data`, `n8n-data`, `whatsapp-auth`, and `source-data`. No customer database dump, customer records, n8n credentials, WhatsApp session, private key, or local `.env` is included.

## Database, knowledge and workflow package

Fresh initialization applies the audited schema, an additive seed-free extract of the repository professional-support migration, and an additive dashboard-admin migration. It does not execute the repository's synthetic customer/agent seed data or modify customer program fields. Existing databases require backup and reviewed additive migration; bootstrap SQL runs automatically only for a new empty PostgreSQL volume.

Knowledge source package contains the DEPI scrape JSON, scraper source, and local FAQ/PDF materials. The verified scrape in the prior runtime audit contained DEPI facts; the package does **not** include a live KB dump. Digilians provenance is not established, so its material requires Ministry source review before production ingestion. Offline dashboard charts/fonts may not load because the source frontend references external CDNs.

## Deployment modes and operator commands

- **Online:** `bash scripts/deploy.sh gpu`, then `bash scripts/13_initialize_models.sh`, workflow credential setup/import, source review, and target acceptance.
- **Offline:** On an approved connected Linux builder run `bash scripts/prepare_offline_bundle.sh`. It creates an output folder containing a clean nested `deployment/` folder with image/model archives and no `.env`. Transfer only that nested folder. On target, generate fresh secrets and run `bash scripts/install_offline.sh`.
- **Health:** `bash scripts/healthcheck.sh`.
- **Infrastructure smoke:** `bash scripts/smoke.sh`.

The exact operator sequence is in `DEPLOYMENT.md`; the first Ministry-server command is `sha256sum -c MANIFEST.sha256` from the received `deployment/` folder.

## Validation actually executed

| Check | Result | Scope/limitation |
|---|---|---|
| Docker Compose base config | PASS | Parsed with `.env.example`; did not start services |
| GPU Compose overlay config | PASS | YAML/Compose syntax only; GPU not tested |
| Offline Compose overlay config | PASS | YAML/Compose syntax only; archive import not tested |
| Proxy/tools profile config | PASS | Parse only; TLS paths and proxy routes not exercised |
| Bundle smoke/config checks | PASS | Compose variants parsed; no services started |
| Secret-pattern, permission and checksum checks | PASS | Static local bundle checks; not a penetration test |
| Host port exposure policy | PASS | n8n, WhatsApp and dashboard bind to localhost; data services remain private |
| Bash syntax | PASS, 35 shell scripts | `bash -n` with Git for Windows Bash; not Ubuntu execution or ShellCheck |
| Workflow JSON | PASS, 10 exports | Parsed; verified inactive and credential-free |
| Inventory JSON | PASS | Parsed |
| Repository secret-pattern scan | PASS | Values suppressed; local `.env`, backups, data and assistant worktrees excluded |
| Runtime DB migrations | NOT RUN | No temporary or production database migration was executed |
| Docker image builds | NOT RUN | Avoided competing for local Docker memory while the existing Ollama stack is in service |
| Ubuntu/GPU/model/RAG/WhatsApp/dashboard acceptance | NOT RUN | Requires Ministry target hardware, credentials, network, source approval and WhatsApp test account |
| Offline staging/import/restore drill | NOT RUN | Requires connected Linux builder and isolated target |

The local root `scripts/secret_scan.py` was changed to remove embedded literal credential patterns; it now reports matched file/rule only. Scanned source did not match its configured high-confidence credential patterns. The ignored local `.env` and forensic backups remain secret-bearing local files and were intentionally excluded. An ignored local `infra/n8n/credentials.json` artifact is malformed and remains untouched outside the bundle; it was not copied. Protect these local artifacts and rotate values if shared outside the workstation.

## Known blockers and target-side requirements

The runtime forensic audit remains **NOT READY**: local Qwen generation was OOM-killed, prior concurrency had 503 responses, Digilians official source lineage is incomplete, and real WhatsApp outbound E2E has not been performed. This bundle does not resolve or conceal those response-quality findings. n8n workflow credentials must be created and assigned manually; model generation and GPU utilization require fresh target tests; proxy QR access requires Ministry perimeter restrictions; offline model import is same-Ollama-version dependent.

Ministry IT must supply and approve the actual Ubuntu/GPU/driver, signed package mirrors, DNS/FQDN, firewall/allowlists, TLS key/certificate, SSH/admin identities, secret vault, backup target/retention, WhatsApp test account and operator, official Digilians source materials, monitoring/support ownership, and maintenance/acceptance window. The platform owner must verify grounded Arabic and English answers, program isolation, no-answer/security cases, latency, concurrency, and recovery before public use.

## Security and remaining review

Bundle scanning does not constitute a penetration test. Review all n8n SQL expressions, Baileys account policy, dashboard RBAC/queries, image/model provenance, Nginx access restrictions, retention, and data-sovereignty controls. Do not publish a claim of production readiness until every target acceptance gate has evidence.
