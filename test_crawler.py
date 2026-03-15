import asyncio
from crawler.crawler_engine import crawl_page

async def test_crawler():
    url = "https://example.com"
    print(f"Testing crawler fallback with {url}...")
    try:
        content = await crawl_page(url)
        print("✅ Crawler worked!")
        print(f"Content length: {len(content)}")
        print(f"Snippet: {content[:200]}...")
    except Exception as e:
        print(f"❌ Crawler failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_crawler())
