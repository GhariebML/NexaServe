# Knowledge Freshness Report

## Fresh DEPI scrape

- Source targets are configured in `DEPI_Web_Scraper/scraper/config.py`; current official FAQ URL is `https://depi.gov.eg/content/faqs`.
- `python main.py` completed at 2026-09-27 22:20 Africa/Cairo: seven configured pages, 29 FAQ records, seven eligible page-section RAG chunks, zero discovered PDF documents.
- `faqs.json`, `depi_rag.json`, `pages.json`, `depi_data.json`, and `documents.json` were written at 22:20 Cairo. These are the newest audit files and were ingested with `python scripts/ingest_knowledge.py --scraped-only` at approximately 22:30.
- Initial scraper run failed to launch bundled Chromium and extracted no sections. The scraper was changed to use installed Microsoft Edge on Windows before falling back to packaged Chromium; the fresh run completed. The configuration still depends on a browser being installed on the machine.
- The 29 FAQ source rows are hash-matched to the current scrape; the 7 page chunks were added with source URLs. No PDFs were discovered from the targeted site in this crawl.

## Remaining freshness limits

- The scraper output does not currently record crawl timestamps per page/record or ingestion/embedding timestamps in the DB. File modification times and local logs are the available freshness evidence.
- Historical 36 KB rows lack a content hash, source URL, and per-row embedding model/version metadata. Their freshness and embedding synchronization cannot be validated.
- No official Digilians website crawl or source URL is present in this evidence set. Its 26 active KB rows remain unverified against a current official source.
- Scraping was not scheduled in the inspected run evidence; this audit proves one fresh manual crawl, not an ongoing freshness SLA.
