import sys
import asyncio
import qasync
from PySide6.QtWidgets import QApplication
from ui.views.main_window import MainWindow
from loguru import logger

def main():
    # Setup Loguru
    logger.remove()
    logger.add(sys.stderr, level="INFO")
    import os
    base_dir = os.path.dirname(os.path.abspath(__file__))
    log_dir = os.path.join(base_dir, "logs")
    os.makedirs(log_dir, exist_ok=True)
    
    logger.add(os.path.join(log_dir, "scraper.log"), rotation="10 MB", retention="10 days", level="DEBUG")
    logger.add(os.path.join(log_dir, "ai_trace.log"), filter=lambda record: "ai_trace" in record["extra"], rotation="10 MB", level="TRACE")
    
    app = QApplication(sys.argv)
    
    # Integrate asyncio with Qt
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)
    
    window = MainWindow()
    window.show()
    
    with loop:
        loop.run_forever()

if __name__ == "__main__":
    main()
