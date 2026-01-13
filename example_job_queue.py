from database.repository import SQLiteJobRepository
from database.models import JobSettings
from core.job_service import JobService

def main():
    # Initialize repository and service
    repo = SQLiteJobRepository("crawl_jobs.db")
    service = JobService(repo)

    # 1. Enqueue a job
    settings = JobSettings(
        url="https://example.com",
        max_pages=2,
        scroll_mode=True
    )
    job_id = service.enqueue_job(settings)
    print(f"Job enqueued with ID: {job_id}")

    # 2. Get next pending job
    job = service.get_next_pending_job()
    if job:
        print(f"Processing job {job.id} for {job.settings.url}")
        
        # 3. Mark as running
        service.start_job(job.id)
        
        # ... perform crawl logic here ...
        
        # 4. Mark as completed
        service.complete_job(job.id, {"data": "extracted content", "pages": 2})
        print(f"Job {job.id} completed.")

if __name__ == "__main__":
    main()
