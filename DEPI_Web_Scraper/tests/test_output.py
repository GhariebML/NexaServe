import json
from pathlib import Path

from scraper.config import FINAL_DIR


def test_final_json_files_exist():
    expected = [
        FINAL_DIR / 'depi_data.json',
        FINAL_DIR / 'depi_rag.json',
        FINAL_DIR / 'pages.json',
        FINAL_DIR / 'faqs.json',
        FINAL_DIR / 'documents.json',
    ]
    for path in expected:
        assert path.exists(), f'Missing output file: {path}'


def test_json_files_are_valid():
    for path in [
        FINAL_DIR / 'depi_data.json',
        FINAL_DIR / 'depi_rag.json',
        FINAL_DIR / 'pages.json',
        FINAL_DIR / 'faqs.json',
        FINAL_DIR / 'documents.json',
    ]:
        with path.open('r', encoding='utf-8') as fh:
            json.load(fh)
