from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
    QTableWidgetItem, QPushButton, QHeaderView, QLabel,
    QMenu, QMessageBox
)
from PySide6.QtCore import Qt, Signal, QTimer
from database.models import JobStatus

class JobView(QWidget):
    job_selected = Signal(dict) # Emits job data when "View Result" is clicked

    def __init__(self, viewModel, parent=None):
        super().__init__(parent)
        self.viewModel = viewModel
        self.setup_ui()
        self.setup_bindings()
        
        # Refresh timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.viewModel.refresh_jobs)
        self.timer.start(3000) # Refresh every 3 seconds

        # Initial load
        self.viewModel.refresh_jobs()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("<h2>Job Queue & History</h2>"))
        
        self.refresh_btn = QPushButton("Refresh Now")
        self.refresh_btn.clicked.connect(self.viewModel.refresh_jobs)
        
        self.clear_all_btn = QPushButton("Clear All Jobs")
        self.clear_all_btn.setStyleSheet("background-color: #f44336; color: white;")
        self.clear_all_btn.clicked.connect(self.on_clear_all_clicked)
        
        header_layout.addStretch()
        header_layout.addWidget(self.clear_all_btn)
        header_layout.addWidget(self.refresh_btn)
        
        layout.addLayout(header_layout)
        
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels([
            "ID", "Status", "URL", "Settings", "Created At", "Updated At", "Actions"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        
        layout.addWidget(self.table)

    def setup_bindings(self):
        self.viewModel.jobs_updated.connect(self.update_table)
        self.viewModel.job_details_ready.connect(self.job_selected.emit)
        self.viewModel.error_occurred.connect(self.on_error)

    def update_table(self, jobs):
        self.table.setRowCount(0)
        for job in jobs:
            idx = self.table.rowCount()
            self.table.insertRow(idx)
            
            settings = job['settings']
            url = settings.get('url', 'N/A')
            
            self.table.setItem(idx, 0, QTableWidgetItem(str(job['id'])))
            
            status_item = QTableWidgetItem(job['status'])
            self.set_status_color(status_item, job['status'])
            self.table.setItem(idx, 1, status_item)
            
            self.table.setItem(idx, 2, QTableWidgetItem(url))
            
            # Settings Summary
            max_p = settings.get('max_pages', 1)
            pages_str = f"P: {max_p if max_p > 0 else 'All'}"
            scroll_str = "Scroll: ON" if settings.get('scroll_mode') else "Scroll: OFF"
            delay_str = f"Delay: {settings.get('delay', 0)}s"
            settings_summary = f"{pages_str} | {scroll_str} | {delay_str}"
            self.table.setItem(idx, 3, QTableWidgetItem(settings_summary))
            
            self.table.setItem(idx, 4, QTableWidgetItem(str(job['created_at'])))
            self.table.setItem(idx, 5, QTableWidgetItem(str(job['updated_at'])))
            
            view_btn = QPushButton("View Result")
            view_btn.clicked.connect(lambda checked, r_id=job['id']: self.viewModel.get_job_details(r_id))
            self.table.setCellWidget(idx, 6, view_btn)

    def set_status_color(self, item, status):
        if status == JobStatus.COMPLETED:
            item.setForeground(Qt.green)
        elif status == JobStatus.FAILED:
            item.setForeground(Qt.red)
        elif status == JobStatus.RUNNING:
            item.setForeground(Qt.blue)
        else:
            item.setForeground(Qt.gray)

    def show_context_menu(self, pos):
        item = self.table.itemAt(pos)
        if not item: return
        
        row = item.row()
        job_id = int(self.table.item(row, 0).text())
        
        menu = QMenu()
        view_action = menu.addAction("View Details")
        delete_action = menu.addAction("Delete Job")
        
        action = menu.exec(self.table.mapToGlobal(pos))
        if action == view_action:
            self.viewModel.get_job_details(job_id)
        elif action == delete_action:
            self.viewModel.delete_job(job_id)

    def on_clear_all_clicked(self):
        reply = QMessageBox.question(self, 'Confirm Clear', 'Are you sure you want to delete ALL jobs?', 
                                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.viewModel.clear_all_jobs()

    def on_error(self, error_msg):
        QMessageBox.warning(self, "Error", error_msg)
