from PySide6.QtCore import QObject
from ui.viewmodels.base_viewmodel import BaseViewModel
from ui.viewmodels.settings_viewmodel import SettingsViewModel
from ui.viewmodels.crawl_viewmodel import CrawlViewModel
from ui.viewmodels.job_viewmodel import JobViewModel
from database.repository import SQLiteJobRepository
from database.models import JobSettings

class MainViewModel(BaseViewModel):
    """
    Root ViewModel that orchestrates child ViewModels.
    """
    def __init__(self):
        super().__init__()
        
        # Initialize Child ViewModels
        self.settings_vm = SettingsViewModel()
        self.crawl_vm = CrawlViewModel()
        self.job_vm = JobViewModel()
        
        # Setup Inter-ViewModel Communication
        self.crawl_vm.queue_requested.connect(self.on_queue_requested)

    def on_queue_requested(self, url, crawl_settings, ai_config):
        # Convert configs to JobSettings
        llm_config_dict = None
        if ai_config:
             llm_config_dict = {
                "provider": ai_config["provider"],
                "model_name": ai_config["model_name"],
                "api_key": ai_config["api_key"] or "not-needed",
                "base_url": ai_config["base_url"] or None,
                "instruction": ai_config["instruction"],
                "response_schema": ai_config["response_schema"] or None,
                "ai_split_pattern": ai_config.get("split_pattern") or None
            }

        settings = JobSettings(
            magic_mode=crawl_settings["magic_mode"],
            max_pages=crawl_settings["max_pages"],
            scroll_mode=crawl_settings["scroll_mode"],
            scroll_depth=crawl_settings["scroll_depth"],
            delay=crawl_settings["delay"],
            llm_config=llm_config_dict
        )
        
        # Add to Repo (via JobVM logic or direct repo access if JobVM exposes it)
        # Since JobVM wraps the repo, we should probably add a method there or access repo directly.
        # Let's add a method to JobVM to add a job.
        
        repo = SQLiteJobRepository() # Or reuse self.job_vm.repo
        job_id = repo.add_job(url, settings)
        
        self.log(f"Added Job #{job_id} to queue: {url}")
        self.job_vm.refresh_jobs()
