import re
from typing import Any, Dict, List

from bs4 import BeautifulSoup


def clean_text(value: str) -> str:
    if value is None:
        return ''
    text = re.sub(r'\s+', ' ', value, flags=re.UNICODE)
    return text.strip()


def normalize_arabic(value: str) -> str:
    return clean_text(value).replace('\u200f', '').replace('\u200e', '')


def extract_title(html: str) -> str:
    soup = BeautifulSoup(html, 'html.parser')
    title = soup.title.get_text(' ', strip=True) if soup.title else ''
    if title:
        return clean_text(title)
    h1 = soup.select_one('h1')
    return clean_text(h1.get_text(' ', strip=True)) if h1 else 'Untitled'


def extract_sections(html: str) -> List[Dict[str, str]]:
    soup = BeautifulSoup(html, 'html.parser')
    sections: List[Dict[str, str]] = []
    body = soup.body or soup

    current_heading = ''
    current_content: List[str] = []

    for tag in body.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'li']):
        text = normalize_arabic(tag.get_text(' ', strip=True))
        if not text:
            continue

        if tag.name in {'h1', 'h2', 'h3', 'h4', 'h5', 'h6'}:
            if current_heading or current_content:
                section_text = clean_text(' '.join(current_content))
                if current_heading or section_text:
                    sections.append({'heading': normalize_arabic(current_heading), 'content': section_text})
            current_heading = text
            current_content = []
        else:
            if current_heading:
                current_content.append(text)

    if current_heading or current_content:
        sections.append({'heading': normalize_arabic(current_heading), 'content': clean_text(' '.join(current_content))})

    if not sections:
        body_text = normalize_arabic(body.get_text(' ', strip=True))
        if body_text:
            sections.append({'heading': 'Main Content', 'content': body_text})

    deduped: List[Dict[str, str]] = []
    seen = set()
    for section in sections:
        key = (section.get('heading', ''), section.get('content', ''))
        if len(section.get('content', '')) < 3:
            continue
        if key not in seen:
            seen.add(key)
            deduped.append(section)
    return deduped


def extract_links(html: str) -> List[str]:
    soup = BeautifulSoup(html, 'html.parser')
    links = []
    for link in soup.select('a[href]'):
        href = link.get('href', '').strip()
        if href and href not in links:
            links.append(href)
    return links


def extract_faqs(html: str) -> List[Dict[str, str]]:
    soup = BeautifulSoup(html, 'html.parser')
    faqs: List[Dict[str, str]] = []

    for detail in soup.select('details, .faq, .accordion-item, .accordion, .faq-item, .question-item'):
        q = detail.select_one('summary, .question, h3, h4, h5, .faq-question')
        a = detail.select_one('.answer, .faq-answer, p, .content')
        if q and a:
            question = normalize_arabic(q.get_text(' ', strip=True))
            answer = normalize_arabic(a.get_text(' ', strip=True))
            if question and answer:
                faqs.append({'question': question, 'answer': answer})

    if not faqs:
        headings = soup.find_all(['h3', 'h4', 'h5'])
        for heading in headings:
            text = normalize_arabic(heading.get_text(' ', strip=True))
            if not text:
                continue
            if re.search(r'\?|\s+[سش].*\?', text, flags=re.UNICODE):
                next_node = heading.find_next_sibling()
                while next_node is not None and next_node.name not in {'h3', 'h4', 'h5'}:
                    content = normalize_arabic(next_node.get_text(' ', strip=True))
                    if content:
                        faqs.append({'question': text, 'answer': content})
                        break
                    next_node = next_node.find_next_sibling()

    # generic fallback
    if not faqs:
        for entry in soup.select('li, div, p'):
            text = normalize_arabic(entry.get_text(' ', strip=True))
            if not text:
                continue
            if len(text) > 60 and '?' in text:
                parts = re.split(r'\s*\?\s*', text, maxsplit=1)
                if len(parts) == 2:
                    q = clean_text(parts[0]) + '?'
                    a = clean_text(parts[1])
                    if q and a:
                        faqs.append({'question': q, 'answer': a})

    deduped = []
    seen = set()
    for faq in faqs:
        key = (faq['question'], faq['answer'])
        if key not in seen:
            seen.add(key)
            deduped.append(faq)
    return deduped

