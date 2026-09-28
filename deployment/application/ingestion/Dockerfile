FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
# scripts/ holds ingest_knowledge.py and the db_config.py module it imports.
COPY scripts/ /app/scripts/
COPY FAQs/ /app/FAQs/
# Scraper output is runtime data from the source-data volume (compose kb-ingest), not build input.
RUN mkdir -p /app/DEPI_Web_Scraper/data/final
CMD ["python", "/app/scripts/ingest_knowledge.py", "--scraped-only"]
