import asyncio
import qasync
import os
import json
from datetime import datetime
from typing import List, Optional

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QLineEdit, QPushButton, QCheckBox,
    QProgressBar, QMessageBox, QSpinBox, QGroupBox, 
    QFormLayout, QTextEdit, QComboBox, QTabWidget
)
from PySide6.QtCore import Qt, QThread, QTimer, Signal
from loguru import logger

from ui.components import ProxyInputForm, LogConsole
from ui.settings_widgets import CrawlSettingsWidget, AISettingsWidget
from ui.workers import CrawlWorker, JobQueueWorker, AITestWorker
from utils.file_manager import ensure_dir
from utils.proxy_parser import parse_proxy_list
from utils.result_handler import ResultHandler
from config.settings import AI_PROVIDERS, UI_CONFIG, PATHS_CONFIG
from models.scraper_input import LLMConfig
from core.extraction import LLMExtractor
from ui.job_manager import JobManagerWidget
from database.repository import SQLiteJobRepository
from database.models import JobSettings
import litellm

# Silence litellm globally
litellm.telemetry = False
litellm.suppress_debug_info = True
litellm.set_verbose = False
litellm._logging_level = "CRITICAL"
litellm.drop_params = True
litellm.turn_off_message_logging = True 

class MainWindow(QMainWindow):
    log_signal = Signal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle(UI_CONFIG["WINDOW_TITLE"])
        self.resize(*UI_CONFIG["WINDOW_SIZE"])
        
        self.setup_ui()
        self.setup_connections()
        self.load_templates()
        self.start_background_workers()

        logger.add(self.log_to_console, format="{time} | {level} | {message}")

    def setup_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        
        self.console = LogConsole()
        
        self.tabs = QTabWidget()
        self.main_layout.addWidget(self.tabs)
        
        # Tab 1: Crawler
        self.crawler_tab = QWidget()
        self.layout = QVBoxLayout(self.crawler_tab)
        self.tabs.addTab(self.crawler_tab, "Crawler")
        
        # Tab 2: Job Manager
        self.job_manager = JobManagerWidget()
        self.tabs.addTab(self.job_manager, "Job Queue")
        
        # URL Input Row
        self.setup_url_row()
        
        # Settings
        self.proxy_form = ProxyInputForm()
        self.layout.addWidget(self.proxy_form)
        
        self.crawl_settings = CrawlSettingsWidget()
        self.layout.addWidget(self.crawl_settings)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.hide()
        self.layout.addWidget(self.progress_bar)
        
        self.ai_settings = AISettingsWidget()
        self.layout.addWidget(self.ai_settings)
        
        self.layout.addWidget(self.console)

    def setup_url_row(self):
        url_row = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Enter Target URL (e.g., https://example.com)")
        self.url_input.setFixedHeight(30)
        
        self.start_button = QPushButton("Start Crawl")
        self.start_button.setFixedWidth(120)
        self.start_button.setFixedHeight(30)
        self.start_button.setStyleSheet("background-color: #0078d4; color: white; font-weight: bold; border-radius: 4px;")
        
        self.queue_button = QPushButton("Add to Queue")
        self.queue_button.setFixedWidth(120)
        self.queue_button.setFixedHeight(30)
        self.queue_button.setStyleSheet("background-color: #28a745; color: white; font-weight: bold; border-radius: 4px;")
        
        self.clean_button = QPushButton("Clean")
        self.clean_button.setFixedWidth(80)
        self.clean_button.setFixedHeight(30)
        self.clean_button.setStyleSheet("background-color: #dc3545; color: white; font-weight: bold; border-radius: 4px;")
        self.clean_button.setToolTip("Clean Workspace (Logs & Outputs)")
        
        url_row.addWidget(QLabel("URL:"))
        url_row.addWidget(self.url_input)
        url_row.addWidget(self.start_button)
        url_row.addWidget(self.queue_button)
        url_row.addWidget(self.clean_button)
        
        self.layout.addLayout(url_row)

    def setup_connections(self):
        self.log_signal.connect(self.console.append_log)
        self.start_button.clicked.connect(self.on_start_clicked)
        self.queue_button.clicked.connect(self.on_queue_clicked)
        self.clean_button.clicked.connect(self.clean_workspace)
        self.ai_settings.test_connection_requested.connect(self.test_ai_connection)
        self.job_manager.job_selected.connect(self.on_job_selected)

    def start_background_workers(self):
        self.job_worker = JobQueueWorker()
        self.job_worker.job_started.connect(lambda j_id, url: self.console.append_log(f"[Queue] Started Job {j_id}: {url}"))
        self.job_worker.job_finished.connect(lambda j_id, res: self.console.append_log(f"[Queue] Finished Job {j_id}"))
        self.job_worker.job_failed.connect(lambda j_id, err: self.console.append_log(f"[Queue] Failed Job {j_id}: {err}"))
        QTimer.singleShot(1000, self.job_worker.start)

    def log_to_console(self, message):
        self.log_signal.emit(message.strip())

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
            
        self.ai_settings.set_templates(prompt_templates, schema_templates)

    def validate_ai_config(self, config):
        if not config: return False
        model = config.get("model_name", "").strip()
        provider = config.get("provider", "")
        
        if not model:
            QMessageBox.warning(self, "Validation Error", "Model Name cannot be empty.")
            return False
            
        if provider == "openai" and "llama" in model.lower():
            if QMessageBox.question(self, "Potential Mismatch", "Selected OpenAI but model looks like Llama. Continue?", QMessageBox.Yes | QMessageBox.No) == QMessageBox.No: return False
            
        if provider == "anthropic" and "gpt" in model.lower():
            if QMessageBox.question(self, "Potential Mismatch", "Selected Anthropic but model looks like GPT. Continue?", QMessageBox.Yes | QMessageBox.No) == QMessageBox.No: return False
            
        return True

    def test_ai_connection(self):
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Error", "Please enter a Target URL first to test extraction.")
            return

        ai_config = self.ai_settings.get_config()
        if not ai_config:
            QMessageBox.warning(self, "Error", "Please enable AI settings first.")
            return

        if not self.validate_ai_config(ai_config):
            return

        self.console.append_log(f"--- AI TEST START ---")
        config = LLMConfig(
            provider=ai_config["provider"],
            model_name=ai_config["model_name"],
            api_key=ai_config["api_key"] or "not-needed",
            base_url=ai_config["base_url"] or None,
            instruction=ai_config["instruction"],
            response_schema=ai_config["response_schema"] or None
        )

        self.test_worker = AITestWorker(url, config)
        self.test_worker.log.connect(self.console.append_log)
        self.test_worker.error.connect(lambda err: QMessageBox.critical(self, "Error", f"AI Connection Failed: {err}"))
        self.test_worker.finished.connect(self.on_ai_test_finished)
        self.test_worker.start()

    def on_ai_test_finished(self, data):
        result = data["result"]
        elapsed = data["elapsed"]
        self.console.append_log(f"[AI] Done thinking. Thought for {elapsed:.2f} seconds.")
        self.console.append_log(f"[AI] Response: {json.dumps(result, indent=2, ensure_ascii=False)}")
        QMessageBox.information(self, "Success", f"AI Connection Successful!\nThought for {elapsed:.2f}s")

    def on_start_clicked(self):
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Validation Error", "Please enter a Target URL.")
            return

        if not url.startswith(("http://", "https://")):
            QMessageBox.warning(self, "Validation Error", "Target URL must start with http:// or https://")
            return
            
        proxy_text = self.proxy_form.input.toPlainText().strip()
        proxy_list = parse_proxy_list(proxy_text) if proxy_text else []
        
        crawl_settings = self.crawl_settings.get_settings()
        ai_config_data = self.ai_settings.get_config()
        
        llm_config = None
        if ai_config_data:
            if not ai_config_data["api_key"] and ai_config_data["provider"] not in ["ollama", "lm-studio"]:
                 QMessageBox.warning(self, "Error", "API Key is required for AI extraction")
                 return

            llm_config = LLMConfig(
                provider=ai_config_data["provider"],
                model_name=ai_config_data["model_name"],
                api_key=ai_config_data["api_key"] or "not-needed",
                base_url=ai_config_data["base_url"] or None,
                instruction=ai_config_data["instruction"],
                response_schema=ai_config_data["response_schema"] or None,
                ai_split_pattern=ai_config_data.get("split_pattern") or None
            )
        
        self.start_button.setEnabled(False)
        self.progress_bar.show()
        self.console.clear()
        
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
        self.current_worker.finished.connect(self.handle_finished)
        self.current_worker.error.connect(self.handle_error)
        self.current_worker.progress.connect(self.console.append_log)
        self.current_worker.progress_percent.connect(self.progress_bar.setValue)
        self.current_worker.finished.connect(lambda: self.cleanup_worker())
        self.current_worker.error.connect(lambda: self.cleanup_worker())
        self.current_worker.start()

    def cleanup_worker(self):
        self.start_button.setEnabled(True)
        self.progress_bar.hide()
        self.current_worker = None

    def on_queue_clicked(self):
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Validation Error", "Please enter a Target URL.")
            return

        crawl_settings = self.crawl_settings.get_settings()
        ai_config_data = self.ai_settings.get_config()
        
        llm_config_dict = None
        if ai_config_data:
             llm_config_dict = {
                "provider": ai_config_data["provider"],
                "model_name": ai_config_data["model_name"],
                "api_key": ai_config_data["api_key"] or "not-needed",
                "base_url": ai_config_data["base_url"] or None,
                "instruction": ai_config_data["instruction"],
                "response_schema": ai_config_data["response_schema"] or None,
                "ai_split_pattern": ai_config_data.get("split_pattern") or None
            }

        settings = JobSettings(
            magic_mode=crawl_settings["magic_mode"],
            max_pages=crawl_settings["max_pages"],
            scroll_mode=crawl_settings["scroll_mode"],
            scroll_depth=crawl_settings["scroll_depth"],
            delay=crawl_settings["delay"],
            llm_config=llm_config_dict
        )
        
        repo = SQLiteJobRepository()
        job_id = repo.add_job(url, settings)
        
        self.console.append_log(f"Added Job #{job_id} to queue: {url}")
        self.job_manager.refresh_jobs()

    def clean_workspace(self):
        reply = QMessageBox.question(
            self, 
            "Clean Workspace", 
            "This will delete all LOG files and OUTPUT files (Markdown/JSON) in the workspace.\n\nAre you sure you want to proceed?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Remove all logger handlers to release file lock on Windows
            logger.remove()
            
            from utils.file_manager import clean_up_workspace
            msg = clean_up_workspace(clean_logs=True, clean_outputs=True)
            
            # Re-add handlers (restore state from main.py and __init__)
            import sys
            # Note: We hardcode the config here to match main.py. 
            # Ideally this should be centralized, but for now this fixes the lock issue.
            logger.add(sys.stderr, level="INFO")
            logger.add("scraper.log", rotation="10 MB", level="DEBUG")
            logger.add(self.log_to_console, format="{time} | {level} | {message}")
            
            self.console.append_log(msg)
            QMessageBox.information(self, "Cleanup", msg)

    def handle_error(self, error_msg):
        self.console.append_log(f"ERROR: {error_msg}")
        QMessageBox.critical(self, "Error", error_msg)

    def handle_finished(self, result):
        self.console.append_log("--- CRAWL FINISHED ---")
        saved_files = ResultHandler.save_result(result, self.console.append_log)
        if saved_files:
            msg = "Crawl finished!\nSaved to:\n" + "\n".join(saved_files)
            QMessageBox.information(self, "Done", msg)
        else:
            QMessageBox.warning(self, "Warning", "No content extracted.")

    def on_job_selected(self, job_data):
        if not job_data: return
        result_file = job_data.get("result_file")
        if result_file and os.path.exists(result_file):
            try:
                self.console.append_log(f"Viewing Job Result: {result_file}")
                os.startfile(result_file)
            except Exception as e:
                self.console.append_log(f"Error opening file: {e}")

    def closeEvent(self, event):
        if hasattr(self, 'job_worker') and self.job_worker:
            self.job_worker.stop()
            self.job_worker.wait()
        event.accept()
