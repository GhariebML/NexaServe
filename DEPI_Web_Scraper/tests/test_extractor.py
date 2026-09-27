from scraper.cleaner import is_rag_section_eligible
from scraper.extractor import clean_text, extract_sections


def test_clean_text_removes_extra_whitespace():
    text = '  مرحبا   بالعالم   \n   هذا   نص  '
    result = clean_text(text)
    assert '   ' not in result
    assert 'مرحبا بالعالم هذا نص' in result


def test_extract_sections_handles_headings_and_paragraphs():
    html = '''
    <html><body>
    <h1>عنوان رئيسي</h1>
    <p>فقرة أولى.</p>
    <h2>قسم فرعي</h2>
    <p>فقرة ثانية.</p>
    </body></html>
    '''
    sections = extract_sections(html)
    assert len(sections) >= 2
    assert any('عنوان رئيسي' in section['heading'] for section in sections)
    assert any('فقرة ثانية' in section['content'] for section in sections)


def test_rag_section_filter_removes_navigation_fragments():
    assert not is_rag_section_eligible('روابط هامة', 'وزارة الاتصالات جميع الحقوق محفوظة')
    assert not is_rag_section_eligible('التسجيل', 'تسجيل جديد')
    assert is_rag_section_eligible('قنوات التواصل', 'للاستفسارات يرجى الاتصال على الرقم 15388 يوميا')
