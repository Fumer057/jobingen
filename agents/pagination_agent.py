import re
from urllib.parse import urljoin
from bs4 import BeautifulSoup

class PaginationAgent:
    def __init__(self):
        pass

    def find_next_page(self, html: str, current_url: str) -> str:
        """
        Heuristic-based next page discovery from HTML.
        Look for common 'Next' patterns in link text.
        """
        soup = BeautifulSoup(html, 'html.parser')
        
        # Common patterns for Next links
        next_patterns = [
            r'next', r'forward', r'newer', r'>', r'»', r'arrow-right',
            r'pagi?n?ation'
        ]
        
        links = soup.find_all('a', href=True)
        
        for link in links:
            text = link.get_text().strip().lower()
            # Check text matches or class/id contains 'next'
            if any(re.search(p, text) for p in next_patterns) or \
               any(re.search(r'next', str(val).lower()) for val in link.get('class', [])) or \
               re.search(r'next', str(link.get('id', '')).lower()):
                
                href = link['href']
                if not href.startswith('javascript'):
                    return urljoin(current_url, href)
                    
        return None
