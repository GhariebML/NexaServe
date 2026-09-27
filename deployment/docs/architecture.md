# Runtime architecture

The package deploys six current runtime services: PostgreSQL 16 + pgvector, Redis 7, Ollama, n8n 2.38.1, Baileys WhatsApp bridge, and the repository's FastAPI dashboard. All share a private Docker bridge network; only n8n, QR bridge, and dashboard bind to host loopback. Optional Nginx terminates TLS; optional tools run scraper and ingestion.

WhatsApp → bridge → `POST /webhook/customer-service` → Master workflow → Session → Intent → 04A/04B/04C → Output → Logger → bridge/WhatsApp. n8n calls Ollama over Docker DNS (`cs-ollama:11434`) and PostgreSQL via n8n credential. RAG data flows from DEPI official pages/FAQ → JSON scrape → review → idempotent ingestion → `knowledge_base.embedding vector(768)` → program-filtered retrieval → generation/guardrail.

This is architecture derived from the actual Compose and workflow exports, not a claim that every route has passed E2E. See root-level `docs/live_runtime_architecture.md` and the runtime readiness report for observed execution evidence and known failures.
