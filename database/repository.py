import sqlite3
import json
from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import datetime
from .models import JobRecord, JobStatus, JobSettings
from config.settings import DB_CONFIG

class IJobRepository(ABC):
    @abstractmethod
    def add_job(self, job: JobRecord) -> int:
        pass

    @abstractmethod
    def get_job(self, job_id: int) -> Optional[JobRecord]:
        pass

    @abstractmethod
    def update_job_status(self, job_id: int, status: JobStatus, result: Optional[dict] = None, error: Optional[str] = None):
        pass

    @abstractmethod
    def get_pending_jobs(self) -> List[JobRecord]:
        pass

    @abstractmethod
    def delete_all_jobs(self):
        pass

class SQLiteJobRepository(IJobRepository):
    def __init__(self, db_path: str = DB_CONFIG["DB_PATH"]):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    status TEXT NOT NULL,
                    settings TEXT NOT NULL,
                    result TEXT,
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def add_job(self, job: JobRecord) -> int:
        with self._get_connection() as conn:
            cursor = conn.execute(
                "INSERT INTO jobs (status, settings, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (job.status.value, job.settings.model_dump_json(), job.created_at, job.updated_at)
            )
            return cursor.lastrowid

    def get_job(self, job_id: int) -> Optional[JobRecord]:
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
            if row:
                return self._row_to_model(row)
        return None

    def update_job_status(self, job_id: int, status: JobStatus, result: Optional[dict] = None, error: Optional[str] = None):
        with self._get_connection() as conn:
            conn.execute(
                "UPDATE jobs SET status = ?, result = ?, error_message = ?, updated_at = ? WHERE id = ?",
                (status.value, json.dumps(result) if result else None, error, datetime.now(), job_id)
            )

    def get_pending_jobs(self) -> List[JobRecord]:
        with self._get_connection() as conn:
            rows = conn.execute("SELECT * FROM jobs WHERE status = ? ORDER BY created_at ASC", (JobStatus.PENDING.value,)).fetchall()
            return [self._row_to_model(row) for row in rows]

    def delete_all_jobs(self):
        with self._get_connection() as conn:
            conn.execute("DELETE FROM jobs")
            conn.commit()

    def _row_to_model(self, row: sqlite3.Row) -> JobRecord:
        return JobRecord(
            id=row['id'],
            status=JobStatus(row['status']),
            settings=JobSettings.model_validate_json(row['settings']),
            result=json.loads(row['result']) if row['result'] else None,
            error_message=row['error_message'],
            created_at=datetime.fromisoformat(row['created_at']) if isinstance(row['created_at'], str) else row['created_at'],
            updated_at=datetime.fromisoformat(row['updated_at']) if isinstance(row['updated_at'], str) else row['updated_at']
        )
