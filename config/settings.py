import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "Universal Web Scraper"
    DEFAULT_TIMEOUT: int = 1000
    LOG_LEVEL: str = "INFO"
    USER_AGENT: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
    
    # Browser Configs
    HEADLESS: bool = True
    
    class Config:
        env_file = ".env"

settings = Settings()

# User Agents List
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0"
]

# AI Extraction Configuration
AI_CONFIG = {
    "MAX_CHARS_PER_BLOCK": 4000,   # Reduced to 4000 to safely fit within 4096 token context window (approx 1000-1200 tokens)
    "BATCH_SIZE": 1,               # Number of blocks to process in parallel (or sequential batch)
    "TEMPERATURE": 0.1,            # AI Creativity
    "DEFAULT_MODEL": "gpt-4o-mini",
    "CHUNK_TOKEN_THRESHOLD": 1000, # Token limit for chunking strategy
    "OVERLAP_RATE": 0.1            # Overlap rate between chunks
}

# Crawler Configuration
CRAWL_CONFIG = {
    "DEFAULT_TIMEOUT": 60000,      # Page load timeout (ms)
    "SCROLL_DELAY": 1500,          # Delay between scrolls (ms)
    "RETRY_ATTEMPTS": 3,           # Number of retries for failed pages
    "RETRY_DELAY": 2               # Seconds to wait before retry
}

# Content Filtering Configuration (Crawl4AI)
CONTENT_FILTER_CONFIG = {
    # 1. Lọc theo cấu trúc HTML (Loại bỏ rác)
    "excluded_tags": [
        "nav", "footer", "header", "script", "style", "noscript", "iframe", "svg", "button", "input", "form", 
        "aside", "meta", "link"
    ], # Các thẻ HTML không chứa nội dung hữu ích
    
    "excluded_selector": (
        ".ads, .advertisement, .social-share, .cookie-consent, "
        ".sidebar, .menu, .navigation, .related-posts, .comments, "
        ".popups, .newsletter-signup, .hidden, .display-none, "
        "#header, #footer, .breadcrumb"
    ), # CSS Selector của các thành phần rác (quảng cáo, menu, popup...)
    
    # 2. Lọc theo nội dung Text
    "word_count_threshold": 10,       # Bỏ qua các block text quá ngắn (dưới 10 từ) -> Giúp lọc nút bấm, link rác
    
    # 3. Lọc Link & Media
    "exclude_external_links": True,   # Không lấy link trỏ ra ngoài domain hiện tại
    "exclude_social_media_links": True, # Tự động bỏ link Facebook, Twitter, v.v.
    "exclude_domains": [
        "facebook.com", "twitter.com", "instagram.com", "linkedin.com", 
        "youtube.com", "pinterest.com", "google.com", "googletagmanager.com"
    ], # Danh sách domain đen cần loại bỏ link
    
    "exclude_external_images": True,  # Bỏ ảnh từ nguồn ngoài (thường là quảng cáo)
    
    # 4. Xử lý nâng cao
    "remove_overlay_elements": True,  # Tự động xóa popup/modal che màn hình
    "process_iframes": False,         # Không xử lý nội dung trong iframe (thường là quảng cáo/video nhúng)
    
    # 5. Chọn lọc nội dung (Quan trọng)
    "css_selector": None,             # Nếu set (vd: ".main-content"), chỉ lấy nội dung TRONG selector này. Mặc định lấy body.
    "keep_data_attributes": False     # Giữ lại các thuộc tính data-* (vd: data-id, data-price) nếu cần thiết
}

# AI Provider Constants
AI_PROVIDERS = {
    "openai": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo", "gpt-oss-20b"],
    "anthropic": ["claude-3-5-sonnet-20240620", "claude-3-opus-20240229", "claude-3-sonnet-20240229", "claude-3-haiku-20240307"],
    "google": [
        "gemini-3.0-pro", "gemini-3.0-flash", "gemini-3.0-deep-think",
        "gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.5-flash-lite",
        "gemini-2.0-flash", "gemini-2.0-flash-lite"
    ],
    "groq": ["llama3-70b-8192", "llama3-8b-8192", "mixtral-8x7b-32768", "gemma-7b-it"],
    "ollama": ["llama3", "qwen2", "mistral", "phi3", "gemma2"],
    "lm-studio": ["openai/gpt-oss-20b","meta-llama-3-8b-instruct", "llama3", "qwen2", "gpt-oss-20b", "mistral", "gemma2"]
}

# Database Configuration
DB_CONFIG = {
    "DB_PATH": "crawl_jobs.db"
}

# File Paths
PATHS_CONFIG = {
    "LOG_DIR": "logs",
    "OUTPUT_DIR": "outputs",
    "TEMPLATES_DIR": "templates",
    "PROMPTS_FILE": "templates/prompts.json",
    "SCHEMAS_FILE": "templates/schemas.json",
    "MAIN_LOG_FILE": "scraper.log",
    "AI_ERROR_LOG_FILE": "logs/ai_errors.log"
}

# UI Defaults
UI_CONFIG = {
    "WINDOW_TITLE": "Universal Web Scraper",
    "WINDOW_SIZE": (800, 600),
    "DEFAULT_MAX_PAGES": 1,
    "DEFAULT_SCROLL_DEPTH": 5,
    "DEFAULT_DELAY": 2,
    "DEFAULT_AI_INSTRUCTION": "Extract the main entities and their attributes from the page content."
}

# Default AI Base URLs
DEFAULT_AI_URLS = {
    "ollama": "http://localhost:11434/v1",
    "lm-studio": "http://localhost:1234/v1",
    "openai": "https://api.openai.com/v1",
    "anthropic": "https://api.anthropic.com/v1",
    "google": "https://generativelanguage.googleapis.com/v1beta",
    "groq": "https://api.groq.com/openai/v1"
}
