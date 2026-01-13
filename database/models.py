from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum

class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

from config.settings import UI_CONFIG

class JobSettings(BaseModel):
    url: str
    max_pages: int = UI_CONFIG["DEFAULT_MAX_PAGES"]
    scroll_mode: bool = False
    scroll_depth: int = UI_CONFIG["DEFAULT_SCROLL_DEPTH"]
    magic_mode: bool = False
    delay: int = UI_CONFIG["DEFAULT_DELAY"]
    proxy_config: Optional[Dict[str, Any]] = None
    llm_config: Optional[Dict[str, Any]] = None

class JobRecord(BaseModel):
    id: Optional[int] = None
    status: JobStatus = JobStatus.PENDING
    settings: JobSettings
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
