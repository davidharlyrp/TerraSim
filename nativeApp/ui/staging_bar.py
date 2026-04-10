# ui/staging_bar.py
from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QLabel, QFrame
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon, QPixmap

class StagingBar(QWidget):
    """
    A horizontal toolbar for the STAGING tab.
    Action triggers have been moved to the floating TopToolBar.
    """
    run_requested = Signal() # Kept for backward compat if any, but unused

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFixedHeight(34)
        
        # Consistent styling with MeshBar
        self.setStyleSheet("""
            QWidget {
                background-color: #f8fafc;
                border-bottom: 1px solid #e2e8f0;
            }
            QLabel {
                color: #64748b;
                font-size: 11px;
                font-weight: 500;
            }
        """)

        self._build_ui()

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(16)

        # 1. Label
        layout.addWidget(QLabel("Analysis Staging Operations"))
        
        # Separator
        line = QFrame()
        line.setFrameShape(QFrame.VLine)
        line.setStyleSheet("background-color: #e2e8f0; border: none; min-width: 1px; max-width: 1px; margin: 8px 0;")
        layout.addWidget(line)
        
        layout.addStretch()
        # The Run Analysis button has been moved to the floating TopToolBar
