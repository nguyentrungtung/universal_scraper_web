from PySide6.QtCore import QObject, Signal

class BaseViewModel(QObject):
    """
    Base class for all ViewModels.
    Provides common signals for error handling and status updates.
    """
    error_occurred = Signal(str)
    status_message = Signal(str)
    
    def __init__(self):
        super().__init__()

    def log(self, message: str):
        self.status_message.emit(message)
        
    def handle_error(self, error: str):
        self.error_occurred.emit(error)
