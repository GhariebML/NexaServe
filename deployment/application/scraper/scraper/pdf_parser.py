import logging
from pathlib import Path
from typing import Dict, Optional

import requests
from pypdf import PdfReader

from scraper.config import DOCUMENTS_DIR, RAW_DIR

logger = logging.getLogger(__name__)


def download_pdf(document_url: str, source_page: str, file_name: Optional[str] = None) -> Dict[str, str]:
    DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)

    if not file_name:
        file_name = Path(document_url).name or 'document.pdf'
    target_path = DOCUMENTS_DIR / file_name

    try:
        response = requests.get(document_url, timeout=30, stream=True, headers={'User-Agent': 'Mozilla/5.0'})
        response.raise_for_status()
        with target_path.open('wb') as fh:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    fh.write(chunk)
        text = extract_pdf_text(target_path)
        return {
            'document_name': file_name,
            'document_url': document_url,
            'source_page': source_page,
            'file_type': 'pdf',
            'file_path': str(target_path),
            'extracted_text': text,
        }
    except Exception as exc:
        logger.exception('Failed to download PDF %s from %s: %s', document_url, source_page, exc)
        return {
            'document_name': file_name,
            'document_url': document_url,
            'source_page': source_page,
            'file_type': 'pdf',
            'file_path': str(target_path),
            'extracted_text': '',
            'error': str(exc),
        }


def extract_pdf_text(pdf_path: Path) -> str:
    try:
        reader = PdfReader(str(pdf_path))
        chunks = []
        for page in reader.pages:
            text = page.extract_text() or ''
            chunks.append(text)
        return ' '.join(chunks).strip()
    except Exception as exc:
        logger.exception('Failed to parse PDF %s: %s', pdf_path, exc)
        return ''
