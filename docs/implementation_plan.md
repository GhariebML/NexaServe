# Strategic Implementation Plan
## Customer Service AI Automation Platform (Local Architecture)

This document provides the definitive architectural blueprint, engineering specifications, data models, sub-workflow topologies, and phased development roadmap for the **Customer Service AI Automation System** deployed at `E:\NexaServe`.

---

## 1. Executive Summary & Core Principles

The platform is designed to provide high-reliability customer service automation running **100% locally** with zero external cloud dependencies. It orchestrates workflow execution, local LLM inference, relational persistence, and caching through Docker Compose and native host vector hardware acceleration.

### Key Architectural Principles:
1. **Local-First & Autonomous**: All core intelligence, persistence, and workflow orchestration remain local to the machine. External channels (such as WhatsApp Business API or external CRMs) connect through clean gateway boundaries.
2. **Micro-Workflow Pattern**: Decomposing complex business logic into isolated, testable, single-responsibility sub-workflows with strict JSON contracts.
3. **Defense in Depth & Graceful Degradation**: If local LLM inference encounters memory pressure or timeouts, deterministic rule-based heuristics take over to prevent dropping customer requests.
4. **Relational Rigor & Auditability**: Every customer turn, AI classification, confidence metric, and system event is persisted with relational integrity in PostgreSQL.
5. **Least-Privilege Security**: Sensitive secrets are strictly isolated in `.env` (excluded from version control); exposed ports are bound to `127.0.0.1`.

---

## 2. High-Level Sub-Workflow Architecture

```
                             [ INCOMING CUSTOMER MESSAGE ]
                      (Webhook: POST /webhook/customer-service)
                                           |
                                           v
                       +---------------------------------------+
                       | Master 01: Gateway Dispatcher         |
                       | - Payload Validation & Sanitization   |
                       | - Rate Limiting & Latency Stopwatch   |
                       +---------------------------------------+
                                           |
                                           v
                       +---------------------------------------+
                       | SubWF 02: Customer Profile & Session  |
                       | - Find or Create Customer (Postgres)  |
                       | - Fetch Active Conversation History   |
                       +---------------------------------------+
                                           |
                                           v
                       +---------------------------------------+
                       | SubWF 03: AI Cognitive Engine         |
                       | - Prompt Engineering & Guardrails     |
                       | - Intent Classification (JSON Schema) |
                       | - Ollama Inference + Heuristic Fail-  |
                       |   safe Graceful Fallback              |
                       +---------------------------------------+
                                           |
                                           v
                       [ INTENT ROUTING SWITCH (n8n Switch Node) ]
                        /          |              |            \
                       v           v              v             v
             +--------------+ +-----------+ +------------+ +----------------+
             | SubWF 04A:   | | SubWF 04B:| | SubWF 04C: | | SubWF 04D:     |
             | Order Lookup | | Knowledge | | Human-in-  | | Conversational |
             | & Tracking   | | Base / FAQ| | the-Loop   | | General Chat   |
             +--------------+ +-----------+ +------------+ +----------------+
                        \          |              |            /
                         \         |              |           /
                          v        v              v          v
                       +---------------------------------------+
                       | SubWF 05: Audit & Conversation Logger |
                       | - Log Inbound & Outbound Turns        |
                       | - Record Execution Latency & Audit    |
                       +---------------------------------------+
                                           |
                                           v
                       [ STANDARDIZED JSON WEBHOOK RESPONSE ]
```

---

## 3. Sub-Workflow Specification & Contracts

### 3.1 Master 01 - Gateway Dispatcher (`CSWF000000000001`)
* **Role**: Primary entrypoint and orchestrator.
* **Triggers**: Webhook (`POST /webhook/customer-service`) and Manual Canvas Trigger.
* **Pipeline**:
  1. Normalizes incoming payloads (extracts `message`, `phone`, `name`, `channel`).
  2. Starts precision latency timer.
  3. Invokes `SubWF 02` (Session Manager).
  4. Invokes `SubWF 03` (AI Intent Engine).
  5. Evaluates intent and routes via Switch node.
  6. Invokes appropriate intent handler (`04A`, `04B`, `04C`, or `04D`).
  7. Invokes `SubWF 05` (Logger) to record interaction.
  8. Emits standardized JSON HTTP response to caller.

### 3.2 SubWF 02 - Customer Profile & Session Manager (`CSWF000000000002`)
* **Role**: Customer identity resolution and session management.
* **Contract**:
  * Input: `{ phone_number, full_name, email, channel }`
  * Output: `{ customer: { id, phone_number, full_name, metadata }, conversation: { id, status } }`
* **Logic**: Uses atomic `INSERT ... ON CONFLICT (phone_number) DO UPDATE` to retrieve or provision customer records and starts or resumes active session in `conversations`.

### 3.3 SubWF 03 - AI Cognitive & Intent Engine (`CSWF000000000003`)
* **Role**: Intent classification, sentiment detection, entity extraction, and confidence scoring.
* **Engine**: Local Ollama running `gemma2:2b` via AVX-512 vector instructions (`http://host.docker.internal:11434/api/generate`).
* **Output Schema**:
  ```json
  {
    "intent": "order_lookup | faq_query | human_escalation | general_support",
    "confidence": 0.85,
    "entities": { "order_number": "ORD-1001" },
    "sentiment": "positive | neutral | frustrated | angry",
    "requires_human": false,
    "direct_response": "..."
  }
  ```
* **Fault Tolerance**: Implements `onError: continueRegularOutput` with rule-based regex fallback to ensure 100% uptime even under extreme memory pressure or host restarts.

### 3.4 SubWF 04A - Order Lookup & Tracking (`CSWF000000000004`)
* **Role**: Real-time e-commerce order verification.
* **Contract**:
  * Input: `{ entities: { order_number }, customer: { phone_number } }`
  * Output: `{ status, order_found, order_data, reply }`
* **Logic**: Queries PostgreSQL `orders` table joined with `customers`. Formats friendly shipping notifications including carrier, tracking number, items, and estimated delivery dates.

### 3.5 SubWF 04B - Knowledge Base & FAQ (`CSWF000000000005`)
* **Role**: Grounded question answering for store policies.
* **Contract**:
  * Input: `{ customer_message }`
  * Output: `{ status, category, question_matched, reply }`
* **Logic**: Queries PostgreSQL `knowledge_base` using keyword array overlap (`ILIKE ANY`) and full-text substring matching across return policies, shipping times, warranties, and payment methods.

### 3.6 SubWF 04C - Human in the Loop Escalation (`CSWF000000000006`)
* **Role**: Automated escalation to human support specialists.
* **Trigger Conditions**: Customer sentiment is `angry`, intent is `human_escalation`, or `requires_human == true`.
* **Logic**: Generates a ticket in `tickets` table with priority `high`/`urgent`, sets conversation status to `handed_off`, and returns an empathetic confirmation with ticket tracking ID.

### 3.7 SubWF 05 - Conversation & Audit Logger (`CSWF000000000007`)
* **Role**: Turn persistence and system observability.
* **Logic**: Asynchronously inserts inbound customer message and outbound AI reply into `messages` table and logs latency, intent, and execution status into `audit_logs`.

### 3.8 Global Error Handler & Dead Letter Queue (`CSWF000000000008`)
* **Role**: Catches unhandled node exceptions and archives dead-letter records into `audit_logs`.

---

## 4. Database Relational Schema (`customerservice`)

The application schema consists of 7 normalized relational tables in PostgreSQL:

| Table | Purpose | Primary Keys & Indexes |
| :--- | :--- | :--- |
| **`customers`** | Customer identity & profiles | `id` (UUID, PK), index on `phone_number` (UNIQUE), `email` |
| **`conversations`** | Session state and channels | `id` (UUID, PK), index on `customer_id`, `status` |
| **`messages`** | Full turn-by-turn conversation logs | `id` (UUID, PK), index on `conversation_id`, `created_at` |
| **`orders`** | Order status, tracking & items | `id` (UUID, PK), index on `order_number` (UNIQUE), `customer_id` |
| **`knowledge_base`**| FAQ articles & policy texts | `id` (SERIAL, PK), index on `category`, `keywords` |
| **`tickets`** | Human-in-the-Loop escalation tickets | `id` (UUID, PK), index on `ticket_number` (UNIQUE), `status` |
| **`audit_logs`** | Performance metrics & event telemetry | `id` (BIGSERIAL, PK), index on `event_type`, `created_at` |

---

## 5. Verification & Testing Evidence

The complete pipeline has been verified using automated PowerShell suites:

1. **Infrastructure Health Audit** ([`scripts/healthcheck.ps1`](file:///E:/NexaServe/scripts/healthcheck.ps1)):
   * All 8 targets healthy (Docker engine, PostgreSQL, n8n, Redis, Ollama, local network bindings).
2. **11-Point System Verification Suite** ([`scripts/test-stack.ps1`](file:///E:/NexaServe/scripts/test-stack.ps1)):
   * 100% passing across container recovery, schema persistence, data survival across restarts, and LLM model integrity.
3. **End-to-End Simulation Test** ([`scripts/test-e2e-conversation.ps1`](file:///E:/NexaServe/scripts/test-e2e-conversation.ps1)):
   * **Scenario 1 (Order Lookup)**: Verified real order `ORD-1001` retrieval (shipped via DHL Express, tracking `DHL-992817263`).
   * **Scenario 2 (Policy Inquiry)**: Verified grounded 30-day refund policy retrieval from `knowledge_base`.
   * **Scenario 3 (Escalation)**: Verified urgent sentiment detection and ticket creation (`TICK-23719`).
   * **Persistence**: Verified 6 turn messages and 4 audit entries recorded in PostgreSQL.

---

## 6. Phased Implementation Roadmap

### Phase 1: Local Core Foundation (Completed)
- [x] Machine hardware diagnostics & storage optimization via NTFS junction.
- [x] Docker Compose stack deployment (PostgreSQL 16, n8n latest, Redis 7).
- [x] Dedicated application database and non-superuser role configuration.
- [x] AVX-512 hardware-accelerated local Ollama host process integration.
- [x] Modular sub-workflow suite (Workflows 01 through 08) deployed and published.
- [x] End-to-end conversation simulation verified.

### Phase 2: WhatsApp Integration & Channel Expansion
- [ ] Connect WhatsApp Business Cloud API / On-Premise Gateway to n8n webhook listener.
- [ ] Implement signature validation (`X-Hub-Signature-256`) and verification challenge (`hub.challenge`).
- [ ] Format rich WhatsApp message responses (interactive buttons, list messages, media templates).
- [ ] Redis-backed rate limiting per phone number to prevent spam or flood attacks.

### Phase 3: Advanced Retrieval-Augmented Generation (RAG)
- [ ] Enable PostgreSQL `pgvector` extension for vector embeddings.
- [ ] Embed product catalogs and detailed documentation into vector stores via Ollama embeddings endpoint (`/api/embeddings`).
- [ ] Add semantic cosine similarity search to SubWF 04B for complex queries.

### Phase 4: Local Support Agent Dashboard (Google Sheets Replacement)
- [ ] Build a lightweight local web dashboard (Next.js / Vite / Streamlit) connecting directly to `customerservice` PostgreSQL.
- [ ] Real-time view of active support tickets (`tickets` table).
- [ ] Support agent reply interface allowing human agents to intervene, respond, and resolve tickets.
- [ ] Analytics dashboard displaying resolution times, sentiment distributions, and common customer inquiries.
