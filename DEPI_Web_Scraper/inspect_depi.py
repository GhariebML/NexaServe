import requests, re
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

for url in urls:
    print('\n=== URL:', url)
    try:
        resp = requests.get(url, timeout=25, headers={'User-Agent': 'Mozilla/5.0'})
        print('status', resp.status_code)
        print('ctype', resp.headers.get('content-type'))
        print('len', len(resp.text))
        text = resp.text[:2000].replace('\n', ' ')
        print(text)
        soup = BeautifulSoup(resp.text, 'html.parser')
        title = soup.title.get_text(strip=True) if soup.title else 'NO TITLE'
        print('TITLE:', title)
        print('H1:', [h.get_text(' ', strip=True) for h in soup.select('h1')[:5]])
        print('scripts', len(soup.select('script')))
        print('is_angular', 'ng-' in resp.text.lower() or 'angular' in resp.text.lower())
        print('api_markers', bool(re.search(r'api|fetch\(|axios|__NEXT_DATA__|window\.__NUXT__|application/json', resp.text, re.I)))
    except Exception as e:
        print('ERROR', type(e).__name__, e)
