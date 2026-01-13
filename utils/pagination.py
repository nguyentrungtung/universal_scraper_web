from typing import Optional
from urllib.parse import urljoin
import re

def get_next_page_selector(url: str) -> str:
    """
    Returns the CSS selector for the 'Next' button.
    Supports site-specific overrides and generic fallbacks.
    """
    if "batdongsan.com.vn" in url:
        return "a.re__pagination-icon-next"
    
    if "vnexpress.net" in url:
        return "a.next-page, a.btn-next, a.next"
        
    # Generic fallbacks for most websites
    return "a[rel='next'], a.next, li.next a, a.pagination-next, .next-page a"

def resolve_next_url(current_url: str, html: str, selector: str) -> Optional[str]:
    """
    Generic logic to find the next page URL.
    1. Tries to find a direct link (href) in the 'Next' button.
    2. Applies site-specific URL patterns if no link is found.
    """
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, 'html.parser')
    next_element = soup.select_one(selector)
    
    # Strategy A: Direct link in href (Universal)
    if next_element and next_element.get('href'):
        return urljoin(current_url, next_element.get('href'))
    
    # Strategy B: Pattern-based generation (Site-specific fallback)
    if "batdongsan.com.vn" in current_url:
        if "/p" in current_url:
            return re.sub(r'/p(\d+)', lambda m: f"/p{int(m.group(1))+1}", current_url)
        return current_url.rstrip('/') + "/p2"
        
    # Add more pattern-based strategies here if needed
    
    return None
