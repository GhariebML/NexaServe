# DEPI Scraping Report

## Objective

Build a local scraper that collects the main DEPI website content and exports clean, structured JSON that can be consumed by n8n and used for AI/RAG workflows.

## Architecture

The project uses a lightweight Python pipeline:

- Playwright for rendered-page retrieval
- BeautifulSoup for DOM parsing and text extraction
- Normalization and deduplication utilities to keep the JSON clean
- JSON validation and output generation for downstream automation

## Important finding

The DEPI website does not expose all visible content in the raw HTML shell. The real content is rendered dynamically in the browser, so the scraper must use a browser-rendered DOM rather than a simple requests-only approach.

This is why the implementation uses Playwright before parsing text and FAQ structure.

## Data coverage

The scraper targets the main pages in the project config, including:

- Home
- About DEPI
- Guidance
- DEPI
- DEPI Industry
- FAQ
- Contact Us

## Output format

The generated dataset is intended to be consumed directly by n8n and contains:

- page metadata and cleaned section text
- FAQ question/answer pairs
- document metadata when PDFs are detected
- chunk-friendly records for RAG indexing

## Validation summary

The project includes pytest validation for:

- target URL accessibility
- structured page extraction
- FAQ extraction
- Arabic content preservation
- JSON output existence

The final generated dataset already exists in `data/final/` and is ready for use by downstream workflows.
