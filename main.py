import sys
import asyncio
import qasync
from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow
from loguru import logger

def main():
    # Setup Loguru
    logger.remove()
    logger.add(sys.stderr, level="INFO")
    logger.add("scraper.log", rotation="10 MB", level="DEBUG")
    
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
