import asyncio
import random
from typing import Dict, Any, Optional
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
from loguru import logger

from core.interfaces import IPageFetcher
from config.settings import CRAWL_CONFIG, CONTENT_FILTER_CONFIG, USER_AGENTS

class PageFetcher(IPageFetcher):
    """
    Concrete implementation of IPageFetcher using Crawl4AI.
    Handles browser configuration, proxy rotation, and page fetching with retries.
    """

    def __init__(self):
        pass

    async def fetch(self, url: str, config: Dict[str, Any]) -> Any:
        """
        Fetches a single page.
        
        Args:
            url: Target URL.
            config: Dictionary containing:
                - proxy: Proxy string or None
                - headless: bool
                - magic_mode: bool
                - wait_for: str (selector)
                - timeout: int
                - js_code: list of strings (for scrolling)
                
        Returns:
            CrawlResult object from crawl4ai.
        """
        proxy = config.get("proxy")
        headless = config.get("headless", True)
        magic_mode = config.get("magic_mode", False)
        wait_for = config.get("wait_for")
        timeout = config.get("timeout", 30000)
        js_code = config.get("js_code", [])
        exclude_selectors = config.get("exclude_selectors", [])
        
        user_agent = random.choice(USER_AGENTS)
        
        browser_conf = BrowserConfig(
            headless=headless,
            proxy=proxy,
            user_agent=user_agent
        )
        
        filter_config = self._get_content_filter_config(exclude_selectors)
        
        run_conf = CrawlerRunConfig(
            cache_mode="bypass",
            wait_until=wait_for,
            page_timeout=timeout,
            js_code=js_code,
            extraction_strategy=None, # We handle extraction separately
            **filter_config
        )
        
        return await self._execute_with_retry(url, browser_conf, run_conf, magic_mode)

    async def _execute_with_retry(self, url: str, browser_conf: BrowserConfig, run_conf: CrawlerRunConfig, magic_mode: bool):
        async with AsyncWebCrawler(config=browser_conf) as crawler:
            for attempt in range(CRAWL_CONFIG["RETRY_ATTEMPTS"]):
                try:
                    # Magic mode only on first attempt if requested, or as fallback?
                    # Original logic: magic on attempt 0 if requested.
                    current_magic = magic_mode if attempt == 0 else False
                    
                    if attempt > 0:
                        logger.info(f"Retry attempt {attempt+1} for {url}...")

                    result = await crawler.arun(
                        url=url,
                        config=run_conf,
                        magic=current_magic
                    )
                    
                    if result.success:
                        return result
                    else:
                        logger.warning(f"Fetch failed (Attempt {attempt+1}): {result.error_message}")
                        
                except Exception as e:
                    logger.warning(f"Fetch exception (Attempt {attempt+1}): {e}")
                    if attempt == CRAWL_CONFIG["RETRY_ATTEMPTS"] - 1:
                        raise e
                    await asyncio.sleep(CRAWL_CONFIG["RETRY_DELAY"])
        
        return None

    def _get_content_filter_config(self, dynamic_exclude: Optional[list] = None) -> Dict[str, Any]:
        # Merge global excluded selectors with dynamic ones
        base_excluded = CONTENT_FILTER_CONFIG["excluded_selector"]
        if dynamic_exclude:
            # If base is string, convert to list or append
            # Assuming crawl4ai supports string or list, but let's check usage.
            # Usually it's a string selector like "header, footer, .ads"
            if base_excluded:
                combined = f"{base_excluded}, {', '.join(dynamic_exclude)}"
            else:
                combined = ", ".join(dynamic_exclude)
        else:
            combined = base_excluded

        return {
            "excluded_tags": CONTENT_FILTER_CONFIG["excluded_tags"],
            "excluded_selector": combined,
            "word_count_threshold": CONTENT_FILTER_CONFIG["word_count_threshold"],
            "exclude_external_links": CONTENT_FILTER_CONFIG["exclude_external_links"],
            "exclude_social_media_links": CONTENT_FILTER_CONFIG["exclude_social_media_links"],
            "exclude_domains": CONTENT_FILTER_CONFIG["exclude_domains"],
            "exclude_external_images": CONTENT_FILTER_CONFIG["exclude_external_images"],
            "remove_overlay_elements": CONTENT_FILTER_CONFIG["remove_overlay_elements"],
            "process_iframes": CONTENT_FILTER_CONFIG["process_iframes"],
            "css_selector": CONTENT_FILTER_CONFIG.get("css_selector"),
            "keep_data_attributes": CONTENT_FILTER_CONFIG.get("keep_data_attributes", False)
        }
