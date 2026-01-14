import json
import os
import re
from urllib.parse import urlparse
from datetime import datetime
from typing import Dict, Any, List
from loguru import logger
from utils.file_manager import ensure_dir
from config.settings import PATHS_CONFIG

def _get_domain_from_url(url: str) -> str:
    try:
        parsed = urlparse(url)
        domain = parsed.netloc or parsed.path
        # Remove www.
        if domain.startswith("www."):
            domain = domain[4:]
        # Replace non-alphanumeric with _
        return re.sub(r'[^a-zA-Z0-9]', '_', domain)
    except:
        return "unknown_site"

class ResultHandler:
    @staticmethod
    def save_result(data: Dict[str, Any], log_callback=None) -> List[str]:
        """
        Lưu kết quả cuối cùng (Legacy method - dùng cho các job nhỏ hoặc tương thích ngược).
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = PATHS_CONFIG["OUTPUT_DIR"]
        ensure_dir(output_dir)

        # Generate filename prefix based on URL if available
        prefix = "crawl"
        if data.get("url"):
            domain = _get_domain_from_url(data["url"])
            prefix = f"{domain}_{timestamp}"
        else:
            prefix = f"crawl_{timestamp}"

        saved_files = []

        # 1. Save Markdown
        if data.get("markdown"):
            # If markdown is just a path (from StreamResultHandler), don't save again unless it's content
            if data["markdown"].startswith("Saved to"):
                pass # Already saved
            else:
                md_filename = f"{prefix}.md"
                md_path = os.path.join(output_dir, md_filename)
                try:
                    with open(md_path, "w", encoding="utf-8") as f:
                        f.write(data["markdown"])
                    saved_files.append(md_path)
                    if log_callback: log_callback(f"Saved Markdown: {md_path}")
                except Exception as e:
                    logger.error(f"Failed to save markdown: {e}")

        # 2. Save JSON Data
        if data.get("extracted_data"):
            json_filename = f"{prefix}.json"
            json_path = os.path.join(output_dir, json_filename)
            try:
                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump(data["extracted_data"], f, ensure_ascii=False, indent=2)
                saved_files.append(json_path)
                if log_callback: log_callback(f"Saved JSON: {json_path}")
            except Exception as e:
                logger.error(f"Failed to save JSON: {e}")

        return saved_files

class StreamResultHandler:
    """
    Xử lý việc lưu dữ liệu theo luồng (Stream) để tiết kiệm bộ nhớ.
    """
    def __init__(self, job_id: str = None, url: str = None):
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if job_id:
            self.job_id = job_id
        else:
            # Generate job_id based on URL if provided
            if url:
                domain = _get_domain_from_url(url)
                self.job_id = f"{domain}_{self.timestamp}"
            else:
                self.job_id = f"crawl_{self.timestamp}"
        
        # Tạo đường dẫn file
        output_dir = PATHS_CONFIG["OUTPUT_DIR"]
        ensure_dir(output_dir)
        
        self.md_file = os.path.join(output_dir, f"{self.job_id}.md")
        self.json_file = os.path.join(output_dir, f"{self.job_id}.json")
        
        # Khởi tạo file rỗng
        self._init_files()

    def _init_files(self):
        # Init Markdown
        with open(self.md_file, "w", encoding="utf-8") as f:
            f.write(f"# Crawl Result for Job: {self.job_id}\n")
            f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
        # Init JSON (Start with empty list)
        with open(self.json_file, "w", encoding="utf-8") as f:
            f.write("[\n")

    def append_markdown(self, content: str):
        """Ghi nối nội dung markdown vào file"""
        try:
            with open(self.md_file, "a", encoding="utf-8") as f:
                f.write(content + "\n\n")
        except Exception as e:
            logger.error(f"Failed to append markdown: {e}")

    def append_data(self, items: List[Dict]):
        """Ghi nối dữ liệu JSON vào file (xử lý dấu phẩy)"""
        if not items:
            return
            
        try:
            json_str = ""
            for item in items:
                json_str += "  " + json.dumps(item, ensure_ascii=False) + ",\n"
            
            with open(self.json_file, "a", encoding="utf-8") as f:
                f.write(json_str)
                
        except Exception as e:
            logger.error(f"Failed to append JSON data: {e}")

    def finalize(self):
        """Đóng file JSON đúng cú pháp"""
        try:
            # Xóa dấu phẩy cuối cùng và đóng ngoặc vuông
            with open(self.json_file, 'rb+') as f:
                f.seek(0, 2) # Move to end
                file_size = f.tell()
                
                # Check last few bytes to find the comma
                # We might have written ",\n" or ",\r\n"
                # Let's look back up to 10 bytes
                search_limit = min(file_size, 10)
                if search_limit > 0:
                    f.seek(-search_limit, 2)
                    tail = f.read(search_limit)
                    
                    # Find the last comma in the tail
                    last_comma_index = tail.rfind(b',')
                    
                    if last_comma_index != -1:
                        # Check if everything after comma is whitespace
                        after_comma = tail[last_comma_index+1:]
                        if after_comma.strip() == b'':
                            # Truncate at the comma
                            # Position of comma = (file_size - search_limit) + last_comma_index
                            truncate_pos = (file_size - search_limit) + last_comma_index
                            f.seek(truncate_pos)
                            f.truncate()
            
            with open(self.json_file, "a", encoding="utf-8") as f:
                f.write("\n]") # Đóng ngoặc
                
            return [self.md_file, self.json_file]
        except Exception as e:
            logger.error(f"Failed to finalize files: {e}")
            return []
