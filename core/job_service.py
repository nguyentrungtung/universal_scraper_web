from typing import List, Optional
from database.repository import IJobRepository
from database.models import JobRecord, JobStatus, JobSettings
from loguru import logger

class JobService:
    def __init__(self, repository: IJobRepository):
        self.repository = repository

    def enqueue_job(self, settings: JobSettings) -> int:
        job = JobRecord(settings=settings)
        job_id = self.repository.add_job(job)
        logger.info(f"Enqueued job {job_id} for URL: {settings.url}")
        return job_id

    def get_next_pending_job(self) -> Optional[JobRecord]:
        pending_jobs = self.repository.get_pending_jobs()
        if pending_jobs:
            return pending_jobs[0]
        return None

    def start_job(self, job_id: int):
        logger.info(f"Starting job {job_id}")
        self.repository.update_job_status(job_id, JobStatus.RUNNING)

    def complete_job(self, job_id: int, result: dict):
        logger.info(f"Completed job {job_id}")
        self.repository.update_job_status(job_id, JobStatus.COMPLETED, result=result)

    def fail_job(self, job_id: int, error_message: str):
        logger.error(f"Failed job {job_id}: {error_message}")
        self.repository.update_job_status(job_id, JobStatus.FAILED, error=error_message)

    def get_job_status(self, job_id: int) -> Optional[JobRecord]:
        return self.repository.get_job(job_id)

    def delete_all_jobs(self):
        logger.info("Deleting all jobs from queue")
        self.repository.delete_all_jobs()
