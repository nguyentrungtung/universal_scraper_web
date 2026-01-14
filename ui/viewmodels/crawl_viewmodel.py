from PySide6.QtCore import Signal, QObject
from ui.viewmodels.base_viewmodel import BaseViewModel
from ui.workers import CrawlWorker
from config.schemas.scraper_input import LLMConfig
from utils.proxy_parser import parse_proxy_list

class CrawlViewModel(BaseViewModel):
    """
    ViewModel for the Crawler Tab.
    Handles starting crawls, updating progress, and queue requests.
    """
    # Signals
    crawl_started = Signal()
    crawl_finished = Signal(dict)
    progress_updated = Signal(str)
    progress_percent = Signal(int)
    queue_requested = Signal(str, dict, dict) # url, crawl_settings, ai_config
    
    def __init__(self):
        super().__init__()
        self.current_worker = None

    def start_crawl(self, url: str, proxy_text: str, crawl_settings: dict, ai_config: dict):
        if not url:
            self.handle_error("Please enter a Target URL.")
            return

        if not url.startswith(("http://", "https://")):
            self.handle_error("Target URL must start with http:// or https://")
            return

        # Prepare Configs
        proxy_list = parse_proxy_list(proxy_text) if proxy_text else []
        
        llm_config = None
        if ai_config:
            if not ai_config["api_key"] and ai_config["provider"] not in ["ollama", "lm-studio"]:
                 self.handle_error("API Key is required for AI extraction")
                 return

            llm_config = LLMConfig(
                provider=ai_config["provider"],
                model_name=ai_config["model_name"],
                api_key=ai_config["api_key"] or "not-needed",
                base_url=ai_config["base_url"] or None,
                instruction=ai_config["instruction"],
                response_schema=ai_config["response_schema"] or None,
                ai_split_pattern=ai_config.get("split_pattern") or None
            )

        # Start Worker
        self.current_worker = CrawlWorker(
            url=url, 
            proxy_list=proxy_list, 
            magic_mode=crawl_settings["magic_mode"], 
            max_pages=crawl_settings["max_pages"], 
            scroll_mode=crawl_settings["scroll_mode"], 
            scroll_depth=crawl_settings["scroll_depth"], 
            llm_config=llm_config, 
            delay=crawl_settings["delay"]
        )
        
        self.current_worker.finished.connect(self.on_finished)
        self.current_worker.error.connect(self.on_error)
        self.current_worker.progress.connect(self.progress_updated.emit)
        self.current_worker.progress_percent.connect(self.progress_percent.emit)
        
        self.current_worker.start()
        self.crawl_started.emit()

    def request_queue(self, url: str, crawl_settings: dict, ai_config: dict):
        if not url:
            self.handle_error("Please enter a Target URL.")
            return
        self.queue_requested.emit(url, crawl_settings, ai_config)

    def on_finished(self, result):
        self.crawl_finished.emit(result)
        self.current_worker = None

    def on_error(self, error_msg):
        self.handle_error(error_msg)
        self.current_worker = None

    def stop_crawl(self):
        if self.current_worker:
            self.current_worker.terminate() # Force stop if needed, or implement graceful stop
            self.current_worker = None
