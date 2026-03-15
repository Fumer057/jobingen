import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import re

async def crawl_page(url: str):
    """
    Crawls a webpage using Playwright and converts it to Markdown-like text
    using BeautifulSoup's built-in html.parser (no lxml required).
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        try:
            # Navigate with a generous timeout and wait for network idle
            await page.goto(url, wait_until="networkidle", timeout=60000)
            
            # Get the page content
            content = await page.content()
            
            # Use BeautifulSoup with standard html.parser
            soup = BeautifulSoup(content, 'html.parser')
            
            # AGGRESSIVE CLEANING: Remove noise to save tokens/credits
            # These tags almost never contain the structured data we want
            noise_selectors = [
                "script", "style", "nav", "footer", "header", "aside", 
                "iframe", "ins", ".ads", "#ads", ".footer", ".header", 
                ".sidebar", ".menu", ".nav", "noscript", "svg"
            ]
            for selector in noise_selectors:
                for element in soup.select(selector):
                    element.decompose()
            
            # Extract main content if possible (heuristic)
            main_content = soup.find('main') or soup.find('article') or soup.find('div', id='content') or soup.body
            
            if not main_content:
                main_content = soup
                
            # Simple Text representation
            text = main_content.get_text(separator='\n')
            
            # Clean up whitespace and empty lines
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            text = '\n'.join(lines)
            
            # Limit length to essential content (e.g. first 8,000 chars)
            # This is the "Ultra-Low Credit" threshold
            return text[:8000]
            
        except Exception as e:
            raise Exception(f"Failed to crawl {url}: {str(e)}")
        finally:
            await browser.close()

if __name__ == "__main__":
    # Quick test
    async def main():
        url = "https://example.com"
        print(f"Testing fallback crawler with {url}...")
        try:
            text = await crawl_page(url)
            print("Successfully crawled page!")
            print(f"Content snippet: \n{text[:500]}...")
        except Exception as e:
            print(f"Error: {e}")

    asyncio.run(main())
