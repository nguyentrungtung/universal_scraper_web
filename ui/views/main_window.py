import json
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QTabWidget, QMessageBox
)
from PySide6.QtCore import QTimer
from loguru import logger

from config.settings import UI_CONFIG, PATHS_CONFIG
from ui.viewmodels.main_viewmodel import MainViewModel
from ui.views.crawl_view import CrawlView
from ui.views.settings_view import SettingsView
from ui.views.job_view import JobView
from ui.workers import JobQueueWorker
from ui.components import LogConsole

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(UI_CONFIG["WINDOW_TITLE"])
        self.resize(*UI_CONFIG["WINDOW_SIZE"])
        
        # Initialize ViewModel
        self.viewModel = MainViewModel()
        
        self.setup_ui()
        self.setup_connections()
        self.load_templates()
        self.start_background_workers()

        # Redirect Loguru to ViewModel log
        logger.add(self.viewModel.log, format="{time} | {level} | {message}")

    def setup_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        
        self.tabs = QTabWidget()
        self.main_layout.addWidget(self.tabs)
        
        # Tab 1: Crawler
        self.crawler_tab = QWidget()
        self.crawler_layout = QVBoxLayout(self.crawler_tab)
        
        # Crawl View (Top - containing URL input)
        self.crawl_view = CrawlView(self.viewModel.crawl_vm)
        self.crawler_layout.addWidget(self.crawl_view)

        # Settings View (Middle)
        self.settings_view = SettingsView(self.viewModel.settings_vm)
        self.crawler_layout.addWidget(self.settings_view)
        
        # Console (Bottom)
        self.console = LogConsole()
        self.crawler_layout.addWidget(self.console)
        
        self.tabs.addTab(self.crawler_tab, "Crawler")
        
        # Tab 2: Job Queue
        self.job_view = JobView(self.viewModel.job_vm)
        self.tabs.addTab(self.job_view, "Job Queue")

    def setup_connections(self):
        # Connect CrawlView buttons to Main Logic
        self.crawl_view.start_button.clicked.connect(self.on_start_clicked)
        self.crawl_view.queue_button.clicked.connect(self.on_queue_clicked)
        self.crawl_view.clean_button.clicked.connect(self.clean_workspace)
        
        # Connect JobView selection to file opener
        self.job_view.job_selected.connect(self.open_job_result)
        
        # Connect Console Signals
        self.viewModel.status_message.connect(self.console.append_log)
        self.viewModel.crawl_vm.progress_updated.connect(self.console.append_log)
        self.viewModel.crawl_vm.status_message.connect(self.console.append_log)
        self.viewModel.crawl_vm.crawl_started.connect(self.console.clear)

    def load_templates(self):
        prompt_templates = {}
        schema_templates = {}
        try:
            with open(PATHS_CONFIG["PROMPTS_FILE"], "r", encoding="utf-8") as f:
                prompt_templates = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load prompt templates: {e}")

        try:
            with open(PATHS_CONFIG["SCHEMAS_FILE"], "r", encoding="utf-8") as f:
                schema_templates = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load schema templates: {e}")
            
        self.viewModel.settings_vm.set_templates(prompt_templates, schema_templates)

    def start_background_workers(self):
        self.job_worker = JobQueueWorker()
        self.job_worker.job_started.connect(lambda j_id, url: self.viewModel.log(f"[Queue] Started Job {j_id}: {url}"))
        self.job_worker.job_finished.connect(lambda j_id, res: self.viewModel.log(f"[Queue] Finished Job {j_id}"))
        self.job_worker.job_failed.connect(lambda j_id, err: self.viewModel.log(f"[Queue] Failed Job {j_id}: {err}"))
        QTimer.singleShot(1000, self.job_worker.start)

    def on_start_clicked(self):
        # Gather data from Views
        url = self.crawl_view.url_input.text().strip()
        proxy_text = self.settings_view.proxy_form.input.toPlainText().strip()
        crawl_settings = self.settings_view.crawl_settings.get_settings()
        ai_config = self.settings_view.ai_settings.get_config()
        
        # Delegate to ViewModel
        self.viewModel.crawl_vm.start_crawl(url, proxy_text, crawl_settings, ai_config)

    def on_queue_clicked(self):
        url = self.crawl_view.url_input.text().strip()
        crawl_settings = self.settings_view.crawl_settings.get_settings()
        ai_config = self.settings_view.ai_settings.get_config()
        
        self.viewModel.crawl_vm.request_queue(url, crawl_settings, ai_config)

    def clean_workspace(self):
        reply = QMessageBox.question(
            self, 
            "Clean Workspace", 
            "This will delete all LOG files and OUTPUT files (Markdown/JSON) in the workspace.\n\nAre you sure you want to proceed?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            logger.remove()
            from utils.file_manager import clean_up_workspace
            msg = clean_up_workspace(clean_logs=True, clean_outputs=True)
            
            import sys
            import os
            base_dir = os.path.dirname(os.path.abspath(__file__))
            # ui/views/main_window.py -> ui/views -> ui -> root
            root_dir = os.path.dirname(os.path.dirname(os.path.dirname(base_dir)))
            # Fallback if structure is different, but assuming standard structure
            # Better to rely on CWD if running from root, or use relative to main.py location
            # Let's use os.getcwd() as safe default if running via python main.py
            log_dir = os.path.join(os.getcwd(), "logs")
            
            logger.add(sys.stderr, level="INFO")
            logger.add(os.path.join(log_dir, "scraper.log"), rotation="10 MB", retention="10 days", level="DEBUG")
            logger.add(os.path.join(log_dir, "ai_trace.log"), filter=lambda record: "ai_trace" in record["extra"], rotation="10 MB", level="TRACE")
            logger.add(self.viewModel.log, format="{time} | {level} | {message}")
            
            self.viewModel.log(msg)
            QMessageBox.information(self, "Cleanup", msg)

    def open_job_result(self, job_data):
        import os
        if not job_data: return
        
        target_file = None
        result = job_data.get("result")
        
        if result and isinstance(result, dict):
            output_files = result.get("output_files", [])
            if output_files:
                json_files = [f for f in output_files if f.endswith('.json')]
                if json_files:
                    target_file = json_files[0]
                elif output_files:
                    target_file = output_files[0]
        
        if not target_file:
             md = result.get("markdown") if result else None
             if md and isinstance(md, str) and os.path.exists(md):
                 target_file = md

        if target_file and os.path.exists(target_file):
            try:
                self.viewModel.log(f"Viewing Job Result: {target_file}")
                os.startfile(target_file)
            except Exception as e:
                self.viewModel.log(f"Error opening file: {e}")
        else:
            self.viewModel.log("No result file found for this job.")

    def closeEvent(self, event):
        if hasattr(self, 'job_worker') and self.job_worker:
            self.job_worker.stop()
            self.job_worker.wait()
        event.accept()
