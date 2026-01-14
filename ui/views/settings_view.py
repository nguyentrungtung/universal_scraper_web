from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QCheckBox, QSpinBox, QGroupBox, QFormLayout, QTextEdit, 
    QComboBox, QPushButton, QDialog
)
from PySide6.QtCore import Signal
from config.settings import UI_CONFIG

class RegexSuggestionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("AI Regex Suggestion")
        self.setMinimumWidth(500)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel("Markdown Sample (Content to split):"))
        self.content_input = QTextEdit()
        self.content_input.setPlaceholderText("Paste a sample of the Markdown content here...")
        self.content_input.setMinimumHeight(200)
        layout.addWidget(self.content_input)
        
        layout.addWidget(QLabel("Instruction (How to split?):"))
        self.prompt_input = QLineEdit()
        self.prompt_input.setPlaceholderText("e.g., Split by each product block starting with '##'")
        layout.addWidget(self.prompt_input)
        
        btn_layout = QHBoxLayout()
        self.suggest_btn = QPushButton("Get Suggestion")
        self.suggest_btn.clicked.connect(self.accept)
        self.suggest_btn.setStyleSheet("background-color: #0078d4; color: white; font-weight: bold;")
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.suggest_btn)
        layout.addLayout(btn_layout)

    def get_data(self):
        return self.content_input.toPlainText(), self.prompt_input.text()

class ProxyInputForm(QGroupBox):
    def __init__(self, parent=None):
        super().__init__("Proxy Configuration (Optional)", parent)
        self.setCheckable(True)
        self.setChecked(False)
        
        layout = QVBoxLayout(self)
        
        self.input = QTextEdit()
        self.input.setPlaceholderText("Format: user:pass@ip:port or ip:port (one per line)")
        self.input.setMaximumHeight(60)
        self.input.setStyleSheet("font-family: Consolas, monospace; font-size: 11px;")
        
        layout.addWidget(self.input)
        
        # Hide input when unchecked
        self.toggled.connect(self.input.setVisible)
        self.input.setVisible(False)

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
    
    def __init__(self, viewModel, parent=None):
        super().__init__("AI Extraction Settings", parent)
        self.viewModel = viewModel
        self.setCheckable(True)
        self.setChecked(False)
        self.setup_ui()
        self.setup_bindings()

    def setup_ui(self):
        layout = QFormLayout(self)
        
        self.ai_provider = QComboBox()
        self.ai_provider.addItems(self.viewModel.get_ai_providers())
        layout.addRow("Provider:", self.ai_provider)
        
        self.ai_model = QComboBox()
        self.ai_model.setEditable(True)
        layout.addRow("Model Name:", self.ai_model)
        
        self.ai_base_url = QLineEdit()
        self.ai_base_url.setPlaceholderText("e.g. http://localhost:11434 (Ollama)")
        layout.addRow("Base URL:", self.ai_base_url)
        
        self.ai_key = QLineEdit()
        self.ai_key.setEchoMode(QLineEdit.Password)
        self.ai_key.setPlaceholderText("Enter API Key")
        layout.addRow("API Key:", self.ai_key)

        # Templates
        self.prompt_template_cb = QComboBox()
        self.schema_template_cb = QComboBox()
        
        layout.addRow("Prompt Template:", self.prompt_template_cb)
        layout.addRow("Schema Template:", self.schema_template_cb)
        
        self.ai_instruction = QLineEdit()
        self.ai_instruction.setText(UI_CONFIG["DEFAULT_AI_INSTRUCTION"])
        layout.addRow("Instruction:", self.ai_instruction)
        
        self.ai_schema = QTextEdit()
        self.ai_schema.setPlaceholderText('{"properties": ...}')
        self.ai_schema.setMaximumHeight(100)
        layout.addRow("JSON Schema (Optional):", self.ai_schema)
        
        self.split_pattern_input = QLineEdit()
        self.split_pattern_input.setPlaceholderText(r"Regex pattern (e.g., \n(?=\[) )")
        
        split_row = QHBoxLayout()
        split_row.addWidget(self.split_pattern_input)
        self.suggest_regex_btn = QPushButton("Suggest")
        self.suggest_regex_btn.setFixedWidth(70)
        self.suggest_regex_btn.clicked.connect(self.on_suggest_regex_clicked)
        split_row.addWidget(self.suggest_regex_btn)
        
        layout.addRow("Split Pattern (Regex):", split_row)
        
        self.use_proxy_cb = QCheckBox("Use Proxy for AI Requests")
        self.use_proxy_cb.setChecked(False)
        self.use_proxy_cb.setToolTip("Enable this if you want AI requests to go through a proxy")
        layout.addRow("", self.use_proxy_cb)

        
        test_btn = QPushButton("Test AI Connection")
        test_btn.clicked.connect(self.on_test_clicked)
        layout.addRow("", test_btn)

    def on_suggest_regex_clicked(self):
        dialog = RegexSuggestionDialog(self)
        if dialog.exec():
            content, prompt = dialog.get_data()
            if not content.strip():
                return
            
            config = self.get_config()
            if config:
                self.viewModel.suggest_regex(content, prompt, config)

    def on_test_clicked(self):
        config = self.get_config()
        if config:
            self.viewModel.test_ai_connection(config)

    def setup_bindings(self):
        # View -> ViewModel
        self.ai_provider.currentTextChanged.connect(self.viewModel.update_provider)
        self.prompt_template_cb.currentTextChanged.connect(self.on_prompt_changed)
        self.schema_template_cb.currentTextChanged.connect(self.on_schema_changed)
        
        # ViewModel -> View
        self.viewModel.ai_models_changed.connect(self.update_models)
        self.viewModel.base_url_changed.connect(self.ai_base_url.setText)
        self.viewModel.prompt_template_changed.connect(self.ai_instruction.setText)
        self.viewModel.schema_template_changed.connect(self.ai_schema.setText)
        self.viewModel.templates_updated.connect(self.update_templates_ui)
        self.viewModel.regex_suggested.connect(self.split_pattern_input.setText)
        
        # Initialize
        self.viewModel.update_provider(self.ai_provider.currentText())

    def update_models(self, models):
        self.ai_model.clear()
        self.ai_model.addItems(models)

    def on_prompt_changed(self, text):
        target_schema = self.viewModel.select_prompt_template(text)
        if target_schema:
            self.schema_template_cb.setCurrentText(target_schema)

    def on_schema_changed(self, text):
        self.viewModel.select_schema_template(text)

    def update_templates_ui(self, prompts, schemas):
        self.prompt_template_cb.clear()
        self.prompt_template_cb.addItem("Custom")
        self.prompt_template_cb.addItems(prompts.keys())
        
        self.schema_template_cb.clear()
        self.schema_template_cb.addItem("Custom")
        self.schema_template_cb.addItems(schemas.keys())

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
            "split_pattern": self.split_pattern_input.text(),
            "use_proxy": self.use_proxy_cb.isChecked()
        }


class SettingsView(QWidget):
    def __init__(self, viewModel, parent=None):
        super().__init__(parent)
        self.viewModel = viewModel
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.proxy_form = ProxyInputForm()
        layout.addWidget(self.proxy_form)
        
        self.crawl_settings = CrawlSettingsWidget()
        layout.addWidget(self.crawl_settings)
        
        self.ai_settings = AISettingsWidget(self.viewModel)
        layout.addWidget(self.ai_settings)
