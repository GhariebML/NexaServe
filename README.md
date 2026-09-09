# Customer Service AI Automation System (Local Development Environment)

A secure, persistent, local-first development environment engineered for AI-driven customer service automation, powered by **n8n**, **Ollama**, **PostgreSQL 16**, and **Redis 7** running on Docker Compose.

---

## 1. Stack Architecture & Service Ports

| Service | Host / Container | Endpoint / URL | Authentication | Purpose |
| :--- | :--- | :--- | :--- | :--- |
| **n8n** | Container `cs-n8n` | `http://localhost:5678` | Local user authentication | Visual workflow automation, agent workflows, webhooks |
| **Ollama LLM** | Host Process (AVX-512) | `http://localhost:11434` (Docker: `http://host.docker.internal:11434`) | Open local API | High-performance local LLM (`gemma2:2b`, `llama3.1:8b`) |
| **PostgreSQL** | Container `cs-postgres` | `localhost:5432` | Role passwords in `.env` | Primary database (`n8n` and `customerservice` schemas) |
| **Redis** | Container `cs-redis` | `localhost:6379` | `REDIS_PASSWORD` in `.env` | Fast in-memory cache, message broker, rate limiter |

> [!NOTE]
> - All container ports published to the host are strictly bound to `127.0.0.1` to prevent unauthorized network exposure.
> - n8n inside Docker connects to Ollama via `http://host.docker.internal:11434`.
> - Ollama model weights reside safely on Drive E: (`E:\HostData\.ollama`) linked via NTFS Junction to protect the system drive.
> - An optional fully containerized Ollama profile is included in `docker-compose.yml` (`container-ollama`).

---

## 2. Directory Structure

```
E:\NexaServe\
├── docker-compose.yml           # Unified orchestration definition
├── .env                         # Active secret configuration (excluded from Git)
├── .env.example                 # Reference environment template
├── .gitignore                   # Ignores secrets, database dumps, and model weights
├── README.md                    # System documentation
├── infra/                       # Service configuration & initialization
│   ├── postgres/init-databases.sh # Multi-database role provisioning
│   ├── redis/redis.conf         # Redis memory cap & AOF persistence configuration
│   └── n8n/                     # Customer service intent classification workflow
├── data/                        # Persistent volumes on Drive E:
│   ├── postgres/                # PostgreSQL data files
│   ├── n8n/                     # n8n user data and encryption keys
│   └── redis/                   # Redis appendonly storage
├── backups/                     # Timestamped database dumps and manifests
├── scripts/                     # Operational automation scripts
│   ├── start-ollama.ps1         # Launches Ollama listening on 0.0.0.0:11434
│   ├── setup-wslconfig.ps1      # Caps WSL2 memory to 3.5GB to conserve host RAM
│   ├── backup.ps1               # Automated cluster & workflow backup
│   ├── restore.ps1              # System restore runner
│   ├── healthcheck.ps1          # Comprehensive 7-point health auditor
│   └── test-stack.ps1           # Complete 11-point verification test suite
└── docs/                        # Technical documentation
    ├── architecture.md          # Detailed architecture & networking specs
    └── troubleshooting.md      # Diagnostics and issue resolution guide
```

---

## 3. Quick Start & Operational Commands

### Start Entire System
```powershell
# 1. Start Ollama host service
powershell -ExecutionPolicy Bypass -File E:\NexaServe\scripts\start-ollama.ps1

# 2. Start Docker stack (Postgres, n8n, Redis)
docker compose up -d
```

### Stop Entire System
```powershell
docker compose down
```

### Restart Containers
```powershell
docker compose restart
```

### Check Container Status
```powershell
docker compose ps
```

### Stream Live Logs
```powershell
docker compose logs -f
```

---

## 4. Health Checks & Verification

### Run Automated Health Audit
```powershell
powershell -ExecutionPolicy Bypass -File E:\NexaServe\scripts\healthcheck.ps1
```

### Run Complete 11-Point Verification Suite
```powershell
powershell -ExecutionPolicy Bypass -File E:\NexaServe\scripts\test-stack.ps1
```

All 11 automated tests verify:
1. Docker Engine operational
2. PostgreSQL operational (`n8n` and `customerservice` databases exist)
3. n8n service operational (`http://localhost:5678/healthz` returns 200 OK)
4. Ollama service operational (`gemma2:2b`, `llama3.1:8b`)
5. n8n ↔ PostgreSQL connectivity (136 tables initialized)
6. n8n ↔ Ollama connectivity (`http://host.docker.internal:11434`)
7. Container restart tolerance & auto-recovery
8. Database data persistence across container restarts
9. n8n workflow storage persistence in PostgreSQL
10. Ollama model weight persistence
11. Sample customer service AI request & structured JSON validation

---

## 5. Backup & Disaster Recovery

### Create a Timestamped Backup
Dumps PostgreSQL cluster, individual application databases, and exports n8n workflows:
```powershell
powershell -ExecutionPolicy Bypass -File E:\NexaServe\scripts\backup.ps1
```
Backups are archived with a manifest in `E:\NexaServe\backups\backup_YYYYMMDD_HHMMSS\`.

### Restore from Latest Backup
```powershell
powershell -ExecutionPolicy Bypass -File E:\NexaServe\scripts\restore.ps1
```

---

## 6. Accessing n8n & Local LLM

1. Open your browser and navigate to: **[http://localhost:5678](http://localhost:5678)**
2. Set up your local admin account.
3. In any n8n HTTP Request node or AI agent node:
   - **URL**: `http://host.docker.internal:11434/api/generate` (or `/api/chat`)
   - **Model**: `gemma2:2b` (lightweight, ~20 tok/s CPU inference) or `llama3.1:8b` (tool calling)
