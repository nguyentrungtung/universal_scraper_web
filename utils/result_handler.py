import json
import os
from datetime import datetime
from typing import Dict, Any, List
from loguru import logger
from utils.file_manager import ensure_dir
from config.settings import PATHS_CONFIG

class ResultHandler:
    @staticmethod
    def save_result(data: Dict[str, Any], log_callback=None) -> List[str]:
        """
        Lưu kết quả cuối cùng (Legacy method - dùng cho các job nhỏ hoặc tương thích ngược).
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = PATHS_CONFIG["OUTPUT_DIR"]
        ensure_dir(output_dir)

        saved_files = []

        # 1. Save Markdown
        if data.get("markdown"):
            md_filename = f"crawl_{timestamp}.md"
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
            json_filename = f"crawl_{timestamp}.json"
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
    def __init__(self, job_id: str = None):
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.job_id = job_id or f"crawl_{self.timestamp}"
        
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
            f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M%S')}\n\n")
            
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
                size = f.tell()
                if size > 2: # Nếu có data (lớn hơn dấu mở [ và xuống dòng)
                    f.seek(-2, 2) # Lùi lại 2 byte (dấu phẩy và xuống dòng)
                    char = f.read(1)
                    if char == b',':
                        f.seek(-1, 1) # Lùi lại chỗ dấu phẩy
                        f.truncate() # Cắt bỏ dấu phẩy
            
            with open(self.json_file, "a", encoding="utf-8") as f:
                f.write("\n]") # Đóng ngoặc
                
            return [self.md_file, self.json_file]
        except Exception as e:
            logger.error(f"Failed to finalize files: {e}")
            return []
