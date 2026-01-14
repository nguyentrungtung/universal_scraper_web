from PySide6.QtCore import Signal
from ui.viewmodels.base_viewmodel import BaseViewModel
from database.repository import SQLiteJobRepository
from database.models import JobStatus
import json

class JobViewModel(BaseViewModel):
    """
    ViewModel for Job Queue management.
    Handles fetching, deleting, and clearing jobs.
    """
    jobs_updated = Signal(list) # List of job dicts/rows
    job_details_ready = Signal(dict) # Single job details
    
    def __init__(self, repo_path: str = "crawl_jobs.db"):
        super().__init__()
        self.repo = SQLiteJobRepository(repo_path)

    def refresh_jobs(self):
        try:
            # We fetch raw rows for performance, or could fetch JobRecord objects
            with self.repo._get_connection() as conn:
                rows = conn.execute("SELECT id, status, settings, created_at, updated_at FROM jobs ORDER BY id DESC LIMIT 100").fetchall()
            
            # Convert to list of dicts for View
            job_list = []
            for row in rows:
                job_list.append({
                    "id": row["id"],
                    "status": row["status"],
                    "settings": json.loads(row["settings"]),
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"]
                })
            
            self.jobs_updated.emit(job_list)
        except Exception as e:
            self.handle_error(f"Failed to refresh jobs: {e}")

    def get_job_details(self, job_id: int):
        job = self.repo.get_job(job_id)
        if job:
            self.job_details_ready.emit(job.model_dump())
        else:
            self.handle_error(f"Job {job_id} not found")

    def delete_job(self, job_id: int):
        try:
            with self.repo._get_connection() as conn:
                conn.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
                conn.commit()
            self.refresh_jobs()
        except Exception as e:
            self.handle_error(f"Failed to delete job: {e}")

    def clear_all_jobs(self):
        try:
            self.repo.delete_all_jobs()
            self.refresh_jobs()
        except Exception as e:
            self.handle_error(f"Failed to clear jobs: {e}")
