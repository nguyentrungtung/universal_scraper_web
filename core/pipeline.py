import asyncio
import time
from typing import List, Dict, Optional, Callable
from loguru import logger

from core.interfaces import ILLMProvider
from utils.content_splitter import ContentSplitter
from config.settings import AI_CONFIG

class ExtractionPipeline:
    """
    Manages the data extraction pipeline:
    1. Split content into blocks.
    2. Batch blocks.
    3. Send batches to AI Provider.
    4. Aggregate results.
    """
    
    def __init__(self, provider: ILLMProvider, config: Optional[Dict] = None):
        self.provider = provider
        self.config = config or AI_CONFIG

    async def run(self, markdown: str, instruction: str, schema: Optional[Dict] = None, 
                  split_pattern: Optional[str] = None, 
                  progress_callback: Optional[Callable[[int], None]] = None,
                  stream_callback: Optional[Callable[[List[Dict]], None]] = None) -> List[Dict]:
        
        # 1. Split
        blocks = ContentSplitter.split_markdown_to_blocks(
            markdown, 
            max_chars=self.config.get("MAX_CHARS_PER_BLOCK", 4000),
            ai_split_pattern=split_pattern
        )
        logger.info(f"Split content into {len(blocks)} blocks.")
        
        # 2. Batch
        batch_size = self.config.get("BATCH_SIZE", 5)
        batched_blocks = ["\n\n".join(blocks[i:i + batch_size]) for i in range(0, len(blocks), batch_size)]
        total_batches = len(batched_blocks)
        
        extracted_items = []
        
        # Concurrency Control
        concurrency = self.config.get("CONCURRENT_REQUESTS", 3)
        semaphore = asyncio.Semaphore(concurrency)
        
        completed_count = [0] # Mutable for closure

        # 3. Execute
        tasks = [
            self._process_batch(
                i, batch, total_batches, instruction, schema, 
                semaphore, completed_count, progress_callback, stream_callback
            ) 
            for i, batch in enumerate(batched_blocks)
        ]
        results = await asyncio.gather(*tasks)
        
        # 4. Flatten
        for res in results:
            extracted_items.extend(res)
            
        return extracted_items

    async def _process_batch(self, i: int, batch_content: str, total_batches: int, 
                             instruction: str, schema: Optional[Dict],
                             semaphore: asyncio.Semaphore, completed_count: List[int],
                             progress_callback: Optional[Callable], stream_callback: Optional[Callable]) -> List[Dict]:
        async with semaphore:
            try:
                logger.debug(f"Processing batch {i+1}/{total_batches}...")
                
                content_len = len(batch_content)
                log_context = f"Batch {i+1} | Size: {content_len} chars"
                logger.info(f"Sending {log_context} to AI...")
                
                # Trace Log Input
                separator = "=" * 50
                trace_msg = (
                    f"\n{separator}\n"
                    f"BATCH {i+1} REQUEST\n"
                    f"Length: {content_len} chars\n"
                    f"{separator}\n"
                    f"{batch_content}\n"
                    f"{separator}\n"
                )
                logger.bind(ai_trace=True).trace(trace_msg)

                start_time = time.time()
                
                items = await self.provider.extract(batch_content, instruction, schema)
                
                elapsed = time.time() - start_time
                
                if items:
                    logger.info(f"Batch {i+1} SUCCESS | Extracted: {len(items)} items | Time: {elapsed:.2f}s")
                    # Trace Log Output
                    trace_resp = (
                        f"\n{separator}\n"
                        f"BATCH {i+1} RESPONSE (Time: {elapsed:.2f}s)\n"
                        f"{separator}\n"
                        f"{items}\n"
                        f"{separator}\n"
                    )
                    logger.bind(ai_trace=True).trace(trace_resp)
                    
                    if stream_callback:
                        stream_callback(items)
                    return items
                else:
                    logger.warning(f"Batch {i+1} EMPTY | Time: {elapsed:.2f}s | Content Preview: {batch_content[:100]}...")
                    logger.bind(ai_trace=True).trace(f"\n{separator}\nBATCH {i+1} RESPONSE: EMPTY\n{separator}\n")
                    return []
            except Exception as e:
                logger.error(f"Batch {i+1} FAILED | Error: {e}")
                logger.bind(ai_trace=True).error(f"\n{separator}\nBATCH {i+1} ERROR:\n{str(e)}\n{separator}\n")
                return []
            finally:
                completed_count[0] += 1
                if progress_callback:
                    percent = int((completed_count[0] / total_batches) * 100)
                    progress_callback(percent)
