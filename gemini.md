# Universal Web Scraper Desktop - Technical Analysis & Workflow

This document serves as a comprehensive guide for AI agents (like Gemini) to understand the architecture, logic flow, and implementation details of the Universal Web Scraper Desktop project.

---

## 1. Project Overview
- **Goal**: A professional desktop GUI for web scraping that handles JS rendering, anti-detection, pagination, infinite scrolling, and AI-powered data extraction.
- **Core Tech Stack**:
    - **GUI**: PySide6 (Qt for Python)
    - **Engine**: Crawl4AI (Playwright-based)
    - **AI Extraction**: LiteLLM (OpenAI, Anthropic, Google, Groq, etc.)
    - **Persistence**: SQLite (via standard `sqlite3` library)
    - **Async**: `qasync` (integrates asyncio with Qt event loop)
    - **Validation**: Pydantic
    - **Logging**: Loguru
    - **Parsing**: BeautifulSoup4

---

## 2. Modular Architecture (Separation of Concerns)

### `config/`
- `settings.py`: Global constants (AI Providers, defaults).

### `database/` (Persistence Layer)
- `models.py`: Pydantic models for `JobRecord`, `JobSettings`, and `JobStatus`.
- `repository.py`: `SQLiteJobRepository` for CRUD operations on jobs.

### `models/`
- `scraper_input.py`: Defines `ProxyConfig` and `LLMConfig`.

### `utils/`
- `proxy_parser.py`: Proxy list parsing.
- `file_manager.py`: File I/O.
- `pagination.py`: Universal pagination logic.
- `scrolling.py`: Sequential JS scrolling.

### `core/` (The Logic Heart)
- `crawler_engine.py`: `WebCrawlerService` with multi-page, proxy rotation, and AI extraction support.
- `extraction.py`: `LLMExtractor` wrapping `crawl4ai.LLMExtractionStrategy`.
- `ai_handler.py`: Centralized factory (`get_smart_ai_strategy`) for configuring AI strategies with chunking and JSON enforcement.
- `job_service.py`: Business logic for job queue management (enqueue, next, complete/fail).

### `ui/` (The Presentation Layer)
- `main_window.py`: Main GUI orchestrating tabs (Crawler, Job Queue) and settings.
- `job_manager.py`: `JobManagerWidget` for viewing and managing the job queue/history.
- `workers.py`: `CrawlWorker` (single run), `JobQueueWorker` (background queue processor), and `AITestWorker`.

---

## 3. Detailed Workflow (Data Flow)

### A. Direct Crawl
1.  **User Input**: URL, Proxies, and AI Settings.
2.  **Start**: User clicks "Start Crawl".
3.  **Execution**: `CrawlWorker` initializes `WebCrawlerService`.
4.  **Scraping Loop**:
    - Engine rotates proxy.
    - Injects Scroll JS.
    - Calls `crawler.arun()` with `LLMExtractionStrategy` (configured via `ai_handler.py`).
    - Collects Markdown and structured JSON data.
    - Resolves next URL (pagination).
5.  **Output**: Saves `.md` and `.json` to `outputs/`.

### B. Job Queue System
1.  **Enqueue**: User clicks "Add to Queue".
2.  **Persistence**: `JobRecord` is saved to SQLite (`jobs.db`) with status `PENDING`.
3.  **Background Processing**: `JobQueueWorker` polls for pending jobs.
4.  **Execution**: When a job is picked up:
    - Status updates to `RUNNING`.
    - `WebCrawlerService` executes the job settings.
5.  **Completion**:
    - Success: Status `COMPLETED`, results stored in DB (path) and disk.
    - Failure: Status `FAILED`, error message stored.
6.  **Monitoring**: `JobManagerWidget` auto-refreshes to show status changes.

---

## 4. Key Implementation Rules for AI
- **AI Extraction**: ALWAYS use `core.ai_handler.get_smart_ai_strategy` to ensure consistent JSON formatting and chunking configuration.
- **Job Persistence**: All long-running tasks should be capable of running via the Job Queue mechanism.
- **Database Access**: Use `SQLiteJobRepository` for all DB interactions; do not use raw SQL in UI or Service layers.
- **Non-Blocking UI**: Critical. Use `qasync` for async/await in Qt slots and Workers for long-running processes.