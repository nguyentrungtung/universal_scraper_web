from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
    QTableWidgetItem, QPushButton, QHeaderView, QLabel,
    QMenu
)
from PySide6.QtCore import Qt, Signal, QTimer
from database.repository import SQLiteJobRepository
from database.models import JobStatus
import json

class JobManagerWidget(QWidget):
    job_selected = Signal(dict) # Emits job data when double clicked or selected

    def __init__(self, repo_path: str = "crawl_jobs.db"):
        super().__init__()
        self.repo = SQLiteJobRepository(repo_path)
        self.setup_ui()
        
        # Refresh timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_jobs)
        self.timer.start(3000) # Refresh every 3 seconds

    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("<h2>Job Queue & History</h2>"))
        
        self.refresh_btn = QPushButton("Refresh Now")
        self.refresh_btn.clicked.connect(self.refresh_jobs)
        
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
        
        self.refresh_jobs()

    def refresh_jobs(self):
        # This is a bit heavy for a UI thread if there are thousands of jobs, 
        # but for a local tool it's usually fine.
        with self.repo._get_connection() as conn:
            rows = conn.execute("SELECT id, status, settings, created_at, updated_at FROM jobs ORDER BY id DESC LIMIT 100").fetchall()
        
        self.table.setRowCount(0)
        for row in rows:
            idx = self.table.rowCount()
            self.table.insertRow(idx)
            
            settings = json.loads(row['settings'])
            url = settings.get('url', 'N/A')
            
            self.table.setItem(idx, 0, QTableWidgetItem(str(row['id'])))
            
            status_item = QTableWidgetItem(row['status'])
            self.set_status_color(status_item, row['status'])
            self.table.setItem(idx, 1, status_item)
            
            self.table.setItem(idx, 2, QTableWidgetItem(url))
            
            # Settings Summary
            max_p = settings.get('max_pages', 1)
            pages_str = f"P: {max_p if max_p > 0 else 'All'}"
            scroll_str = "Scroll: ON" if settings.get('scroll_mode') else "Scroll: OFF"
            delay_str = f"Delay: {settings.get('delay', 0)}s"
            settings_summary = f"{pages_str} | {scroll_str} | {delay_str}"
            self.table.setItem(idx, 3, QTableWidgetItem(settings_summary))
            
            self.table.setItem(idx, 4, QTableWidgetItem(str(row['created_at'])))
            self.table.setItem(idx, 5, QTableWidgetItem(str(row['updated_at'])))
            
            view_btn = QPushButton("View Result")
            view_btn.clicked.connect(lambda checked, r_id=row['id']: self.view_job_result(r_id))
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
            self.view_job_result(job_id)
        elif action == delete_action:
            self.delete_job(job_id)

    def view_job_result(self, job_id):
        job = self.repo.get_job(job_id)
        if job:
            # Emit signal to main window to show result
            self.job_selected.emit(job.model_dump())

    def delete_job(self, job_id):
        with self.repo._get_connection() as conn:
            conn.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
            conn.commit()
        self.refresh_jobs()

    def on_clear_all_clicked(self):
        from PySide6.QtWidgets import QMessageBox
        reply = QMessageBox.question(self, 'Confirm Clear', 'Are you sure you want to delete ALL jobs?', 
                                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.repo.delete_all_jobs()
            self.refresh_jobs()
