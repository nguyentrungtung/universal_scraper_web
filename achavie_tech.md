# Project Structure & Technical Architecture (Achavie Tech)

This document provides a high-level overview of the project's directory structure, technical architecture, and recent improvements.

## 1. Directory Tree

```text
crawl-tool/
├── main.py                 # Application entry point
├── requirements.txt        # Project dependencies (PySide6, crawl4ai, litellm, etc.)
├── gemini.md               # Detailed technical guide & workflow
├── achavie_tech.md         # Project structure overview (this file)
├── config/
│   └── settings.py         # CENTRALIZED CONFIGURATION (AI, Crawl, DB, Paths, UI)
├── core/                   # Business Logic
│   ├── crawler_engine.py   # WebCrawlerService (Handles loop, proxies, AI Batching, Filtering)
│   ├── extraction.py       # LLMExtractor (AI Extraction Strategy)
│   ├── ai_handler.py       # AI Strategy Factory
│   └── job_service.py      # Job Management Service
├── database/               # Persistence Layer
│   ├── models.py           # Database Models (JobRecord, JobSettings)
│   └── repository.py       # SQLiteJobRepository (Job Queue Management)
├── models/                 # Data Models
│   └── scraper_input.py    # Pydantic models (ProxyConfig, LLMConfig)
├── templates/              # Configuration Templates
│   ├── prompts.json        # Pre-defined AI Prompts
│   └── schemas.json        # Pre-defined JSON Schemas
├── ui/                     # Presentation Layer
│   ├── main_window.py      # Main GUI
│   ├── settings_widgets.py # Settings UI (AI & Crawl Configs)
│   ├── job_manager.py      # Job Queue UI
│   ├── workers.py          # Async QThreads (CrawlWorker, JobQueueWorker)
│   └── components.py       # Reusable widgets
├── utils/                  # Helper Utilities
│   ├── ai_parser.py        # Smart Markdown Splitting & JSON Parsing
│   ├── result_handler.py   # Result saving logic
│   ├── proxy_parser.py     # Proxy parsing
│   └── ...
├── logs/                   # Application Logs
│   ├── scraper.log         # General Application Log
│   ├── ai_errors.log       # AI Error Log
│   └── ai_processing_details.log # Detailed AI Batch Logs (Full Content)
└── outputs/                # Scraped data (.md and .json)
```

## 2. Key Technical Features & Improvements

### A. Centralized Configuration (`config/settings.py`)
All hardcoded values have been moved to a single source of truth:
-   **AI_CONFIG**: Controls `MAX_CHARS_PER_BLOCK` (10k chars), `BATCH_SIZE`, `TEMPERATURE`.
-   **CRAWL_CONFIG**: Controls `DEFAULT_TIMEOUT`, `RETRY_ATTEMPTS`, `RETRY_DELAY`.
-   **PATHS_CONFIG**: Manages all file and directory paths.
-   **UI_CONFIG**: Default UI settings.
-   **DEFAULT_AI_URLS**: Base URLs for various AI providers (Ollama, LM Studio, etc.).

### B. Robust AI Extraction Engine
The extraction engine has been significantly upgraded to handle large documents and prevent "Context Overflow":
1.  **Smart Markdown Splitting (`utils/ai_parser.py`)**:
    -   Automatically splits large Markdown content into smaller blocks based on `MAX_CHARS_PER_BLOCK` (default 10,000 chars).
    -   Respects logical boundaries (newlines, link blocks) to avoid breaking data mid-record.
2.  **Batch Processing (`core/crawler_engine.py`)**:
    -   Processes blocks sequentially (or in parallel batches).
    -   **Detailed Logging**: Records full input content and AI response for every batch in `logs/ai_processing_details.log`. This allows for precise debugging of what was sent to the AI.
3.  **Error Handling**:
    -   Catches `ContextWindowExceededError` and other AI provider errors.
    -   Logs failed batches with full content for analysis.

### C. Advanced Crawling & Filtering
-   **Noise Reduction**: `CrawlerRunConfig` is configured to exclude:
    -   Tags: `nav`, `footer`, `header`, `script`, `iframe`, etc.
    -   Selectors: `.ads`, `.sidebar`, `.menu`, `.social-share`.
    -   External links and social media domains.
-   **Anti-Detect**: "Magic Mode" and Proxy Rotation support.

### D. Job Queue System (`database/`)
-   **SQLite Backend**: Persistent job queue using `crawl_jobs.db`.
-   **Job Management**: Add URLs to queue, track status (PENDING, RUNNING, COMPLETED, FAILED), and view results.

### E. User Interface Enhancements
-   **Template Auto-Selection**: Selecting a Prompt Template automatically selects the corresponding Schema Template (e.g., "Real Estate" prompt -> "Real Estate" schema).
-   **Dynamic Settings**: UI elements load defaults from `settings.py`.

## 3. Workflow Summary

1.  **Input**: User enters URL, configures Proxy/Crawl settings, and selects AI Provider/Template.
2.  **Crawl**: `AsyncWebCrawler` fetches pages, executes JS (scrolling), and filters noise.
3.  **Process**:
    -   HTML converted to Markdown.
    -   Markdown split into safe blocks (`ai_parser.py`).
    -   Blocks sent to AI Provider (LiteLLM) in batches.
4.  **Extract**: AI returns JSON -> Parsed & Validated -> Deduplicated.
5.  **Save**: Results saved to `outputs/` (Markdown + JSON). Logs recorded in `logs/`.
