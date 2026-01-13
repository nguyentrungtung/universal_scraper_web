from abc import ABC, abstractmethod
from typing import Any, List, Dict, Optional
import os
import json
from datetime import datetime
from loguru import logger
import litellm

from crawl4ai.extraction_strategy import LLMExtractionStrategy
from models.scraper_input import LLMConfig as AppLLMConfig
from core.ai_handler import get_smart_ai_strategy, get_litellm_model_name
from config.settings import AI_CONFIG, PATHS_CONFIG
from utils.ai_parser import extract_json_from_text, clean_and_deduplicate_items
from utils.content_splitter import ContentSplitter

class BaseExtractor(ABC):
    @abstractmethod
    def extract(self, html: str) -> Any:
        pass

class LLMExtractor:
    def __init__(self, config: AppLLMConfig):
        self.config = config
        self.strategy = get_smart_ai_strategy(config)

    def get_strategy(self) -> LLMExtractionStrategy:
        return self.strategy

class ManualBatchExtractor:
    """
    Handles manual batch processing of markdown content using LLM.
    Splits content, batches it, calls LLM, and aggregates results.
    """
    def __init__(self, llm_config: AppLLMConfig):
        self.llm_config = llm_config
        # We use the instruction from the config
        self.instruction = llm_config.instruction

    def extract(self, markdown: str, existing_items: List[Dict] = None, progress_callback=None) -> List[Dict]:
        if not existing_items:
            existing_items = []
            
        logger.info("Starting Manual AI Extraction...")
        
        # 1. Split Markdown into logical blocks
        # Get split pattern from LLMConfig if available
        ai_split_pattern = getattr(self.llm_config, 'ai_split_pattern', None)
        
        blocks = ContentSplitter.split_markdown_to_blocks(
            markdown, 
            max_chars=AI_CONFIG["MAX_CHARS_PER_BLOCK"],
            ai_split_pattern=ai_split_pattern
        )
        logger.info(f"Split markdown into {len(blocks)} blocks.")
        
        # 2. Batch blocks
        batch_size = AI_CONFIG["BATCH_SIZE"]
        batched_blocks = ["\n\n".join(blocks[i:i + batch_size]) for i in range(0, len(blocks), batch_size)]
        total_batches = len(batched_blocks)
        
        extracted_items = []
        
        for i, batch_content in enumerate(batched_blocks):
            # Update progress: 30% base + (70% * (current_batch / total_batches))
            if progress_callback:
                current_percent = 30 + int((i / total_batches) * 70)
                progress_callback(current_percent)

            try:
                logger.info(f"Processing batch {i+1}/{total_batches} (Length: {len(batch_content)} chars)...")
                
                # Prepare messages
                # Enhance instruction with schema if available
                final_instruction = self.instruction
                if self.llm_config.response_schema:
                    final_instruction += f"\n\nOutput must strictly follow this JSON schema:\n{self.llm_config.response_schema}"
                    final_instruction += "\n\nReturn ONLY the JSON object/list. No markdown formatting, no explanations."

                messages = [
                    {"role": "system", "content": final_instruction},
                    {"role": "user", "content": batch_content}
                ]
                
                # Construct model name correctly using centralized helper
                full_model = get_litellm_model_name(self.llm_config.provider, self.llm_config.model_name)

                # Call AI
                # Check if provider supports native JSON mode (OpenAI, Gemini, etc.)
                kwargs = {
                    "model": full_model,
                    "messages": messages,
                    "api_key": self.llm_config.api_key,
                    "base_url": self.llm_config.base_url,
                    "temperature": AI_CONFIG["TEMPERATURE"]
                }
                
                # Enable JSON mode for supported providers to ensure valid JSON output
                if self.llm_config.provider in ["openai", "google", "ollama", "groq"]:
                     kwargs["response_format"] = {"type": "json_object"}

                response = litellm.completion(**kwargs)
                
                content = response.choices[0].message.content
                
                # Parse JSON
                batch_data, error_msg = extract_json_from_text(content)
                
                if batch_data:
                    if isinstance(batch_data, list):
                        extracted_items.extend(batch_data)
                    elif isinstance(batch_data, dict):
                        extracted_items.append(batch_data)
                    logger.info(f"Batch {i+1}: Extracted {len(batch_data) if isinstance(batch_data, list) else 1} items.")
                    self._log_batch_details(i, total_batches, batch_content, batch_data, success=True)
                else:
                    reason = error_msg if error_msg else "AI returned empty data"
                    logger.warning(f"Batch {i+1}: Extraction failed. Reason: {reason}")
                    self._log_batch_details(i, total_batches, batch_content, error=reason, success=False)

            except Exception as e:
                logger.error(f"Error processing batch {i+1}: {e}")
                self._log_batch_details(i, total_batches, batch_content, error=str(e), success=False)
        
        # 3. Clean and Deduplicate
        if extracted_items:
            new_items = clean_and_deduplicate_items(extracted_items, existing_items)
            return new_items
        
        return []

    def _log_batch_details(self, batch_idx: int, total_batches: int, input_content: str, result: Any = None, error: str = None, success: bool = True):
        try:
            log_dir = PATHS_CONFIG.get("LOG_DIR", "logs")
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)
                
            ai_log_file = os.path.join(log_dir, "ai_processing_details.log")
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            with open(ai_log_file, "a", encoding="utf-8") as f:
                f.write(f"\n{'='*50}\n")
                f.write(f"TIMESTAMP: {timestamp}\n")
                f.write(f"BATCH: {batch_idx+1}/{total_batches}\n")
                f.write(f"STATUS: {'SUCCESS' if success else 'FAILED'}\n")
                if error:
                    f.write(f"ERROR: {error}\n")
                f.write(f"INPUT LENGTH: {len(input_content)} chars\n")
                if success:
                     f.write(f"EXTRACTED ITEMS: {len(result) if isinstance(result, list) else 1}\n")
                f.write("-" * 20 + " FULL INPUT CONTENT " + "-" * 20 + "\n")
                f.write(input_content + "\n")
                f.write(f"{'='*50}\n")
        except Exception as log_err:
            logger.error(f"Failed to write to AI log: {log_err}")

