# pgvector and embeddings

`knowledge_base.embedding` is `vector(768)`; schema enables `vector` and HNSW cosine index. Repository configuration uses `nomic-embed-text`, whose target dimension is configured as 768. Verify via `scripts/smoke.sh` and sample row dimension checks after ingestion.

The packaged scraper outputs source JSON; ingestion is opt-in (`scripts/refresh_sources.sh`) and asks for review/confirmation. It may only embed after Ollama is healthy. Existing DB embedding completeness is unknown on a fresh deployment until queried. Do not regenerate the entire corpus when only changed/missing rows need work.
