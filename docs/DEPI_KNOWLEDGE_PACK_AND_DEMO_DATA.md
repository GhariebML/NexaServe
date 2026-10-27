# DEPI knowledge pack and dashboard demo data

## Knowledge pack (RAG)

`infra/knowledge/depi_knowledge_pack_r5.json` is the curated, customer-facing layer of the
knowledge base: 68 bilingual (AR/EN) entries tagged `DEPI Knowledge Pack R5`.

| Category | Content | Source |
|---|---|---|
| `core_*` | Eligibility, documents, admission, cost, duration, attendance, certificate, locations, registration, exams, military service, contact, DEPI Industry | depi.gov.eg FAQ / About / Guidance / Contact |
| `catalog_track` | The 7 Round 5 tracks with their job profiles, plus an all-tracks overview | `FAQs/Catal/DEPI-CATALOG-2025-R5-V1.md` |
| `catalog_profile` | 31 job profiles with the full technical study plan | same catalog |
| `catalog_industry_profile` | 6 DEPI Industry profiles | `FAQs/Catal/DEPI-Industry-CATALOG-2025-R5-V1.md` |
| `catalog_skills` | Soft skills, freelancing, entrepreneurship, English | catalog Skills track |

Rebuild and load after a catalog or FAQ change (idempotent; unchanged rows are skipped,
changed rows are re-embedded and versioned in `knowledge_base_versions`):

```bash
python scripts/kb/depi_knowledge_pack.py
python scripts/kb/load_depi_knowledge_pack.py
```

The official scraped depi.gov.eg rows stay active as the audited source records.

### Retrieval (SubWF 04B)

- The customer text, query embedding, retrieval mode and topic are bound SQL parameters
  (`$1..$4`), never interpolated. Arabic alef/yaa variants are normalised on both sides.
- Topic routing maps the question to a pack category (+35); pack entries get +8.
- Evidence gate: a row needs lexical evidence (topic match with lexical >= 6, lexical >= 18,
  or lexical >= 10 with semantic >= 27). Semantic similarity alone never answers.
- A clear match on a pack entry is answered verbatim (`verified_curated_answer`, about 1-3 s).
  Two tied entries of the same kind (e.g. SAP MM and SAP FI) are answered together. Anything
  else goes to grounded generation with qwen2.5:1.5b, which falls back to the verified answer.
- SubWF 03 routes course vocabulary to the knowledge base and short greetings to small talk
  without calling the LLM classifier.

## Dashboard demo data

`scripts/demo/seed_dashboard_demo.py` seeds 45 days of realistic DEPI activity: about 420
customers, 830 conversations, 4,400 messages (answers taken from the knowledge pack),
105 tickets with events, CSAT, agent performance and turn telemetry, plus 6 agents.

```bash
python scripts/demo/seed_dashboard_demo.py            # (re)seed; replaces earlier demo rows
python scripts/demo/seed_dashboard_demo.py --remove   # delete every demo row
```

Every row is tagged (`customers.metadata.demo`, `agents.metadata.demo`,
`audit_logs.payload.demo`, `agent_performance.notes = 'demo-seed'`, tickets via their
customer). Demo customers have no WhatsApp id and `+20 0...` phone numbers, which cannot
exist in Egypt, so nothing can be delivered to them. Take a database backup before seeding
on any environment other than a local demo.
