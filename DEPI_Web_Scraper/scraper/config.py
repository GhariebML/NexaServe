from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / 'data'
RAW_DIR = DATA_DIR / 'raw'
PROCESSED_DIR = DATA_DIR / 'processed'
FINAL_DIR = DATA_DIR / 'final'
DOCUMENTS_DIR = RAW_DIR / 'documents'

TARGET_URLS = {
    'home': 'https://depi.gov.eg/content/home',
    'about_depi': 'https://depi.gov.eg/content/aboutdepi',
    'guidance': 'https://depi.gov.eg/StaticContent/Guidance',
    'depi': 'https://depi.gov.eg/content/depi',
    'depi_industry': 'https://depi.gov.eg/content/depiindustry',
    'faq': 'https://depi.gov.eg/content/faqs',
    'contact_us': 'https://depi.gov.eg/StaticContent/ContactUs',
}

LOG_FORMAT = '%(asctime)s | %(levelname)s | %(message)s'
