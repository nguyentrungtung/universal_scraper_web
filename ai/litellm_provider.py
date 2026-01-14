import json
import litellm
from typing import Dict, List, Optional, Any
from loguru import logger

from core.interfaces import ILLMProvider
from config.settings import AI_CONFIG
from utils.ai_parser import extract_json_from_text
from utils.ai_parser import extract_json_from_text

def get_litellm_model_name(provider: str, model_name: str) -> str:
    """
    Normalize model name for LiteLLM.
    """
    provider = provider.lower().strip()
    
    # 1. Special cases
    if provider == "lm-studio":
        return f"openai/{model_name}"
        
    if provider == "ollama":
         return f"ollama/{model_name}"

    # 2. Google (LiteLLM uses 'gemini/')
    if provider == "google":
        return f"gemini/{model_name}"
        
    # 3. Default: provider/model_name
    return f"{provider}/{model_name}"

class LiteLLMProvider(ILLMProvider):
    """
    Implementation of ILLMProvider using LiteLLM (OpenAI, Anthropic, etc.).
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Args:
            config: Dictionary containing:
                - provider: str
                - model_name: str
                - api_key: str
                - base_url: str (optional)
                - use_proxy: bool (optional, default False)
        """
        self.config = config
        self.provider = config.get("provider", "openai")
        self.model_name = config.get("model_name", "gpt-3.5-turbo")
        self.api_key = config.get("api_key")
        self.base_url = config.get("base_url")
        self.proxy = config.get("proxy")
        self.use_proxy = config.get("use_proxy", False)

        
    async def extract(self, content: str, instruction: str, schema: Optional[Dict] = None) -> List[Dict]:
        try:
            # Simplify prompt for local models
            if self.base_url:
                # Local model: simpler, more direct prompt
                final_instruction = f"{instruction}\n\nReturn valid JSON array of objects. Example: [{{'field': 'value'}}]"
            else:
                # Cloud model: can handle more complex prompts
                final_instruction = instruction
                if schema:
                    final_instruction += f"\n\nOutput must strictly follow this JSON schema:\n{json.dumps(schema, indent=2)}"
                
                if "json" not in final_instruction.lower():
                    final_instruction += "\n\nReturn the results in valid JSON format."
                    
                final_instruction += "\n\nReturn ONLY the JSON object/list. No markdown formatting, no explanations."

            messages = [
                {"role": "system", "content": final_instruction},
                {"role": "user", "content": content}
            ]
            
            full_model = get_litellm_model_name(self.provider, self.model_name)

            # Increase timeout for local models (they are slower)
            timeout = 300 if self.base_url else 120  # 5 minutes for local, 2 for cloud

            kwargs = {
                "model": full_model,
                "messages": messages,
                "api_key": self.api_key,
                "base_url": self.base_url,
                "temperature": AI_CONFIG.get("TEMPERATURE", 0.1),
                "timeout": timeout
            }
            
            # Only use proxy if explicitly enabled
            if self.use_proxy and self.proxy:
                kwargs["proxy"] = self.proxy

            
            # Enable JSON mode for supported providers
            # IMPORTANT: Disable if base_url is set, as many local bridges (LM Studio/Local Proxy) 
            # do not support the response_format parameter and will fail or return junk.
            if self.provider in ["openai", "google", "ollama", "groq"] and not self.base_url:
                 kwargs["response_format"] = {"type": "json_object"}

            logger.debug(f"Calling LLM with timeout={timeout}s, content_length={len(content)}")
            response = await litellm.acompletion(**kwargs)
            
            response_content = response.choices[0].message.content
            
            # Check for empty response
            if not response_content or not response_content.strip():
                logger.warning("AI returned empty response")
                logger.bind(ai_trace=True).trace(f"EMPTY RESPONSE from AI\nFull Response: {response}")
                return []
            
            # Parse JSON using existing utility
            data, error = extract_json_from_text(response_content)
            
            if error:
                logger.warning(f"JSON Parsing Error: {error}")
                logger.debug(f"Raw Response Content: {response_content[:500]}...")
                # Also log to ai_trace if possible
                logger.bind(ai_trace=True).trace(f"PARSING ERROR: {error}\nRAW CONTENT:\n{response_content}")
                return []
                
            return self._normalize_output(data)


        except Exception as e:
            logger.error(f"LiteLLM Extraction Failed: {e}")
            return []

    def _normalize_output(self, data: Any) -> List[Dict]:
        """Ensures the output is always a list of dicts."""
        if isinstance(data, list):
            return data
        elif isinstance(data, dict):
            # Heuristic: Check if it wraps a list
            for key, value in data.items():
                if isinstance(value, list) and len(value) > 0 and isinstance(value[0], dict):
                    return value
            # Treat dict as single item
            return [data]
        return []
