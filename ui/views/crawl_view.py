from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QProgressBar, QMessageBox
)
from PySide6.QtCore import Qt
from ui.components import LogConsole

class CrawlView(QWidget):
    def __init__(self, viewModel, parent=None):
        super().__init__(parent)
        self.viewModel = viewModel
        self.setup_ui()
        self.setup_bindings()

    def setup_ui(self):
        self.layout = QVBoxLayout(self)
        
        # URL Row
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
        
        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.hide()
        self.layout.addWidget(self.progress_bar)
        
        # Console removed from here, will be handled by MainWindow
        # self.console = LogConsole()
        # self.layout.addWidget(self.console)

    def setup_bindings(self):
        # ViewModel -> View
        self.viewModel.progress_percent.connect(self.update_progress)
        self.viewModel.crawl_started.connect(self.on_crawl_started)
        self.viewModel.crawl_finished.connect(self.on_crawl_finished)
        self.viewModel.error_occurred.connect(self.on_error)
        
        # Console signals are now handled by MainWindow


        # View -> ViewModel (via MainWindow usually, but we can emit signals)
        # We don't connect start_button directly to VM.start_crawl because we need settings.
        # So we expose the buttons or emit custom signals.
        pass

    def update_progress(self, value):
        self.progress_bar.setValue(value)

    def on_crawl_started(self):
        self.start_button.setEnabled(False)
        self.progress_bar.show()
        # Console cleared by MainWindow

    def on_crawl_finished(self, result):
        self.start_button.setEnabled(True)
        self.progress_bar.hide()
        
        saved_files = result.get("output_files", [])
        if saved_files:
            msg = "Crawl finished!\nSaved to:\n" + "\n".join(saved_files)
            QMessageBox.information(self, "Done", msg)
        else:
            QMessageBox.warning(self, "Warning", "No content extracted.")

    def on_error(self, error_msg):
        self.start_button.setEnabled(True)
        self.progress_bar.hide()
        QMessageBox.critical(self, "Error", error_msg)
