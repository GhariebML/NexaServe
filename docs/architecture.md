# Architecture & System Design Document
## Customer Service AI Automation System

This document describes the local-first infrastructure design, network topology, persistence model, and future extensibility for the Customer Service AI Automation System deployed at `E:\NexaServe`.

---

## 1. High-Level Architecture Diagram

```
+-----------------------------------------------------------------------------------+
| Host Machine: Windows 11 Pro | AMD Ryzen 5 PRO 7545U (6C/12T) | 16 GB RAM         |
| Primary Data & Workspace: E:\NexaServe (Drive E: 45+ GB Free)                     |
+-----------------------------------------------------------------------------------+
       |                                                               |
       | (Direct AVX-512 Host Process)                                 | (WSL2 Linux VM: 3.5 GB RAM Cap)
       v                                                               v
+----------------------+                               +---------------------------------+
| Native Windows Ollama|                               |    customer-service-network     |
| (AVX-512 Accelerated)|                               |         (Docker Bridge)         |
|                      |                               +---------------------------------+
| Port: 0.0.0.0:11434  | <------------------------+             |                    |
+----------------------+                          |             v                    v
       |                                          |    +------------------+ +------------------+
       v                                          |    |   cs-postgres    | |     cs-redis     |
 [NTFS Junction]                                  |    | (PostgreSQL 16)  | |(Redis 7 Bookworm)|
 E:\HostData\.ollama                              |    |                  | |                  |
       ^                                          |    | Port: 5432 (int) | | Port: 6379 (int) |
       |                                          |    | Port: 127.0.0.1: | | Port: 127.0.0.1: |
       |                                          |    |       5432 (ext) | |       6379 (ext) |
       |                                          |    +------------------+ +------------------+
       |                                          |             |                    |
       |                                          |             v                    v
       |                                          |       [Data Volume]        [Data Volume]
       |                                          |   ./data/postgres         ./data/redis
       |                                          |
       |                   +------------------------------------+
       +------------------ |               cs-n8n               |
                           |   (Workflow Core & Orchestrator)   |
                           |                                    |
                           | Host Gateway: host.docker.internal |
                           | Internal Port: 5678 (0.0.0.0)      |
                           | Host Published: 127.0.0.1:5678     |
                           +------------------------------------+
                                             |
                                             v
                                       [Data Volume]
                                        ./data/n8n
```

---

## 2. Core Infrastructure Components

### 2.1 Database Layer (`cs-postgres`)
- **Engine**: PostgreSQL 16 Alpine
- **Multi-Tenant Logical Isolation**:
  - `n8n`: Dedicated database and user (`n8n_user`) exclusively handling workflow states, node executions, and credentials. Migrated 136 core tables.
  - `customerservice`: Dedicated application database and user (`cs_app_user`) reserved for CRM customer records, conversation transcripts, order lookups, and audit trails.
  - `postgres`: Superuser account used strictly for administrative initialization and backups.
- **Storage**: Persistent mount to `E:\NexaServe\data\postgres`.
- **Healthcheck**: `pg_isready -U postgres -d postgres`.

### 2.2 Automation Engine (`cs-n8n`)
- **Engine**: n8n Community Edition (`docker.n8n.io/n8nio/n8n:latest`)
- **Persistence**: Workflows, node configurations, and file binaries are stored in `E:\NexaServe\data\n8n`.
- **Database Backend**: PostgreSQL (`DB_TYPE=postgresdb`), eliminating SQLite lock contentions and enabling scalable multi-step workflows.
- **Listen Address**: `0.0.0.0:5678` inside container, bound strictly to `127.0.0.1:5678` on the host.
- **Ollama Access**: Configured with `extra_hosts: ["host.docker.internal:host-gateway"]` enabling immediate HTTP calls to host Ollama at `http://host.docker.internal:11434`.

### 2.3 Local LLM Inference Engine (Ollama)
- **Engine**: Native Windows Ollama process with direct AMD Ryzen AVX-512 hardware instruction execution.
- **Storage & Junction**: Models reside in `E:\HostData\.ollama` mapped to `%USERPROFILE%\.ollama` via NTFS Junction (`mklink /J`), avoiding any storage pressure on Drive C:.
- **Installed Models**:
  - `gemma2:2b`: 2.6B parameter model (1.6 GB). Highly optimized for instruction-following and structured JSON output. Achieves ~20 tokens/sec on CPU inference with ~3.1s response latency.
  - `llama3.1:8b`: 8.0B parameter model (4.9 GB). Equipped with native tool-calling and completion capabilities for complex agentic workflows.
- **Container Profile**: An optional fully containerized Ollama service is configured in `docker-compose.yml` under profile `container-ollama` for environments requiring complete container isolation.

### 2.4 Caching & State Management (`cs-redis`)
- **Engine**: Redis 7 Bookworm (`redis:7-bookworm`)
- **Architecture Note**: Debian Bookworm base selected to ensure binary ABI compatibility with the WSL2 host kernel environment (resolving musl entrypoint execution issues).
- **Configuration**: Authenticated access via `REDIS_PASSWORD`, 256MB memory cap, `allkeys-lru` eviction policy, and AOF persistence in `E:\NexaServe\data\redis`.
- **Role**: Rate limiting for inbound WhatsApp webhooks, short-term conversational session caching, and background job queuing.

---

## 3. Storage Strategy & Drive Selection Rationale

During initial host diagnostics, the primary system drive (`C:`) was detected with **less than 1 GB of free space** (due to a 17.4 GB Windows pagefile and a 6.5 GB hibernation file). 
In contrast, Drive `E:` had **56+ GB of free space**.

**Engineering Actions Taken**:
1. All Docker container volumes (`./data/postgres`, `./data/n8n`, `./data/redis`) and backups (`./backups`) are strictly bound within `E:\NexaServe`.
2. Ollama model storage was moved from Drive C: to `E:\HostData\.ollama` using an NTFS directory junction, freeing 6.1 GB on Drive C:.
3. Drive C: free space is maintained above 2.0 GB, while Drive E: holds all models and database files.

---

## 4. Memory & Resource Management

- **Physical Host RAM**: 16 GB (15.28 GB visible).
- **WSL2 Resource Constraint**: Configured in `C:\Users\LAPTOPS HOUSE\.wslconfig` with:
  ```ini
  [wsl2]
  memory=3500MB
  processors=4
  swap=0
  localhostForwarding=true
  ```
  This prevents WSL2 from consuming 8+ GB of RAM, leaving 12+ GB of system memory available for Windows and the Ollama CPU inference engine.
- **Container Memory Footprint**:
  - `cs-n8n`: ~346 MB
  - `cs-postgres`: ~36 MB
  - `cs-redis`: ~4 MB
  Total container memory consumption is under 400 MB.

---

## 5. Local Networking & Security Guarantees

1. **Local-Only Port Binding**: Every service published to the host is bound strictly to `127.0.0.1` (`127.0.0.1:5678`, `127.0.0.1:5432`, `127.0.0.1:6379`). Nothing is accessible across the local area network or public internet.
2. **Internal DNS Resolution**: Containers communicate via standard Docker service names (`postgres`, `redis`) over the isolated bridge network `customer-service-network`.
3. **Least-Privilege Database Access**: The n8n engine connects using `n8n_user`, which cannot alter or read the `customerservice` application database.
4. **Secret Isolation**: All credentials, tokens, and encryption keys are stored exclusively in `.env` (excluded by `.gitignore`).

---

## 6. Extensibility: Future Component Roadmap

The infrastructure is pre-configured to receive the following modules without breaking changes:

| Component | Integration Method | Pre-configured Anchor |
| :--- | :--- | :--- |
| **WhatsApp Business API** | Webhook listener in n8n (`http://localhost:5678/webhook/...`) | Redis token rate limiting + PostgreSQL audit log |
| **Knowledge Base / RAG** | Vector embeddings in PostgreSQL (`pgvector`) | Ollama embedding endpoints (`/api/embeddings`) |
| **Human-in-the-Loop (HITL)** | n8n "Wait for Approval" node or webhook escalation | Persistent n8n execution engine + PostgreSQL task queue |
| **Local CRM Dashboard** | Web frontend connecting to `customerservice` DB | Dedicated `cs_app_user` with isolated schema |
