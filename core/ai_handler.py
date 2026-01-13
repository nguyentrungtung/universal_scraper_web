from typing import Any, Optional
import json
import litellm
from crawl4ai.extraction_strategy import LLMExtractionStrategy
from crawl4ai.async_configs import LLMConfig as CrawlLLMConfig
from crawl4ai.content_filter_strategy import PruningContentFilter
from models.scraper_input import LLMConfig as AppLLMConfig
from config.settings import AI_CONFIG, AI_PROVIDERS, DEFAULT_AI_URLS

# Cấu hình LiteLLM toàn cục
litellm.telemetry = False
litellm.suppress_debug_info = True
litellm.set_verbose = False
litellm.success_callback = []
litellm.failure_callback = []
litellm.callbacks = []
litellm._logging_level = "CRITICAL"
litellm.drop_params = True
litellm.turn_off_message_logging = True

def get_litellm_model_name(provider: str, model_name: str) -> str:
    """
    Chuẩn hóa tên model theo định dạng của LiteLLM dựa trên cấu hình settings.py.
    """
    provider = provider.lower().strip()
    
    # 1. Xử lý các trường hợp đặc biệt (Local LLM giả lập OpenAI)
    if provider == "lm-studio":
        # LM Studio dùng API tương thích OpenAI, nhưng model name giữ nguyên hoặc prefix
        return f"openai/{model_name}"
        
    if provider == "ollama":
         return f"ollama/{model_name}"

    # 2. Xử lý Google (LiteLLM dùng 'gemini/' cho Google AI Studio)
    if provider == "google":
        return f"gemini/{model_name}"
        
    # 3. Mặc định: provider/model_name (openai/gpt-4o, anthropic/claude-3...)
    return f"{provider}/{model_name}"

def get_smart_ai_strategy(config: AppLLMConfig) -> LLMExtractionStrategy:
    """
    Hàm xử lý tập trung logic AI theo chiến lược 3 bước:
    1. Nén dữ liệu (Markdown)
    2. Chia nhỏ (Chunking + Overlap)
    3. Lọc nội dung (Pruning Filter)
    """
    
    # --- BƯỚC 0: Cấu hình Model ---
    full_model_name = get_litellm_model_name(config.provider, config.model_name)
    
    crawl_llm_config = CrawlLLMConfig(
        provider=full_model_name,
        api_token=config.api_key,
        base_url=config.base_url
    )

    # --- BƯỚC 1 & 3: Lọc nội dung rác (Tạm tắt để tránh mất tin đăng) ---
    content_filter = None

    # Sử dụng trực tiếp Instruction từ giao diện/template
    base_instruction = config.instruction

    # Chỉ thêm quy tắc định dạng JSON để đảm bảo kết quả không bị lỗi
    strict_instruction = (
        f"{base_instruction}\n\n"
        "IMPORTANT:\n"
        "1. Extract ALL listings found in the text.\n"
        "2. Return ONLY a JSON array of objects.\n"
        "3. Each object must have: 'id', 'title', 'price', 'area', 'location', 'link_detail', 'source', 'link_url'.\n"
        "4. If no listings found, return [].\n"
        "5. Do NOT output any markdown formatting, code blocks, or explanations. Just the raw JSON.\n"
        "6. Note: Listings often start with '[ ![Image]...' and contain price/area info like '3,3 tỷ · 70 m²'."
    )

    # --- BƯỚC 2: Chiến lược Chia để trị (Chunking) ---
    strategy = LLMExtractionStrategy(
        llm_config=crawl_llm_config,
        instruction=strict_instruction,
        schema=json.loads(config.response_schema) if config.response_schema else None,
        
        apply_chunking=True,
        chunk_token_threshold=AI_CONFIG["CHUNK_TOKEN_THRESHOLD"], 
        overlap_rate=AI_CONFIG["OVERLAP_RATE"],           
        
        input_format="markdown",
        content_filter=content_filter,
        include_raw_html=False,
        verbose=True                
    )
    
    return strategy
