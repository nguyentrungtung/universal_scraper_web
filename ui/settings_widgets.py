from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QCheckBox, QSpinBox, QGroupBox, QFormLayout, QTextEdit, 
    QComboBox, QPushButton
)
from PySide6.QtCore import Signal
from config.settings import AI_PROVIDERS, UI_CONFIG, DEFAULT_AI_URLS

class CrawlSettingsWidget(QGroupBox):
    def __init__(self, parent=None):
        super().__init__("Crawl Settings", parent)
        self.setup_ui()

    def setup_ui(self):
        layout = QHBoxLayout(self)
        
        self.magic_mode_cb = QCheckBox("Magic Mode")
        self.magic_mode_cb.setChecked(True)
        self.magic_mode_cb.setToolTip("Anti-detect mode to bypass bot detection")
        
        self.max_pages_spin = QSpinBox()
        self.max_pages_spin.setRange(1, 1000)
        self.max_pages_spin.setValue(UI_CONFIG["DEFAULT_MAX_PAGES"])
        self.max_pages_spin.setFixedWidth(60)
        
        self.crawl_all_cb = QCheckBox("All")
        self.crawl_all_cb.toggled.connect(lambda checked: self.max_pages_spin.setEnabled(not checked))
        
        self.scroll_mode_cb = QCheckBox("Infinite Scroll")
        
        self.scroll_depth_spin = QSpinBox()
        self.scroll_depth_spin.setRange(1, 100)
        self.scroll_depth_spin.setValue(UI_CONFIG["DEFAULT_SCROLL_DEPTH"])
        self.scroll_depth_spin.setFixedWidth(60)
        
        self.scroll_all_cb = QCheckBox("Scroll All")
        self.scroll_all_cb.toggled.connect(lambda checked: self.scroll_depth_spin.setEnabled(not checked))
        
        self.delay_spin = QSpinBox()
        self.delay_spin.setRange(0, 60)
        self.delay_spin.setValue(UI_CONFIG["DEFAULT_DELAY"])
        self.delay_spin.setFixedWidth(50)
        
        layout.addWidget(self.magic_mode_cb)
        layout.addSpacing(20)
        layout.addWidget(QLabel("Max Pages:"))
        layout.addWidget(self.max_pages_spin)
        layout.addWidget(self.crawl_all_cb)
        layout.addSpacing(20)
        layout.addWidget(self.scroll_mode_cb)
        layout.addWidget(QLabel("Depth:"))
        layout.addWidget(self.scroll_depth_spin)
        layout.addWidget(self.scroll_all_cb)
        layout.addSpacing(20)
        layout.addWidget(QLabel("Delay (s):"))
        layout.addWidget(self.delay_spin)
        layout.addStretch()

    def get_settings(self):
        return {
            "magic_mode": self.magic_mode_cb.isChecked(),
            "max_pages": 0 if self.crawl_all_cb.isChecked() else self.max_pages_spin.value(),
            "scroll_mode": self.scroll_mode_cb.isChecked(),
            "scroll_depth": 0 if self.scroll_all_cb.isChecked() else self.scroll_depth_spin.value(),
            "delay": self.delay_spin.value()
        }

class AISettingsWidget(QGroupBox):
    test_connection_requested = Signal()
    prompt_template_changed = Signal(str)
    schema_template_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__("AI Extraction Settings", parent)
        self.setCheckable(True)
        self.setChecked(False)
        self.setup_ui()
        self.prompts = {}
        self.schemas = {}

    def setup_ui(self):
        layout = QFormLayout(self)
        
        self.ai_provider = QComboBox()
        self.ai_provider.addItems(list(AI_PROVIDERS.keys()))
        self.ai_provider.currentTextChanged.connect(self.update_ai_models)
        layout.addRow("Provider:", self.ai_provider)
        
        self.ai_model = QComboBox()
        self.ai_model.setEditable(True)
        layout.addRow("Model Name:", self.ai_model)
        
        self.ai_base_url = QLineEdit()
        self.ai_base_url.setText(DEFAULT_AI_URLS.get("lm-studio", "http://localhost:1234/v1"))
        self.ai_base_url.setPlaceholderText("e.g. http://localhost:11434 (Ollama) or http://localhost:1234/v1 (LM Studio)")
        layout.addRow("Base URL:", self.ai_base_url)
        
        self.ai_key = QLineEdit()
        self.ai_key.setEchoMode(QLineEdit.Password)
        self.ai_key.setPlaceholderText("Enter API Key (use 'ollama' for local)")
        layout.addRow("API Key:", self.ai_key)

        # Templates
        self.prompt_template_cb = QComboBox()
        self.prompt_template_cb.currentTextChanged.connect(self.on_prompt_template_changed)
        
        self.schema_template_cb = QComboBox()
        self.schema_template_cb.currentTextChanged.connect(self.on_schema_template_changed)
        
        layout.addRow("Prompt Template:", self.prompt_template_cb)
        layout.addRow("Schema Template:", self.schema_template_cb)
        
        self.ai_instruction = QLineEdit()
        self.ai_instruction.setText(UI_CONFIG["DEFAULT_AI_INSTRUCTION"])
        layout.addRow("Instruction:", self.ai_instruction)
        
        self.ai_schema = QTextEdit()
        self.ai_schema.setPlaceholderText('{"properties": {"title": {"type": "string"}}, "required": ["title"]}')
        self.ai_schema.setMaximumHeight(100)
        layout.addRow("JSON Schema (Optional):", self.ai_schema)
        
        self.split_pattern_input = QLineEdit()
        self.split_pattern_input.setPlaceholderText(r"Regex pattern to split content (e.g., \n(?=\[) ). Leave empty for auto.")
        self.split_pattern_input.setToolTip(r"Use this to split markdown into blocks. Example: \n(?=\[) for Batdongsan.")
        layout.addRow("Split Pattern (Regex):", self.split_pattern_input)
        
        test_btn = QPushButton("Test AI Connection")
        test_btn.clicked.connect(self.test_connection_requested.emit)
        layout.addRow("", test_btn)
        
        # Initialize models
        self.update_ai_models(self.ai_provider.currentText())

    def update_ai_models(self, provider_name):
        self.ai_model.clear()
        if provider_name in AI_PROVIDERS:
            self.ai_model.addItems(AI_PROVIDERS[provider_name])
            
            if provider_name in DEFAULT_AI_URLS:
                self.ai_base_url.setText(DEFAULT_AI_URLS[provider_name])
            else:
                self.ai_base_url.clear()

    def get_config(self):
        if not self.isChecked():
            return None
            
        return {
            "provider": self.ai_provider.currentText(),
            "model_name": self.ai_model.currentText(),
            "base_url": self.ai_base_url.text(),
            "api_key": self.ai_key.text(),
            "instruction": self.ai_instruction.text(),
            "response_schema": self.ai_schema.toPlainText(),
            "split_pattern": self.split_pattern_input.text()
        }

    def set_templates(self, prompts, schemas):
        self.prompts = prompts
        self.schemas = schemas
        
        self.prompt_template_cb.clear()
        self.prompt_template_cb.addItem("Custom")
        self.prompt_template_cb.addItems(prompts.keys())
        
        self.schema_template_cb.clear()
        self.schema_template_cb.addItem("Custom")
        self.schema_template_cb.addItems(schemas.keys())

    def on_prompt_template_changed(self, text):
        if text in self.prompts:
            self.ai_instruction.setText(self.prompts[text])
            
            # Auto-select schema
            # 1. Try explicit mapping
            mapping = {
                "Thương mại điện tử (Sản phẩm)": "Sản phẩm (E-commerce)",
                "Tin tức / Blog": "Bài viết (News)"
            }
            
            if text in mapping and mapping[text] in self.schemas:
                self.schema_template_cb.setCurrentText(mapping[text])
                self.prompt_template_changed.emit(text)
                return

            # 2. Try substring match
            for schema_key in self.schemas:
                # Check if schema key is part of prompt key (e.g. "Bất động sản" in "Bất động sản (Mặc định)")
                if schema_key in text:
                    self.schema_template_cb.setCurrentText(schema_key)
                    break
        
        self.prompt_template_changed.emit(text)

    def on_schema_template_changed(self, text):
        if text in self.schemas:
            self.ai_schema.setText(self.schemas[text])
        
        self.schema_template_changed.emit(text)
