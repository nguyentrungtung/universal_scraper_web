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
    - **Streaming**: Custom `StreamResultHandler` for low-memory footprint.

---

## 2. Modular Architecture (Separation of Concerns)

### `config/`
- `settings.py`: Global constants (AI Providers, defaults, paths).

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
- **`content_splitter.py`**: Smart Markdown splitting logic (Token/Char based) to handle large context windows.
- **`result_handler.py`**: `StreamResultHandler` for real-time disk writing.

### `core/` (The Logic Heart)
- **`crawler_engine.py`**: `WebCrawlerService`. Orchestrates the crawl loop: Fetch -> Scroll -> Filter -> **Stream to Disk** -> **Manual Batch Extract**.
- **`extraction.py`**: `ManualBatchExtractor`. Handles the AI extraction loop: Split Markdown -> Batch -> Call AI -> Parse JSON -> Stream Results.
- `ai_handler.py`: Helper for LiteLLM model names and strategies.
- `job_service.py`: Business logic for job queue management.
- **`site_config.py`**: `SiteConfigManager`. Centralized site-specific configurations (selectors, wait conditions, scroll settings).

### `ui/` (The Presentation Layer)
- `main_window.py`: Main GUI orchestrating tabs (Crawler, Job Queue) and settings.
- `job_manager.py`: `JobManagerWidget` for viewing and managing the job queue/history.
- `workers.py`: `CrawlWorker` (single run), `JobQueueWorker` (background queue processor), and `AITestWorker`.

---

## 3. Detailed Workflow (Data Flow)

### A. Direct Crawl (Streaming Architecture)
1.  **User Input**: URL, Proxies, and AI Settings.
2.  **Start**: User clicks "Start Crawl".
3.  **Execution**: `CrawlWorker` initializes `WebCrawlerService`.
4.  **Scraping Loop**:
    -   **Fetch**: Engine rotates proxy, injects Scroll JS, and fetches page.
    -   **Stream**: Raw Markdown is immediately appended to `outputs/[job_id].md`.
    -   **Extract**:
        -   `ManualBatchExtractor` splits markdown into chunks.
        -   Chunks are sent to AI (LiteLLM) in parallel (controlled concurrency).
        -   Extracted JSON items are **immediately streamed** to `outputs/[job_id].json`.
    -   **Pagination**: Resolves next URL and repeats.
5.  **Completion**: Finalizes JSON file syntax (closes array).

### B. Job Queue System
1.  **Enqueue**: User clicks "Add to Queue".
2.  **Persistence**: `JobRecord` is saved to SQLite (`crawl_jobs.db`) with status `PENDING`.
3.  **Background Processing**: `JobQueueWorker` polls for pending jobs.
4.  **Execution**: When a job is picked up:
    -   Status updates to `RUNNING`.
    -   `WebCrawlerService` executes the job settings (using the same Streaming Architecture).
5.  **Completion**:
    -   Success: Status `COMPLETED`, results stored in DB (path to files) and disk.
    -   Failure: Status `FAILED`, error message stored.
6.  **Monitoring**: `JobManagerWidget` auto-refreshes to show status changes.

---

## 4. Key Implementation Rules for AI
-   **Streaming First**: Never hold large datasets in memory. Always use `StreamResultHandler` to write data as it is generated.
-   **Manual Batching**: Do not rely on `crawl4ai`'s built-in extraction strategy for complex/large pages. Use `ManualBatchExtractor` to control splitting and error handling.
-   **Job Persistence**: All long-running tasks should be capable of running via the Job Queue mechanism.
-   **Database Access**: Use `SQLiteJobRepository` for all DB interactions.
-   **Non-Blocking UI**: Critical. Use `qasync` for async/await in Qt slots and Workers.