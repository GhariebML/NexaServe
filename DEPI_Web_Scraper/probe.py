from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

urls = [
    'https://depi.gov.eg/content/home',
    'https://depi.gov.eg/content/aboutdepi',
    'https://depi.gov.eg/StaticContent/Guidance',
    'https://depi.gov.eg/content/depi',
    'https://depi.gov.eg/content/depiindustry',
    'https://depi.gov.eg/content/faqs',
    'https://depi.gov.eg/StaticContent/ContactUs',
]

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    for url in urls:
        page = browser.new_page(viewport={'width': 1440, 'height': 2200})
        page.goto(url, wait_until='domcontentloaded', timeout=30000)
        page.wait_for_timeout(2500)
        html = page.content()
        print('URL', url)
        print('TITLE', page.title())
        soup = BeautifulSoup(html, 'html.parser')
        print('H1s', [x.get_text(' ', strip=True) for x in soup.select('h1')[:5]])
        print('body_text_start', page.locator('body').inner_text()[:700].replace('\n', ' '))
        print('----')
        page.close()
    browser.close()
