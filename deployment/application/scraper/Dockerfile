FROM mcr.microsoft.com/playwright/python:v1.63.0-noble
WORKDIR /app/DEPI_Web_Scraper
COPY requirements.runtime.txt /app/requirements.runtime.txt
RUN pip install --no-cache-dir --timeout 60 --retries 10 -r /app/requirements.runtime.txt
COPY main.py /app/DEPI_Web_Scraper/main.py
COPY scraper/ /app/DEPI_Web_Scraper/scraper/
# Scrape output goes to the source-data volume mounted at data/ (compose scraper), not the image.
RUN mkdir -p /app/DEPI_Web_Scraper/data/final /app/DEPI_Web_Scraper/data/raw
CMD ["python", "/app/DEPI_Web_Scraper/main.py"]
