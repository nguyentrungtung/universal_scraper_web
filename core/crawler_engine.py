import asyncio
from typing import Optional, Dict, Any, List
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
from models.scraper_input import ProxyConfig
from config.settings import CRAWL_CONFIG, CONTENT_FILTER_CONFIG, USER_AGENTS
from loguru import logger
import litellm
import random

# New Components
from core.site_config import SiteConfigManager
from core.extraction import ManualBatchExtractor
from utils.pagination import get_next_page_selector, resolve_next_url
from utils.scrolling import get_infinite_scroll_js

class WebCrawlerService:
    def __init__(self, proxy_list: Optional[List[ProxyConfig]] = None, browser_config: Optional[Dict[str, Any]] = None):
        self.proxy_list = proxy_list or []
        self.browser_config = browser_config or {}
        self.current_proxy_idx = 0

    def _get_next_proxy(self) -> Optional[ProxyConfig]:
        if not self.proxy_list:
            return None
        proxy = self.proxy_list[self.current_proxy_idx]
        self.current_proxy_idx = (self.current_proxy_idx + 1) % len(self.proxy_list)
        return proxy

    async def run_crawl(self, url: str, max_pages: int = 1, scroll_mode: bool = False, magic_mode: bool = False, scroll_depth: int = 5, llm_config: Optional[ProxyConfig] = None, delay: int = 0, progress_callback=None) -> Dict[str, Any]:
        logger.info(f"Starting crawl for URL: {url} (Pages: {max_pages}, Scroll: {scroll_mode}, Magic: {magic_mode}, AI: {llm_config is not None}, Delay: {delay}s)")
        
        # 1. Setup Configuration
        site_cfg = SiteConfigManager.get_site_config(url)
        next_selector = get_next_page_selector(url)
        
        effective_scroll_mode = scroll_mode or site_cfg.get("scroll_mode", False)
        final_scroll_depth = scroll_depth if scroll_mode else site_cfg.get("scroll_depth", 5)
        
        # 2. Setup Extractor & Stream Handler
        extractor = ManualBatchExtractor(llm_config) if llm_config else None
        if extractor:
            logger.info(f"Using AI Extraction with model: {llm_config.model_name}")

        # Initialize Stream Handler
        from utils.result_handler import StreamResultHandler
        stream_handler = StreamResultHandler()
        logger.info(f"Stream processing enabled. Job ID: {stream_handler.job_id}")

        pages_crawled = 0
        total_items_extracted = 0
        last_error = ""
        current_url = url
        
        try:
            for p in range(max_pages):
                # Proxy & Logging
                proxy = self._get_next_proxy()
                proxy_display = proxy.server if proxy else "DIRECT"
                logger.info(f">>> PAGE {p+1} | PROXY: {proxy_display} | URL: {current_url}")
                
                if progress_callback:
                    progress_callback(p + 1, max_pages, stage="crawling")
                
                # Prepare JS
                page_js = site_cfg["js_code"] if p == 0 else []
                if effective_scroll_mode:
                    logger.info(f"Applying infinite scroll (depth: {final_scroll_depth})")
                    page_js.extend(get_infinite_scroll_js(final_scroll_depth, delay_ms=delay * 1000 if delay > 0 else 2000))
                
                # Configure Crawler
                user_agent = random.choice(USER_AGENTS)
                browser_conf = BrowserConfig(
                    headless=self.browser_config.get("headless", True),
                    proxy=proxy.server if proxy else None,
                    user_agent=user_agent
                )
                
                run_conf = CrawlerRunConfig(
                    cache_mode="bypass",
                    wait_until=site_cfg["wait_until"],
                    page_timeout=site_cfg["timeout"],
                    js_code=page_js,
                    extraction_strategy=None, # We do manual extraction
                    **self._get_content_filter_config()
                )
                
                # Execute Crawl with Retry
                result = await self._execute_crawl_with_retry(current_url, browser_conf, run_conf, site_cfg, magic_mode, p)
                
                if result and result.success:
                    pages_crawled += 1
                    
                    # Token Check
                    self._check_token_limit(result.markdown, llm_config)

                    # Store Markdown (Stream to disk immediately)
                    page_header = self._create_page_header(p + 1, current_url, proxy_display)
                    stream_handler.append_markdown(page_header + result.markdown)
                    
                    # AI Extraction
                    if extractor:
                        # Pass progress callback to extractor
                        def extractor_progress_wrapper(percent):
                            if progress_callback:
                                progress_callback(percent, stage="extracting")
                                
                        # Extract data (but don't accumulate in memory)
                        new_items = extractor.extract(result.markdown, [], progress_callback=extractor_progress_wrapper)
                        
                        # Stream data to disk immediately
                        stream_handler.append_data(new_items)
                        total_items_extracted += len(new_items)
                        
                        logger.info(f"Total items extracted from page {p+1}: {len(new_items)}")
                        
                        # Clear memory
                        del new_items
                    else:
                        logger.info("No AI strategy configured. Skipping extraction.")
                    
                    # Pagination Check (Before clearing memory)
                    next_url = resolve_next_url(current_url, result.html, next_selector)
                    
                    # Clear result memory to free RAM
                    del result
                    
                    if not next_url:
                        logger.info("Pagination finished: No next page URL resolved.")
                        break
                        
                    current_url = next_url
                    if delay > 0:
                        await asyncio.sleep(delay)
                    
                else:
                    last_error = result.error_message if result else "Unknown error"
                    logger.error(f"Crawl failed at page {p+1}: {last_error}")
                    break
        except Exception as e:
            logger.exception(f"Unexpected error: {e}")
            return {"url": url, "success": False, "error": str(e)}
            
        # Finalize Stream
        saved_files = stream_handler.finalize()
        logger.info(f"Crawl finished. Saved files: {saved_files}")

        return {
            "url": url,
            "markdown": f"Saved to {stream_handler.md_file}", # Return path instead of content
            "extracted_data": [], # Return empty list to save RAM, data is in file
            "success": pages_crawled > 0,
            "pages_crawled": pages_crawled,
            "error": last_error,
            "output_files": saved_files
        }

    def _get_content_filter_config(self) -> Dict[str, Any]:
        return {
            "excluded_tags": CONTENT_FILTER_CONFIG["excluded_tags"],
            "excluded_selector": CONTENT_FILTER_CONFIG["excluded_selector"],
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

    async def _execute_crawl_with_retry(self, url: str, browser_conf: BrowserConfig, run_conf: CrawlerRunConfig, site_cfg: Dict, magic_mode: bool, page_num: int):
        async with AsyncWebCrawler(config=browser_conf) as crawler:
            for attempt in range(CRAWL_CONFIG["RETRY_ATTEMPTS"]):
                try:
                    current_magic = magic_mode if attempt == 0 else False
                    if attempt > 0:
                        logger.info(f"Retry attempt {attempt+1} for page {page_num+1} (Magic: {current_magic})...")
                    
                    result = await crawler.arun(
                        url=url,
                        config=run_conf,
                        magic=current_magic,
                        wait_for=site_cfg["wait_for"]
                    )
                    if result.success:
                        return result
                except Exception as e:
                    error_msg = str(e)
                    logger.warning(f"Attempt {attempt+1} failed: {error_msg}")
                    if "model" in error_msg.lower():
                         raise Exception(f"AI Model Error: {error_msg}")
                    if attempt == CRAWL_CONFIG["RETRY_ATTEMPTS"] - 1:
                        return None # Or raise
                    await asyncio.sleep(CRAWL_CONFIG["RETRY_DELAY"])
        return None

    def _check_token_limit(self, markdown: str, llm_config: Optional[ProxyConfig]):
        if not llm_config:
            return
        
        from core.ai_handler import get_litellm_model_name
        full_model = get_litellm_model_name(llm_config.provider, llm_config.model_name)
        
        try:
            max_tokens = litellm.get_max_tokens(full_model)
            est_tokens = litellm.token_counter(model=full_model, text=markdown)
            limit_info = f" / {max_tokens}" if max_tokens else ""
            logger.info(f"Content tokens: ~{est_tokens}{limit_info}")
            
            if max_tokens and est_tokens > max_tokens:
                logger.warning(f"CRITICAL: Page exceeds model max tokens ({est_tokens} > {max_tokens})!")
        except:
            pass

    def _create_page_header(self, page_num: int, url: str, proxy: str) -> str:
        return f"\n\n{'='*20} PAGE {page_num} {'='*20}\nSOURCE URL: {url}\nPROXY USED: {proxy}\n{'='*50}\n\n"
