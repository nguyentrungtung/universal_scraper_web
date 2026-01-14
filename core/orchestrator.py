import asyncio
from typing import Dict, Any, Optional, List, Callable
from loguru import logger

from core.interfaces import IPageFetcher, ILLMProvider, IStorageService
from core.fetcher import PageFetcher
from core.pipeline import ExtractionPipeline
from ai.litellm_provider import LiteLLMProvider
from utils.result_handler import StreamResultHandler
from core.site_config import SiteConfigManager
from utils.pagination import get_next_page_selector, resolve_next_url
from utils.scrolling import get_infinite_scroll_js
from config.schemas.scraper_input import CrawlRunConfig

class CrawlOrchestrator:
    """
    Orchestrates the crawling process.
    Refactored to use CrawlRunConfig and split responsibilities.
    """
    
    def __init__(self):
        self.fetcher = PageFetcher()

    async def run(self, config: CrawlRunConfig, progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        logger.info(f"Orchestrator started for {config.url}")
        
        # 1. Setup Components
        storage = StreamResultHandler(url=config.url)
        logger.info(f"Job ID: {storage.job_id}")
        
        pipeline = self._setup_pipeline(config)
        site_cfg = SiteConfigManager.get_site_config(config.url)
        next_selector = get_next_page_selector(config.url)
        
        # 2. Determine effective settings
        effective_scroll_mode = config.scroll_mode or site_cfg.get("scroll_mode", False)
        final_scroll_depth = config.scroll_depth if config.scroll_mode else site_cfg.get("scroll_depth", 5)

        # 3. Crawl Loop
        current_url = config.url
        pages_crawled = 0
        last_error = ""
        current_proxy_idx = 0
        
        try:
            for p in range(config.max_pages):
                # Proxy selection
                proxy_server = self._get_proxy(config.proxies, current_proxy_idx)
                if config.proxies:
                    current_proxy_idx = (current_proxy_idx + 1) % len(config.proxies)
                
                logger.info(f">>> PAGE {p+1} | URL: {current_url} | PROXY: {proxy_server or 'DIRECT'}")
                
                if progress_callback:
                    progress_callback(p + 1, config.max_pages, stage="crawling")

                # Prepare Fetch Config
                fetch_config = self._prepare_fetch_config(
                    p, site_cfg, effective_scroll_mode, final_scroll_depth, 
                    config.delay, proxy_server, config.magic_mode
                )
                
                # Fetch
                result = await self.fetcher.fetch(current_url, fetch_config)
                
                if result and result.success:
                    pages_crawled += 1
                    
                    # Save & Extract
                    await self._process_page_result(
                        result, p, current_url, storage, pipeline, config, progress_callback
                    )
                    
                    # Pagination
                    next_url = resolve_next_url(current_url, result.html, next_selector)
                    del result # Cleanup
                    
                    if not next_url:
                        logger.info("Pagination finished.")
                        break
                        
                    current_url = next_url
                    if config.delay > 0:
                        await asyncio.sleep(config.delay)
                else:
                    last_error = result.error_message if result else "Unknown fetch error"
                    logger.error(f"Page {p+1} failed: {last_error}")
                    break
                    
        except Exception as e:
            logger.exception(f"Orchestrator error: {e}")
            last_error = str(e)
            
        # 4. Finalize
        saved_files = storage.finalize()
        
        return {
            "url": config.url,
            "success": pages_crawled > 0,
            "pages_crawled": pages_crawled,
            "error": last_error,
            "output_files": saved_files
        }

    def _setup_pipeline(self, config: CrawlRunConfig) -> Optional[ExtractionPipeline]:
        if not config.llm_config:
            return None
            
        # Use the first proxy for AI only if use_proxy is enabled
        ai_proxy = None
        if config.llm_config.use_proxy and config.proxies and len(config.proxies) > 0:
            ai_proxy = config.proxies[0].server

        provider_config = {
            "provider": config.llm_config.provider,
            "model_name": config.llm_config.model_name,
            "api_key": config.llm_config.api_key,
            "base_url": config.llm_config.base_url,
            "proxy": ai_proxy,
            "use_proxy": config.llm_config.use_proxy
        }
        provider = LiteLLMProvider(provider_config)
        pipeline = ExtractionPipeline(provider)
        logger.info(f"AI Pipeline initialized with {config.llm_config.model_name}")
        return pipeline


    def _get_proxy(self, proxies, idx):
        if not proxies:
            return None
        proxy = proxies[idx]
        return proxy.server if proxy else None

    def _prepare_fetch_config(self, page_idx, site_cfg, scroll_mode, scroll_depth, delay, proxy, magic_mode):
        page_js = site_cfg["js_code"] if page_idx == 0 else []
        if scroll_mode:
            page_js.extend(get_infinite_scroll_js(scroll_depth, delay_ms=delay * 1000 if delay > 0 else 2000))
        
        return {
            "proxy": proxy,
            "headless": True,
            "magic_mode": magic_mode,
            "wait_for": site_cfg["wait_until"],
            "timeout": site_cfg["timeout"],
            "js_code": page_js,
            "exclude_selectors": site_cfg.get("exclude_selectors", [])
        }

    async def _process_page_result(self, result, page_idx, url, storage, pipeline, config, progress_callback):
        # Save Raw Content
        header = f"\n\n{'='*20} PAGE {page_idx+1} {'='*20}\nSOURCE URL: {url}\n{'='*50}\n\n"
        storage.append_content(header + result.markdown)
        
        # Extract Data
        if pipeline and config.llm_config:
            def on_chunk_extracted(items):
                storage.append_data(items)
                
            def pipeline_progress(percent):
                if progress_callback:
                    progress_callback(percent, stage="extracting")
            
            await pipeline.run(
                markdown=result.markdown,
                instruction=config.llm_config.instruction,
                schema=config.llm_config.response_schema,
                split_pattern=getattr(config.llm_config, 'ai_split_pattern', None),
                progress_callback=pipeline_progress,
                stream_callback=on_chunk_extracted
            )
