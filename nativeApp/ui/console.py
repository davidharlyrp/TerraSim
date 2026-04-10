# ui/console.py
# ===========================================================================
# TerraSimConsole — Dedicated logging widget for the application
# ===========================================================================

from PySide6.QtWidgets import QPlainTextEdit
from PySide6.QtGui import QColor

class TerraSimConsole(QPlainTextEdit):
    """
    A stylized, read-only console for logging application events,
    errors, and status updates.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setMaximumBlockCount(500)
        
        # Apply modern minimalist aesthetic with custom scrollbar
        self.setStyleSheet("""
            QPlainTextEdit {
                background-color: #fcfcfc;
                border-top: 1px solid #e4e4e7;
                color: #27272a;
                font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
                font-size: 11px;
                padding: 4px;
            }
            QScrollBar:vertical {
                border: none;
                background: #f4f4f5;
                width: 8px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #d4d4d8;
                min-height: 20px;
                border-radius: 4px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

    def log(self, message: str):
        """Append a message with a prompt prefix."""
        self.appendPlainText(f"> {message}")
