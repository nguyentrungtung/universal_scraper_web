import re
from typing import List, Optional
from loguru import logger
from config.settings import AI_CONFIG

class ContentSplitter:
    """
    Module chuyên biệt để xử lý logic tách nội dung (Markdown/Text) thành các block nhỏ.
    Hỗ trợ Regex động và các chiến lược fallback.
    """

    @staticmethod
    def split_markdown_to_blocks(markdown: str, max_chars: int = None, ai_split_pattern: str = None) -> List[str]:
        """
        Tách Markdown thành các khối tin đăng để đưa vào AI Context.
        
        Args:
            markdown (str): Nội dung markdown cần tách.
            max_chars (int): Giới hạn ký tự tối đa cho mỗi block (lấy từ config nếu None).
            ai_split_pattern (str): Regex pattern tùy chỉnh để tách block (AI Context Splitting).

        Returns:
            List[str]: Danh sách các block nội dung đã tách.
        """
        if not markdown:
            return []
            
        # Lấy cấu hình mặc định nếu không truyền vào
        if max_chars is None:
            max_chars = AI_CONFIG.get("MAX_CHARS_PER_BLOCK", 4000)

        raw_blocks = []
        
        # 1. Chiến lược 1: Dùng Regex tùy chỉnh (nếu có)
        if ai_split_pattern:
            try:
                # Xử lý ký tự xuống dòng đặc biệt từ UI (ví dụ người dùng nhập \n thì phải hiểu là xuống dòng thật)
                pattern = ai_split_pattern.replace('\\n', '\n')
                raw_blocks = re.split(pattern, markdown)
                logger.info(f"Splitting content using custom AI Context pattern: {repr(pattern)}")
            except Exception as e:
                logger.error(f"Invalid AI split pattern '{ai_split_pattern}': {e}. Falling back to default strategies.")
                
        # 2. Chiến lược 2: Tự động phát hiện Pattern phổ biến (Heuristics)
        if not raw_blocks:
            # Pattern cho Batdongsan.com.vn (bắt đầu bằng link [ )
            if "\n[" in markdown:
                raw_blocks = re.split(r'\n(?=\[)', markdown)
            # Có thể thêm các pattern khác ở đây cho các site khác
            # elif "## " in markdown: ...
            else:
                # Fallback cuối cùng: Tách theo đoạn văn (2 dòng xuống dòng)
                raw_blocks = markdown.split('\n\n')
        
        # 3. Hậu xử lý: Gom nhóm hoặc cắt nhỏ lại để đảm bảo kích thước (Chunking)
        final_blocks = []
        for block in raw_blocks:
            block = block.strip()
            
            # Bỏ qua các block quá ngắn (rác, menu, footer)
            if len(block) <= 300:
                continue

            # Nếu block vẫn quá lớn so với max_chars, cần cắt nhỏ tiếp
            if len(block) > max_chars:
                final_blocks.extend(ContentSplitter._recursive_split(block, max_chars))
            else:
                final_blocks.append(block)
                
        logger.debug(f"Split result: {len(final_blocks)} blocks. Sizes: {[len(b) for b in final_blocks]}")
        return final_blocks

    @staticmethod
    def _recursive_split(text: str, max_chars: int) -> List[str]:
        """
        Hàm đệ quy để cắt nhỏ văn bản quá dài thành các mảnh nhỏ hơn max_chars.
        Ưu tiên cắt ở dấu xuống dòng kép (\n\n), rồi đến đơn (\n), rồi đến cắt cứng.
        """
        if len(text) <= max_chars:
            return [text]
            
        chunks = []
        
        # Thử cắt bằng \n\n
        sub_blocks = text.split('\n\n')
        current_chunk = ""
        
        for sub in sub_blocks:
            # Nếu cộng thêm sub này mà vẫn nhỏ hơn max_chars -> Gom vào
            if len(current_chunk) + len(sub) < max_chars:
                current_chunk += sub + "\n\n"
            else:
                # Nếu đã có dữ liệu gom -> Đẩy vào list
                if current_chunk:
                    chunks.append(current_chunk.strip())
                
                # Reset chunk mới
                current_chunk = sub + "\n\n"
                
                # Trường hợp đặc biệt: Bản thân sub này đã lớn hơn max_chars
                # -> Phải cắt cứng (Hard split)
                if len(current_chunk) > max_chars:
                    while len(current_chunk) > max_chars:
                        chunks.append(current_chunk[:max_chars])
                        current_chunk = current_chunk[max_chars:]
        
        # Đẩy phần dư cuối cùng vào
        if current_chunk:
            chunks.append(current_chunk.strip())
            
        return chunks
