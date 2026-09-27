from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width': 1440, 'height': 2200})
    page.goto('https://depi.gov.eg/content/faqs', wait_until='domcontentloaded', timeout=30000)
    page.wait_for_timeout(4000)
    text = page.locator('body').inner_text()
    print(text[:5000])
    print('---HTML-TAGS---')
    for selector in ['details', 'summary', '.faq', '.accordion', 'div', 'h3', 'h4', 'h5', 'h6', 'li']:
        count = page.locator(selector).count()
        if count:
            print(selector, count)
    browser.close()
