import asyncio
import logging
import sys

from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)


async def launch_browser(playwright):
    """Prefer an installed Edge browser on Windows; otherwise use Playwright Chromium."""
    if sys.platform == 'win32':
        try:
            return await playwright.chromium.launch(channel='msedge', headless=True)
        except Exception as exc:
            logger.debug('Installed Edge launch failed; trying Playwright Chromium: %s', exc)
    return await playwright.chromium.launch(headless=True)


def fetch_page_html(url: str, timeout_ms: int = 30000) -> str:
    async def _fetch() -> str:
        async with async_playwright() as p:
            browser = await launch_browser(p)
            page = await browser.new_page(viewport={'width': 1440, 'height': 2200}, locale='ar-EG')
            await page.goto(url, wait_until='domcontentloaded', timeout=timeout_ms)
            await page.wait_for_timeout(2000)
            text = await page.locator('body').inner_text()
            if len(text.strip()) < 80:
                await page.wait_for_timeout(3000)
            html = await page.content()
            await page.close()
            await browser.close()
            return html

    return asyncio.run(_fetch())
