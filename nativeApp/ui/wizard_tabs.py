from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QFrame
from PySide6.QtCore import Qt, Signal
from core.state import ProjectState

class WizardTabs(QWidget):
    """
    Horizontal navigation wizard showing Input, Mesh, Staging, Result.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(44)
        self.setAttribute(Qt.WA_StyledBackground, True)
        
        self.setObjectName("WizardTabs")
        self.setStyleSheet("""
            QWidget#WizardTabs {
                background-color: #ffffff;
                border-bottom: 1px solid #e4e4e7; /* zinc-200 */
            }
            /* The nested container holding the buttons */
            QWidget#TabContainer {
                background-color: #f4f4f5; /* zinc-100 */
                border-radius: 6px;
            }
            /* The buttons themselves */
            QPushButton {
                background: transparent;
                color: #71717a; /* zinc-500 */
                font-size: 12px;
                font-weight: 500;
                border: none;
                border-radius: 4px;
                padding: 4px 16px;
                margin: 0;
            }
            QPushButton:hover {
                color: #18181b; /* zinc-900 */
                background-color: #e4e4e7; /* zinc-200 */
            }
            QPushButton:checked {
                background-color: #ffffff;
                color: #09090b; /* zinc-950 */
                border: 1px solid #d4d4d8; /* zinc-300 */
                font-weight: 600;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 6, 16, 6)
        layout.setSpacing(16)

        self._tabs = {}
        tabs_config = [
            ("INPUT", "Input"),
            ("MESH", "Mesh"),
            ("STAGING", "Staging"),
            ("RESULT", "Result")
        ]

        # Clean title text instead of just standard icon
        title_lbl = QPushButton("  TerraSim")
        
        from PySide6.QtWidgets import QStyle
        # Apply standard icon just for a bit of character
        title_lbl.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DirHomeIcon))
        title_lbl.setFlat(True)
        title_lbl.setStyleSheet("border: none; background: transparent; font-weight: bold; color: #18181b; font-size: 14px;")
        title_lbl.setEnabled(False)
        layout.addWidget(title_lbl)
        
        # segmented control sub-container
        self.tab_container = QWidget()
        self.tab_container.setObjectName("TabContainer")
        self.tab_container.setFixedHeight(32)
        tab_layout = QHBoxLayout(self.tab_container)
        tab_layout.setContentsMargins(2, 2, 2, 2)
        tab_layout.setSpacing(2)
        
        layout.addWidget(self.tab_container)

        for tab_id, label in tabs_config:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setFixedHeight(28)
            btn.setFixedWidth(100)
            btn.setCursor(Qt.PointingHandCursor)
            
            # Connect
            btn.clicked.connect(lambda checked, tid=tab_id: self._on_tab_clicked(tid))
            
            tab_layout.addWidget(btn)
            self._tabs[tab_id] = btn

        layout.addStretch()

        self._state = ProjectState.instance()
        self._state.active_tab_changed.connect(self._sync_active_tab)

        # Initial sync
        self._sync_active_tab(self._state.active_tab)

    def _on_tab_clicked(self, tab_id: str):
        self._state.set_active_tab(tab_id)

    def _sync_active_tab(self, tab_id: str):
        for tid, btn in self._tabs.items():
            # Block signals temporarily to avoid bounce-back
            btn.blockSignals(True)
            btn.setChecked(tid == tab_id)
            btn.blockSignals(False)

    def set_tab_enabled(self, tab_id: str, enabled: bool):
        """Enable or disable a specific tab button."""
        if tab_id in self._tabs:
            btn = self._tabs[tab_id]
            btn.setEnabled(enabled)
            
            # Visual feedback for disabled state
            if enabled:
                btn.setToolTip("")
                btn.setCursor(Qt.PointingHandCursor)
            else:
                btn.setToolTip("Run analysis first to view results.")
                btn.setCursor(Qt.ForbiddenCursor)
