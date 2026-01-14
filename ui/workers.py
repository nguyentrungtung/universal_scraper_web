import asyncio
from typing import List, Optional
from PySide6.QtCore import QObject, Signal, QThread
from loguru import logger

from core.orchestrator import CrawlOrchestrator
from config.schemas.scraper_input import ProxyConfig, LLMConfig, CrawlRunConfig
from core.job_service import JobService
from database.repository import SQLiteJobRepository
from database.models import JobSettings, JobStatus

class CrawlWorker(QThread):
    finished = Signal(dict)
    error = Signal(str)
    progress = Signal(str)
    progress_percent = Signal(int)

    def __init__(self, url: str, proxy_list: List[ProxyConfig] = None, magic_mode: bool = False, max_pages: int = 1, scroll_mode: bool = False, scroll_depth: int = 5, llm_config: Optional[LLMConfig] = None, delay: int = 0):
        super().__init__()
        self.config = CrawlRunConfig(
            url=url,
            max_pages=max_pages,
            scroll_mode=scroll_mode,
            magic_mode=magic_mode,
            scroll_depth=scroll_depth,
            delay=delay,
            proxies=proxy_list,
            llm_config=llm_config
        )

    def run(self):
        """Chạy trong một thread riêng biệt với event loop riêng"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            self.progress.emit(f"Initializing orchestrator for {self.config.url} (Max Pages: {self.config.max_pages}, Scroll: {self.config.scroll_mode}, AI: {self.config.llm_config is not None}, Delay: {self.config.delay}s)...")
            self.progress_percent.emit(5)
            
            orchestrator = CrawlOrchestrator()
            
            # Callback function to update progress
            def progress_callback(value, total=None, stage="crawling"):
                if stage == "crawling":
                    # Crawling takes up first 35% of progress
                    if total:
                        p = int((value / total) * 35)
                        self.progress_percent.emit(5 + p)
                elif stage == "extracting":
                    # Extraction takes up the remaining 65%
                    # value is percentage complete (0-100) from pipeline
                    p = int((value / 100) * 60) # Map 0-100 to 0-60
                    self.progress_percent.emit(40 + p)

            result = loop.run_until_complete(
                orchestrator.run(self.config, progress_callback=progress_callback)
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
            proxy_list = [] # TODO: Load proxies from settings if needed
            llm_config = None
            if job.settings.llm_config:
                llm_config = LLMConfig(**job.settings.llm_config)

            config = CrawlRunConfig(
                url=job.settings.url,
                max_pages=job.settings.max_pages,
                scroll_mode=job.settings.scroll_mode,
                magic_mode=job.settings.magic_mode,
                scroll_depth=job.settings.scroll_depth,
                delay=job.settings.delay,
                proxies=proxy_list,
                llm_config=llm_config
            )

            orchestrator = CrawlOrchestrator()
            return await orchestrator.run(config)

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
            from ai.litellm_provider import LiteLLMProvider
            
            provider_config = {
                "provider": self.config.provider,
                "model_name": self.config.model_name,
                "api_key": self.config.api_key,
                "base_url": self.config.base_url,
                "use_proxy": getattr(self.config, 'use_proxy', False)
            }
            provider = LiteLLMProvider(provider_config)

            
            self.log.emit(f"[AI] Model: {self.config.model_name}")
            self.log.emit(f"[AI] Status: Thinking...")
            
            import time
            start_time = time.time()
            
            # Test extraction
            result = loop.run_until_complete(
                provider.extract(
                    content="This is a test content to verify AI connection. Please extract: {'title': 'Test'}", 
                    instruction=self.config.instruction,
                    schema=self.config.response_schema
                )
            )
            
            elapsed = time.time() - start_time
            self.finished.emit({"result": result, "elapsed": elapsed})
        except Exception as e:
            self.error.emit(str(e))
        finally:
            loop.close()
class RegexSuggestionWorker(QThread):
    finished = Signal(str)
    error = Signal(str)
    log = Signal(str)

    def __init__(self, content: str, prompt: str, config: LLMConfig):
        super().__init__()
        self.content = content
        self.prompt = prompt
        self.config = config

    def run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            from ai.litellm_provider import LiteLLMProvider
            
            provider_config = {
                "provider": self.config.provider,
                "model_name": self.config.model_name,
                "api_key": self.config.api_key,
                "base_url": self.config.base_url,
                "use_proxy": getattr(self.config, 'use_proxy', False)
            }
            provider = LiteLLMProvider(provider_config)

            
            self.log.emit(f"[AI] Suggesting regex for splitting...")
            
            instruction = (
                f"You are an expert in Regular Expressions. "
                f"The user wants to split the following Markdown content into multiple parts. "
                f"Instruction: {self.prompt}\n"
                f"Please provide ONLY the regex pattern that can be used with Python's re.split() "
                f"to achieve this. Do not include any explanation, code blocks, or quotes. "
                f"Just the raw regex string."
            )
            
            # We use a simple prompt here. LiteLLMProvider.extract expects a schema and returns a list of dicts.
            # Maybe we should add a simpler 'chat' or 'complete' method to LiteLLMProvider.
            # For now, let's use a trick: ask for a JSON with a 'regex' field.
            
            schema = {
                "type": "object",
                "properties": {
                    "regex": {"type": "string"}
                },
                "required": ["regex"]
            }
            
            result = loop.run_until_complete(
                provider.extract(
                    content=self.content,
                    instruction=instruction,
                    schema=schema
                )
            )
            
            if result and isinstance(result, list) and len(result) > 0:
                regex = result[0].get("regex", "")
                self.finished.emit(regex)
            else:
                self.error.emit("AI failed to suggest a regex.")
                
        except Exception as e:
            self.error.emit(str(e))
        finally:
            loop.close()
