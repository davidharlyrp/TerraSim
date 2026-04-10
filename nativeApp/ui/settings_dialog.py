import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QDoubleSpinBox, QCheckBox, QPushButton, QFrame, QWidget
)
from PySide6.QtCore import Qt
from core.state import ProjectState


class SettingsDialog(QDialog):
    """
    Global UI settings dialog for TerraSim.
    Allows adjusting grid spacing, snapping, and layout overlays.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("View Settings")
        self.setMinimumWidth(300)

        self._state = ProjectState.instance()

        self._build_ui()
        self._sync_from_state()

    def _build_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setSpacing(12)

        # Content container
        content = QWidget()
        form_layout = QVBoxLayout(content)
        form_layout.setContentsMargins(0, 0, 0, 0)
        form_layout.setSpacing(12)

        # -- Grid Spacing
        spacing_row = QWidget()
        spacing_layout = QHBoxLayout(spacing_row)
        spacing_layout.setContentsMargins(0, 0, 0, 0)
        
        lbl_spacing = QLabel("Grid Spacing (m):")
        self.spn_spacing = QDoubleSpinBox()
        self.spn_spacing.setRange(0.1, 100.0)
        self.spn_spacing.setSingleStep(0.5)
        self.spn_spacing.setDecimals(2)
        self.spn_spacing.setButtonSymbols(QDoubleSpinBox.NoButtons)
        
        spacing_layout.addWidget(lbl_spacing)
        spacing_layout.addStretch()
        spacing_layout.addWidget(self.spn_spacing)
        form_layout.addWidget(spacing_row)

        # -- Snapping
        self.chk_snap = QCheckBox("Snap to Grid")
        form_layout.addWidget(self.chk_snap)

        # -- Visibility Config
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background-color: #e4e4e7; border: none; min-height: 1px; max-height: 1px;")
        form_layout.addWidget(sep)

        self.chk_ruler = QCheckBox("Show Rulers")
        form_layout.addWidget(self.chk_ruler)

        self.chk_grid = QCheckBox("Show Background Grid")
        form_layout.addWidget(self.chk_grid)
        
        root_layout.addWidget(content)
        root_layout.addStretch()

        # Footer Actions
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        
        btn_save = QPushButton("Save Settings")
        btn_save.setStyleSheet("background-color: #27272a; color: white;")
        btn_save.clicked.connect(self._on_save_clicked)
        
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_save)

        root_layout.addWidget(btn_cancel.parentWidget() if False else QWidget()) # Placeholder fallback
        root_layout.addLayout(btn_layout)

    def _sync_from_state(self):
        settings = self._state.settings
        self.spn_spacing.setValue(settings.get("grid_spacing", 0.5))
        self.chk_snap.setChecked(settings.get("snap_to_grid", True))
        self.chk_ruler.setChecked(settings.get("show_ruler", True))
        self.chk_grid.setChecked(settings.get("show_grid", True))

    def _on_save_clicked(self):
        new_settings = {
            "grid_spacing": self.spn_spacing.value(),
            "snap_to_grid": self.chk_snap.isChecked(),
            "show_ruler": self.chk_ruler.isChecked(),
            "show_grid": self.chk_grid.isChecked(),
        }
        self._state.update_settings(new_settings)
        self.accept()
