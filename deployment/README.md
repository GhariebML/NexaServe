# NexaServe deployment bundle

This directory is a Linux deployment package assembled from the NexaServe repository. Start with [DEPLOYMENT.md](DEPLOYMENT.md). It targets Ubuntu 24.04 x86_64 with Docker Engine, PostgreSQL 16 + pgvector (768 dimensions), Redis 7, n8n 2.38.1, Ollama, the Baileys WhatsApp bridge, and the existing FastAPI admin dashboard.

This is a reproducible deployment candidate, **not a production-readiness certification**. The latest local runtime audit found unstable Qwen generation (OOM-killed), unverified Digilians source lineage, and no controlled outbound WhatsApp test. The Ministry operator must complete the documented acceptance checks before public launch.

No `.env`, n8n credentials, WhatsApp session, database dump, or customer records are included. Current source knowledge files are included as source material; the package does not export the live database.
