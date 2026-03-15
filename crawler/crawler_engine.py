from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import asyncio

class WebCrawler:
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.context = None

    async def start(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=True)
        self.context = await self.browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        )

    async def fetch_page(self, url: str) -> dict:
        """
        Crawls a webpage and returns both raw HTML and cleaned text.
        """
        if not self.context:
            await self.start()
            
        page = await self.context.new_page()
        try:
            await page.goto(url, wait_until="networkidle", timeout=60000)
            html = await page.content()
            
            # Use BeautifulSoup for text extraction
            soup = BeautifulSoup(html, 'html.parser')
            
            # Basic cleaning
            for script_or_style in soup(["script", "style", "nav", "footer", "header"]):
                script_or_style.decompose()
            
            text = soup.get_text(separator='\n')
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            cleaned_text = '\n'.join(lines)
            
            return {
                "html": html,
                "text": cleaned_text
            }
        finally:
            await page.close()

    async def close(self):
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
