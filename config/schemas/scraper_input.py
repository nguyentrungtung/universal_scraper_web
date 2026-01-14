from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, HttpUrl, field_validator
from config.settings import CRAWL_CONFIG

class ProxyConfig(BaseModel):
    server: str = Field(..., description="Proxy server address (e.g., http://ip:port)")
    username: Optional[str] = None
    password: Optional[str] = None

    @field_validator('server')
    @classmethod
    def validate_server(cls, v):
        if not v.startswith(('http://', 'https://', 'socks5://')):
            # Default to http if no protocol specified
            return f"http://{v}"
        return v

class LLMConfig(BaseModel):
    provider: str = Field("openai", description="LLM Provider (openai, anthropic, google, etc.)")
    model_name: str = Field("gpt-4o", description="Model name (e.g., gpt-4o, claude-3-5-sonnet)")
    api_key: str = Field(..., description="API Key for the provider")
    base_url: Optional[str] = Field(None, description="Base URL for local LLMs like Ollama")
    instruction: str = Field("Extract the main entities and their attributes from the page content.", description="Extraction instructions for the AI")
    response_schema: Optional[str] = Field(None, description="JSON schema for structured extraction")
    ai_split_pattern: Optional[str] = Field(None, description="Regex pattern to split markdown content for AI context (e.g., '\\n(?=\\[)').")
    use_proxy: bool = Field(False, description="Whether to use proxy for AI requests")

class ScraperInput(BaseModel):
    url: HttpUrl
    proxy: Optional[ProxyConfig] = None
    magic_mode: bool = False
    extraction_schema: Optional[Dict[str, Any]] = None
    llm_config: Optional[LLMConfig] = None
    timeout: int = CRAWL_CONFIG["DEFAULT_TIMEOUT"]  # ms

class CrawlRunConfig(BaseModel):
    url: str
    max_pages: int = 1
    scroll_mode: bool = False
    magic_mode: bool = False
    scroll_depth: int = 5
    delay: int = 0
    proxies: Optional[list[ProxyConfig]] = None
    llm_config: Optional[LLMConfig] = None
