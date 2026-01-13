import json
import re
import uuid
from typing import List, Any, Dict
from loguru import logger

def extract_json_from_text(text: str) -> tuple[Any, str | None]:
    """
    Trích xuất và parse JSON từ văn bản thô.
    Returns: (data, error_message)
    """
    if not text:
        return None, "Empty input text"
        
    if isinstance(text, (list, dict)):
        return text, None
        
    if not isinstance(text, str):
        return None, f"Invalid input type: {type(text)}"
        
    text = text.strip()
    
    # 1. Try to find JSON within markdown code blocks first
    markdown_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
    if markdown_match:
        try:
            return json.loads(markdown_match.group(1)), None
        except json.JSONDecodeError as e:
            return None, f"Markdown block JSON decode error: {e}"

    # 2. Try parsing the whole text (cleaned)
    try:
        return json.loads(text), None
    except json.JSONDecodeError:
        pass

    # 3. Find the outermost list [...] or object {...}
    try:
        # Find start and end of list
        start_list = text.find('[')
        end_list = text.rfind(']')
        
        # Find start and end of object
        start_obj = text.find('{')
        end_obj = text.rfind('}')
        
        candidate = None
        
        # Determine which one is the valid outer container
        if start_list != -1 and end_list != -1 and end_list > start_list:
            # Check if this list wraps the object (if object exists)
            if start_obj != -1:
                if start_list < start_obj and end_list > end_obj:
                    candidate = text[start_list:end_list+1]
                elif start_obj < start_list: # Object is outer
                    candidate = text[start_obj:end_obj+1]
                else: # List is outer or standalone
                    candidate = text[start_list:end_list+1]
            else:
                candidate = text[start_list:end_list+1]
        elif start_obj != -1 and end_obj != -1 and end_obj > start_obj:
            candidate = text[start_obj:end_obj+1]
            
        if candidate:
            # Fix common trailing comma issues: ,] -> ] and ,} -> }
            candidate = re.sub(r',\s*\]', ']', candidate)
            candidate = re.sub(r',\s*\}', '}', candidate)
            try:
                return json.loads(candidate), None
            except json.JSONDecodeError as e:
                return None, f"Substring JSON decode error: {e}"
            
    except Exception as e:
        return None, f"Unexpected error during extraction: {e}"

    return None, "No valid JSON structure found in text"



def clean_and_deduplicate_items(items: List[Dict[str, Any]], existing_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Làm sạch dữ liệu và đảm bảo ID không bị trùng lặp.
    """
    if not isinstance(items, list):
        items = [items] if isinstance(items, dict) else []

    processed_items = []
    existing_ids = {item.get('id') for item in existing_data if item.get('id')}
    
    for item in items:
        if not isinstance(item, dict):
            continue
            
        # Đảm bảo có ID
        if not item.get('id'):
            # Tạo ID từ title nếu có, không thì dùng uuid
            title = item.get('title', '')
            if title:
                item['id'] = re.sub(r'[^\w\s-]', '', title).strip().lower().replace(' ', '-')[:30]
            else:
                item['id'] = str(uuid.uuid4())[:8]
        
        # Xử lý trùng ID
        base_id = str(item['id'])
        counter = 1
        while item['id'] in existing_ids:
            item['id'] = f"{base_id}-{counter}"
            counter += 1
            
        existing_ids.add(item['id'])
        processed_items.append(item)
        
    return processed_items
