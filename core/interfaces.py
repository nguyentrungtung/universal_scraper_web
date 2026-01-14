from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union

class IPageFetcher(ABC):
    """Interface for fetching web pages."""
    
    @abstractmethod
    async def fetch(self, url: str, config: Dict[str, Any]) -> Any:
        """
        Fetches a page and returns the result (HTML/Markdown).
        
        Args:
            url: The URL to fetch.
            config: Configuration dictionary (proxy, wait_for, etc.).
            
        Returns:
            A result object containing markdown, html, etc.
        """
        pass

class ILLMProvider(ABC):
    """Interface for AI/LLM providers."""
    
    @abstractmethod
    async def extract(self, content: str, instruction: str, schema: Optional[Dict] = None) -> List[Dict]:
        """
        Extracts structured data from content using AI.
        
        Args:
            content: The text content (markdown) to process.
            instruction: The system instruction/prompt.
            schema: Optional JSON schema to enforce.
            
        Returns:
            A list of extracted dictionaries.
        """
        pass

class IStorageService(ABC):
    """Interface for data storage/streaming."""
    
    @abstractmethod
    def append_data(self, data: List[Dict]):
        """Appends structured data to storage."""
        pass
        
    @abstractmethod
    def append_content(self, content: str):
        """Appends raw content (markdown) to storage."""
        pass
    
    @abstractmethod
    def finalize(self) -> List[str]:
        """Finalizes storage (closes files) and returns file paths."""
        pass
