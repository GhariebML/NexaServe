import json

import pytest
import requests

from scraper.config import TARGET_URLS
from scraper.scraper import DEPIDataScraper


def test_target_urls_accessible():
    for _, url in TARGET_URLS.items():
        response = requests.get(url, timeout=30, headers={'User-Agent': 'Mozilla/5.0'})
        assert response.status_code < 400, f'URL failed: {url}'
        assert response.text.strip(), f'Empty response for {url}'


def test_scraper_can_collect_pages():
    scraper = DEPIDataScraper()
    pages = scraper.scrape_pages()
    assert len(pages) >= 7
    for page in pages:
        assert page.get('url')
        assert page.get('title')
        assert page.get('sections')


def test_faq_records_are_structured():
    scraper = DEPIDataScraper()
    faqs = scraper.scrape_faqs()
    assert len(faqs) >= 1
    for faq in faqs:
        assert 'question' in faq
        assert 'answer' in faq
        assert faq['question'].strip()
        assert faq['answer'].strip()


def test_arabic_content_is_retained():
    scraper = DEPIDataScraper()
    content = scraper.scrape_pages()[0]['sections']
    combined = ' '.join(section.get('content', '') for section in content)
    arabic_letters = set('ابتثجحخدذرزسشصضطظعغفقكلمنهويأإآؤةىءئةلألاىة0123456789')
    assert any(ch in arabic_letters for ch in combined)
