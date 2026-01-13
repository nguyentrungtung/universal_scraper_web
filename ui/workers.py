import asyncio
from typing import List, Optional
from PySide6.QtCore import QObject, Signal
from core.crawler_engine import WebCrawlerService
from models.scraper_input import ProxyConfig, LLMConfig
from loguru import logger
from core.job_service import JobService
from database.repository import SQLiteJobRepository
from database.models import JobSettings, JobStatus

from PySide6.QtCore import QObject, Signal, QThread
import asyncio

class CrawlWorker(QThread):
    finished = Signal(dict)
    error = Signal(str)
    progress = Signal(str)
    progress_percent = Signal(int)

    def __init__(self, url: str, proxy_list: List[ProxyConfig] = None, magic_mode: bool = False, max_pages: int = 1, scroll_mode: bool = False, scroll_depth: int = 5, llm_config: Optional[LLMConfig] = None, delay: int = 0):
        super().__init__()
        self.url = url
        self.proxy_list = proxy_list or []
        self.magic_mode = magic_mode
        self.max_pages = max_pages
        self.scroll_mode = scroll_mode
        self.scroll_depth = scroll_depth
        self.llm_config = llm_config
        self.delay = delay

    def run(self):
        """Chạy trong một thread riêng biệt với event loop riêng"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            self.progress.emit(f"Initializing crawler for {self.url} (Max Pages: {self.max_pages}, Scroll: {self.scroll_mode}, AI: {self.llm_config is not None}, Delay: {self.delay}s)...")
            self.progress_percent.emit(5)
            
            # Khởi tạo service bên trong thread
            from core.crawler_engine import WebCrawlerService
            service = WebCrawlerService(proxy_list=self.proxy_list)
            
            # Callback function to update progress
            def progress_callback(value, total=None, stage="crawling"):
                if stage == "crawling":
                    # Crawling takes up first 35% of progress
                    # value is current_page, total is total_pages
                    if total:
                        p = int((value / total) * 35)
                        self.progress_percent.emit(5 + p)
                elif stage == "extracting":
                    # Extraction takes up the remaining 65%
                    # value is percentage complete (0-100) from extractor
                    p = int((value / 100) * 60) # Map 0-100 to 0-60
                    self.progress_percent.emit(40 + p)

            result = loop.run_until_complete(
                service.run_crawl(
                    self.url, 
                    self.max_pages, 
                    self.scroll_mode, 
                    self.magic_mode, 
                    scroll_depth=self.scroll_depth, 
                    llm_config=self.llm_config, 
                    delay=self.delay,
                    progress_callback=progress_callback
                )
            )
            self.progress_percent.emit(100)
            
            if result.get("success"):
                self.finished.emit(result)
            else:
                self.error.emit(result.get("error", "Unknown error"))
        except Exception as e:
            logger.exception("Worker thread failed")
            self.error.emit(str(e))
        finally:
            loop.close()

class JobQueueWorker(QThread):
    job_started = Signal(int, str) # job_id, url
    job_finished = Signal(int, dict) # job_id, result
    job_failed = Signal(int, str) # job_id, error
    progress = Signal(str)

    def __init__(self, repository_path: str = "crawl_jobs.db"):
        super().__init__()
        self.repo = SQLiteJobRepository(repository_path)
        self.job_service = JobService(self.repo)
        self.is_running = True

    def run(self):
        """Chạy hàng đợi trong thread riêng"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        self.progress.emit("Job Queue Worker started in background thread.")
        
        while self.is_running:
            try:
                job = self.job_service.get_next_pending_job()
                if job:
                    self.job_started.emit(job.id, job.settings.url)
                    self.job_service.start_job(job.id)
                    
                    # Chạy job
                    result = loop.run_until_complete(self._execute_job(job))
                    
                    if result.get("success"):
                        self.job_service.complete_job(job.id, result)
                        self.job_finished.emit(job.id, result)
                    else:
                        error_msg = result.get("error", "Unknown error")
                        self.job_service.fail_job(job.id, error_msg)
                        self.job_failed.emit(job.id, error_msg)
            except Exception as e:
                logger.exception("Queue worker loop error")
            
            loop.run_until_complete(asyncio.sleep(3))
            
        loop.close()

    async def _execute_job(self, job):
        try:
            proxy_list = []
            llm_config = None
            if job.settings.llm_config:
                llm_config = LLMConfig(**job.settings.llm_config)

            from core.crawler_engine import WebCrawlerService
            crawler = WebCrawlerService(proxy_list=proxy_list)
            return await crawler.run_crawl(
                url=job.settings.url,
                max_pages=job.settings.max_pages,
                scroll_mode=job.settings.scroll_mode,
                magic_mode=job.settings.magic_mode,
                scroll_depth=job.settings.scroll_depth,
                llm_config=llm_config,
                delay=job.settings.delay
            )
        except Exception as e:
            return {"success": False, "error": str(e)}

    def stop(self):
        self.is_running = False

class AITestWorker(QThread):
    finished = Signal(dict)
    error = Signal(str)
    log = Signal(str)

    def __init__(self, url: str, config: LLMConfig):
        super().__init__()
        self.url = url
        self.config = config

    def run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            from core.extraction import LLMExtractor
            extractor = LLMExtractor(self.config)
            strategy = extractor.get_strategy()
            
            self.log.emit(f"[AI] Model: {self.config.model_name}")
            self.log.emit(f"[AI] Status: Thinking...")
            
            import time
            start_time = time.time()
            
            # Test extraction
            # Note: LLMExtractor uses crawl4ai strategy which has aextract
            result = loop.run_until_complete(
                strategy.aextract(url=self.url, ix=0, html="This is a test content to verify AI connection.")
            )
            
            elapsed = time.time() - start_time
            self.finished.emit({"result": result, "elapsed": elapsed})
        except Exception as e:
            self.error.emit(str(e))
        finally:
            loop.close()
