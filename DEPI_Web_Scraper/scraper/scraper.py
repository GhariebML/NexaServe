import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import requests
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

from scraper.browser import fetch_page_html, launch_browser
from scraper.cleaner import deduplicate_sections, is_rag_section_eligible, normalize_faq_records
from scraper.config import FINAL_DIR, RAW_DIR, TARGET_URLS
from scraper.extractor import clean_text, extract_faqs, extract_links, extract_sections, extract_title, normalize_arabic
from scraper.pdf_parser import download_pdf
from scraper.validator import ensure_no_major_duplicates, ensure_required_fields, validate_json

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger(__name__)


class DEPIDataScraper:
    def __init__(self, base_urls=None):
        self.base_urls = base_urls or TARGET_URLS
        self.raw_dir = RAW_DIR
        self.final_dir = FINAL_DIR
        self.final_dir.mkdir(parents=True, exist_ok=True)
        self.raw_dir.mkdir(parents=True, exist_ok=True)

    def fetch_html(self, url: str, use_playwright: bool = True) -> str:
        if use_playwright:
            try:
                rendered = fetch_page_html(url)
                if '<html' in rendered.lower() and len(rendered) > 5000:
                    return rendered
            except Exception as exc:
                logger.warning('Playwright render failed for %s: %s', url, exc)

        try:
            response = requests.get(url, timeout=25, headers={'User-Agent': 'Mozilla/5.0'})
            response.raise_for_status()
            for encoding in ('utf-8', 'utf-8-sig', 'cp1256', 'latin-1'):
                try:
                    html = response.content.decode(encoding)
                    if '<html' in html.lower() and len(html) > 5000:
                        return html
                except UnicodeDecodeError:
                    continue
            html = response.text
            if html and '<html' in html.lower() and len(html) > 5000:
                return html
        except Exception as exc:
            logger.warning('HTTP fetch failed for %s: %s.', url, exc)

        raise ValueError(f'Unable to fetch HTML for {url}')

    def parse_page(self, url: str, page_type: str) -> Dict[str, Any]:
        logger.info('Opening: %s', url)
        html = self.fetch_html(url, use_playwright=True)
        soup = BeautifulSoup(html, 'html.parser')
        title = extract_title(html)
        sections = extract_sections(html)
        links = extract_links(html)
        page = {
            'page_type': page_type,
            'url': url,
            'title': title,
            'sections': deduplicate_sections(sections),
            'links': links,
            'scraped_at': datetime.now(timezone.utc).isoformat(),
        }
        page['sections'] = [
            {
                'heading': (item.get('heading') or '').strip(),
                'content': clean_text(item.get('content') or ''),
            }
            for item in page['sections']
            if (item.get('content') or '').strip()
        ]
        logger.info('Page %s extracted %s sections', url, len(page['sections']))
        return page

    def scrape_pages(self) -> List[Dict[str, Any]]:
        pages = []
        for page_type, url in self.base_urls.items():
            page = self.parse_page(url, page_type)
            if ensure_required_fields(page):
                pages.append(page)
        return pages

    def scrape_faqs(self) -> List[Dict[str, str]]:
        faq_url = self.base_urls.get('faq')
        if not faq_url:
            return []

        async def _collect() -> List[Dict[str, str]]:
            async with async_playwright() as p:
                browser = await launch_browser(p)
                page = await browser.new_page(viewport={'width': 1440, 'height': 2200}, locale='ar-EG')
                await page.goto(faq_url, wait_until='domcontentloaded', timeout=30000)
                await page.wait_for_timeout(3000)
                faq_records: List[Dict[str, str]] = []
                button_count = await page.locator('.accordion-button').count()
                for idx in range(button_count):
                    button = page.locator('.accordion-button').nth(idx)
                    question = normalize_arabic(await button.inner_text())
                    if not question:
                        continue
                    try:
                        await button.click()
                    except Exception:
                        pass
                    await page.wait_for_timeout(400)
                    body = page.locator('.accordion-body').nth(idx)
                    answer = normalize_arabic(await body.inner_text())
                    if not answer:
                        styled = body.locator('.styled-content')
                        answer = normalize_arabic(await styled.inner_text())
                    if question and answer and answer != question:
                        faq_records.append({'question': question, 'answer': answer})
                await browser.close()
                return faq_records

        faq_records = asyncio.run(_collect())

        if not faq_records:
            html = self.fetch_html(faq_url)
            faq_records = extract_faqs(html)

        faq_records = normalize_faq_records(faq_records)
        for record in faq_records:
            record['source_url'] = faq_url
        logger.info('Found %s FAQ records', len(faq_records))
        return faq_records

    def detect_documents(self, page: Dict[str, Any]) -> List[Dict[str, Any]]:
        documents = []
        for link in page.get('links', []):
            if not link:
                continue
            href = link.strip()
            if href.startswith('http') and href.lower().endswith('.pdf'):
                docs = download_pdf(href, page.get('url', 'unknown'))
                if docs and docs.get('extracted_text'):
                    documents.append(docs)
                else:
                    documents.append(docs)
        return documents

    def build_dataset(self) -> Dict[str, Any]:
        pages = self.scrape_pages()
        faqs = self.scrape_faqs()
        documents = []
        for page in pages:
            documents.extend(self.detect_documents(page))

        dataset = {
            'source': {
                'domain': 'depi.gov.eg',
                'scraped_at': datetime.now(timezone.utc).isoformat(),
            },
            'pages': pages,
            'faqs': faqs,
            'documents': documents,
        }
        return dataset

    def write_json(self, path: Path, payload: Any) -> None:
        with path.open('w', encoding='utf-8') as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
            fh.write('\n')

    def build_rag_records(self, dataset: Dict[str, Any]) -> List[Dict[str, Any]]:
        records = []
        for idx, page in enumerate(dataset.get('pages', []), start=1):
            for section in page.get('sections', []):
                heading = (section.get('heading') or '').strip()
                content = (section.get('content') or '').strip()
                if not is_rag_section_eligible(heading, content):
                    continue
                chunk = f"{heading}: {content}" if heading else content
                records.append({
                    'id': f"depi_page_{idx:03d}_{len(records)+1:03d}",
                    'content': chunk,
                    'metadata': {
                        'source_url': page.get('url'),
                        'page_type': page.get('page_type'),
                        'section': heading,
                        'language': 'ar',
                    },
                })
        for idx, faq in enumerate(dataset.get('faqs', []), start=1):
            content = f"Question: {faq.get('question')} Answer: {faq.get('answer')}"
            records.append({
                'id': f"depi_faq_{idx:03d}",
                'content': content,
                'metadata': {
                    'source_url': faq.get('source_url'),
                    'page_type': 'faq',
                    'language': 'ar',
                },
            })
        return records

    def save_outputs(self) -> Dict[str, Any]:
        dataset = self.build_dataset()
        self.write_json(self.final_dir / 'depi_data.json', dataset)
        self.write_json(self.final_dir / 'pages.json', dataset['pages'])
        self.write_json(self.final_dir / 'faqs.json', dataset['faqs'])
        self.write_json(self.final_dir / 'documents.json', dataset['documents'])
        rag_records = self.build_rag_records(dataset)
        self.write_json(self.final_dir / 'depi_rag.json', rag_records)

        for path in [self.final_dir / 'depi_data.json', self.final_dir / 'depi_rag.json', self.final_dir / 'pages.json', self.final_dir / 'faqs.json', self.final_dir / 'documents.json']:
            assert validate_json(path), f'Invalid JSON: {path}'
        assert ensure_no_major_duplicates(dataset['pages'])
        assert ensure_no_major_duplicates(dataset['faqs'])
        return dataset


def main() -> None:
    scraper = DEPIDataScraper()
    dataset = scraper.save_outputs()
    logger.info('Scraping completed. Pages: %s, FAQs: %s, Documents: %s', len(dataset['pages']), len(dataset['faqs']), len(dataset['documents']))


if __name__ == '__main__':
    main()
