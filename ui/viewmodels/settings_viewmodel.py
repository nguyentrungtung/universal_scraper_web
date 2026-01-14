from typing import Dict, Optional, List
from PySide6.QtCore import Signal
from ui.viewmodels.base_viewmodel import BaseViewModel
from config.settings import AI_PROVIDERS, DEFAULT_AI_URLS, UI_CONFIG
from config.schemas.scraper_input import LLMConfig, ProxyConfig
from utils.proxy_parser import parse_proxy_list

class SettingsViewModel(BaseViewModel):
    """
    ViewModel for managing application settings (Crawl, AI, Proxy).
    """
    # Signals for UI updates
    ai_models_changed = Signal(list) # models
    base_url_changed = Signal(str) # url
    prompt_template_changed = Signal(str) # instruction
    schema_template_changed = Signal(str) # schema
    templates_updated = Signal(dict, dict) # prompts, schemas
    
    def __init__(self):
        super().__init__()
        self.prompts = {}
        self.schemas = {}
        
    # --- AI Settings Logic ---
    def get_ai_providers(self) -> List[str]:
        return list(AI_PROVIDERS.keys())
        
    def update_provider(self, provider_name: str):
        if provider_name in AI_PROVIDERS:
            models = AI_PROVIDERS[provider_name]
            self.ai_models_changed.emit(models)
            
            url = DEFAULT_AI_URLS.get(provider_name, "")
            self.base_url_changed.emit(url)
            
    def set_templates(self, prompts: Dict, schemas: Dict):
        self.prompts = prompts
        self.schemas = schemas
        self.templates_updated.emit(prompts, schemas)
        
    def select_prompt_template(self, template_name: str):
        if template_name in self.prompts:
            instruction = self.prompts[template_name]
            self.prompt_template_changed.emit(instruction)
            
            # Auto-select schema logic
            mapping = {
                "Thương mại điện tử (Sản phẩm)": "Sản phẩm (E-commerce)",
                "Tin tức / Blog": "Bài viết (News)"
            }
            
            target_schema = None
            if template_name in mapping:
                target_schema = mapping[template_name]
            else:
                # Substring match
                for schema_key in self.schemas:
                    if schema_key in template_name:
                        target_schema = schema_key
                        break
            
            if target_schema and target_schema in self.schemas:
                # We don't emit schema change here directly to avoid circular loops if view handles it,
                # but we can return it or emit another signal.
                # For simplicity, let's just emit the content.
                self.schema_template_changed.emit(self.schemas[target_schema])
                return target_schema # Return key for View to update combo box
        return None

    def select_schema_template(self, template_name: str):
        if template_name in self.schemas:
            self.schema_template_changed.emit(self.schemas[template_name])

    def validate_ai_config(self, config: Dict) -> bool:
        if not config: return False
        model = config.get("model_name", "").strip()
        provider = config.get("provider", "")
        
        if not model:
            self.handle_error("Model Name cannot be empty.")
            return False
            
        # Warnings can be handled by View (QMessageBox) or here via signal
        # We'll let View handle "Confirmations", VM handles "Errors"
        return True

    # --- Proxy Logic ---
    def parse_proxies(self, proxy_text: str) -> List[ProxyConfig]:
        return parse_proxy_list(proxy_text) if proxy_text else []

    # --- AI Test Logic ---
    def test_ai_connection(self, config_dict: Dict):
        try:
            # Validate minimal config
            if not config_dict.get("api_key"):
                self.handle_error("API Key is required for testing.")
                return

            llm_config = LLMConfig(**config_dict)
            
            # We need to run this in a worker to avoid freezing UI
            # However, QThread should be managed carefully. 
            # For simplicity, we'll create the worker here and keep a reference.
            from ui.workers import AITestWorker
            
            self.test_worker = AITestWorker("test_connection", llm_config)
            self.test_worker.finished.connect(self._on_test_finished)
            self.test_worker.error.connect(self.handle_error)
            self.test_worker.log.connect(self.log)
            
            self.log(f"Starting AI connection test for {llm_config.provider}...")
            self.test_worker.start()
            
        except Exception as e:
            self.handle_error(f"Configuration Error: {e}")

    def _on_test_finished(self, result):
        self.log(f"AI Test Finished. Result: {result}")
        # Emit a signal if View needs to show a popup
        # For now, logging is sufficient, but we can add a specific signal
        pass

    # --- Regex Suggestion Logic ---
    regex_suggested = Signal(str)

    def suggest_regex(self, content: str, prompt: str, config_dict: Dict):
        try:
            if not config_dict.get("api_key"):
                self.handle_error("API Key is required for regex suggestion.")
                return

            llm_config = LLMConfig(**config_dict)
            
            from ui.workers import RegexSuggestionWorker
            
            self.regex_worker = RegexSuggestionWorker(content, prompt, llm_config)
            self.regex_worker.finished.connect(self._on_regex_finished)
            self.regex_worker.error.connect(self.handle_error)
            self.regex_worker.log.connect(self.log)
            
            self.log("Starting AI regex suggestion...")
            self.regex_worker.start()
            
        except Exception as e:
            self.handle_error(f"Regex Suggestion Error: {e}")

    def _on_regex_finished(self, regex: str):
        self.log(f"AI Suggested Regex: {regex}")
        self.regex_suggested.emit(regex)
