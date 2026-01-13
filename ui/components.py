from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QTextEdit, QCheckBox, 
                             QProgressBar, QGroupBox)

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

class LogConsole(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setStyleSheet("background-color: #1e1e1e; color: #d4d4d4; font-family: Consolas, monospace;")
        self.setPlaceholderText("Logs and results will appear here...")

    def append_log(self, message: str):
        self.append(message)
        # Auto-scroll to bottom
        self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())
