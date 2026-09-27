from collections import OrderedDict
from typing import Dict, List


RAG_NAVIGATION_HEADINGS = {
    'DEPI',
    'برامج المبادرة',
    'التسجيل',
    'الوسائط المتعددة',
    'للمساعدة',
}


def is_rag_section_eligible(heading: str, content: str) -> bool:
    heading = (heading or '').strip()
    content = (content or '').strip()
    if not content or 'جميع الحقوق محفوظة' in content:
        return False
    if heading == 'روابط هامة':
        return False
    if heading in RAG_NAVIGATION_HEADINGS and len(content) < 80:
        return False
    return len(content) >= 40


def deduplicate_sections(sections: List[Dict[str, str]]) -> List[Dict[str, str]]:
    deduped = []
    seen = set()
    for section in sections:
        key = (section.get('heading', ''), section.get('content', ''))
        if key not in seen:
            seen.add(key)
            deduped.append(section)
    return deduped


def normalize_page_record(record: Dict[str, object]) -> Dict[str, object]:
    record = OrderedDict(record)
    if 'sections' in record:
        record['sections'] = deduplicate_sections(record['sections'])
    return record


def normalize_faq_records(faqs: List[Dict[str, str]]) -> List[Dict[str, str]]:
    deduped = []
    seen = set()
    for faq in faqs:
        q = (faq.get('question') or '').strip()
        a = (faq.get('answer') or '').strip()
        if not q or not a:
            continue
        key = (q, a)
        if key not in seen:
            seen.add(key)
            deduped.append({'question': q, 'answer': a})
    return deduped
