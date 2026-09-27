FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY scripts/ /app/scripts/
COPY db_config.py /app/scripts/db_config.py
COPY FAQs/ /app/FAQs/
COPY DEPI_Web_Scraper/data/final/ /app/DEPI_Web_Scraper/data/final/
CMD ["python", "/app/scripts/ingest_knowledge.py", "--scraped-only"]
