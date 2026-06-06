# ui/preferences_dialog.py
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QDoubleSpinBox, QSpinBox, QCheckBox, QPushButton, QFrame, QWidget, QGroupBox,
    QComboBox
)
from PySide6.QtCore import Qt, QStandardPaths
from core.state import ProjectState

try:
    from pypardiso import spsolve
    HAS_PARDISO = True
except Exception as e:
    HAS_PARDISO = False
    # This will print to terminal if running the bundled EXE from cmd/powershell
    print(f"DEBUG: Pardiso import failed: {e}")
    import traceback
    traceback.print_exc()

class PreferencesDialog(QDialog):
    """
    Simulation Preferences dialog.
    Manages numerical parameters (tolerance, iterations) and performance toggles.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Simulation Preferences")
        self.setMinimumWidth(380)
        self._state = ProjectState.instance()

        self._build_ui()
        self._sync_from_state()

    def _build_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(12, 12, 12, 12)
        root_layout.setSpacing(10)

        # Style for secondary labels and compact layout
        self.setStyleSheet("""
            QGroupBox { font-weight: semibold; border: 1px solid #e5e7eb; border-radius: 0px; margin-top: 10px; padding-top: 10px; }
            QGroupBox::title { subcontrol-origin: margin; left: 8px; padding: 0 3px; color: #6b7280; }
            QLabel { color: #374151; font-size: 11px; }
            QSpinBox, QDoubleSpinBox { 
                padding: 4px 6px; 
                border: 1px solid #d1d5db; 
                border-radius: 0px; 
                background-color: #ffffff;
                color: #111827;
                height: 20px;
            }
            QSpinBox:focus, QDoubleSpinBox:focus { border: 1px solid #111827; }
        """)

        # --- Calculation Methods group ---
        meth_group = QGroupBox("Calculation Methods")
        meth_layout = QVBoxLayout(meth_group)
        meth_layout.setSpacing(8)

        self.chk_al = QCheckBox("Enable Arc-Length Calculation")
        self.chk_al.setToolTip("Uses Crisfield's arc-length method (recommended for slope failure/SRM).")
        meth_layout.addWidget(self.chk_al)

        self.chk_pardiso = QCheckBox("Push CPU Performance")
        self.chk_pardiso.setToolTip("Uses Intel MKL Pypardiso for parallel solver execution.")
        
        if not HAS_PARDISO:
            self.chk_pardiso.setEnabled(False)
            self.chk_pardiso.setText(self.chk_pardiso.text() + " [Not Installed]")
            self.chk_pardiso.setStyleSheet("color: #94a3b8;")
        
        meth_layout.addWidget(self.chk_pardiso)

        root_layout.addWidget(meth_group)

        # --- General Parameter group ---
        gp_group = QGroupBox("General Parameters")
        gp_layout = QVBoxLayout(gp_group)
        gp_layout.setSpacing(6)

        self.spn_kw = self._add_row(gp_layout, "Bulk Modulus of Water, Kw (kPa):", QDoubleSpinBox())
        self.spn_kw.setRange(0, 1e12)
        self.spn_kw.setToolTip("Bulk modulus of water (kN/m^2)")

        root_layout.addWidget(gp_group)

        # --- Boundary Conditions group ---
        bc_group = QGroupBox("Boundary Conditions")
        bc_layout = QVBoxLayout(bc_group)
        bc_layout.setSpacing(6)
        
        self.cmb_x_min = self._add_row_combo(bc_layout, "X-Min Boundary:")
        self.cmb_x_max = self._add_row_combo(bc_layout, "X-Max Boundary:")
        self.cmb_y_min = self._add_row_combo(bc_layout, "Y-Min Boundary:")
        self.cmb_y_max = self._add_row_combo(bc_layout, "Y-Max Boundary:")
        
        root_layout.addWidget(bc_group)

        # --- System Maintenance group ---
        sys_group = QGroupBox("System Maintenance")
        sys_layout = QVBoxLayout(sys_group)
        sys_layout.setSpacing(6)

        self.spn_max_logs = self._add_row(sys_layout, "Max Log Files to Keep:", QSpinBox())
        self.spn_max_logs.setRange(1, 100)
        self.spn_max_logs.setToolTip("Maximum number of console and journal log files to maintain in AppData.")

        # Path helper note
        log_path = QStandardPaths.writableLocation(QStandardPaths.AppLocalDataLocation) + "/logs"
        lbl_path = QLabel(f"Logs saved at: {log_path}")
        lbl_path.setStyleSheet("color: #94a3b8; font-style: italic; font-size: 10px; margin-top: -2px;")
        lbl_path.setWordWrap(True)
        sys_layout.addWidget(lbl_path)

        root_layout.addWidget(sys_group)
        root_layout.addStretch()

        # --- Footer ---
        footer_layout = QHBoxLayout()
        
        btn_reset = QPushButton("Reset to Default")
        btn_reset.setFlat(True)
        btn_reset.setStyleSheet("color: #64748b; font-size: 11px;")
        btn_reset.clicked.connect(self._on_reset_clicked)
        
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setFixedWidth(80)
        btn_cancel.setFixedHeight(30)
        btn_cancel.setCursor(Qt.PointingHandCursor)
        btn_cancel.clicked.connect(self.reject)
        
        btn_save = QPushButton("Apply")
        btn_save.setFixedWidth(100)
        btn_save.setFixedHeight(30)
        btn_save.setCursor(Qt.PointingHandCursor)
        btn_save.setStyleSheet("""
            QPushButton { 
                background-color: #111827; 
                color: #ffffff; 
                font-weight: semibold; 
                border-radius: 0px; 
            }
            QPushButton:hover { background-color: #374151; }
        """)
        btn_save.clicked.connect(self._on_save_clicked)

        footer_layout.addWidget(btn_reset)
        footer_layout.addStretch()
        footer_layout.addWidget(btn_cancel)
        footer_layout.addWidget(btn_save)

        root_layout.addLayout(footer_layout)

    def _add_row(self, layout, label_text, widget):
        row = QWidget()
        row_lyt = QHBoxLayout(row)
        row_lyt.setContentsMargins(0, 0, 0, 0)
        lbl = QLabel(label_text)
        widget.setFixedWidth(120)
        if isinstance(widget, (QDoubleSpinBox, QSpinBox)):
            widget.setAlignment(Qt.AlignRight)
            widget.setButtonSymbols(QDoubleSpinBox.NoButtons) # Hide arrows
        row_lyt.addWidget(lbl)
        row_lyt.addStretch()
        row_lyt.addWidget(widget)
        layout.addWidget(row)
        return widget

    def _add_row_combo(self, layout, label_text):
        cmb = QComboBox()
        cmb.addItem("Free", "free")
        cmb.addItem("Fixed (X & Y)", "fixed")
        cmb.addItem("Roller (Fix X)", "roller_x")
        cmb.addItem("Roller (Fix Y)", "roller_y")
        return self._add_row(layout, label_text, cmb)

    def _sync_from_state(self):
        s = self._state.settings
        self.chk_al.setChecked(s.get("use_arc_length", False))
        self.chk_pardiso.setChecked(s.get("use_pardiso", True) and HAS_PARDISO)
        self.spn_max_logs.setValue(s.get("max_log_files", 5))

        self.spn_kw.setValue(s.get("k_w", 2.2e6))
        
        # Sync BCs
        bc_x_min = s.get("bc_x_min", "roller_x")
        bc_x_max = s.get("bc_x_max", "roller_x")
        bc_y_min = s.get("bc_y_min", "fixed")
        bc_y_max = s.get("bc_y_max", "free")
        
        self.cmb_x_min.setCurrentIndex(self.cmb_x_min.findData(bc_x_min))
        self.cmb_x_max.setCurrentIndex(self.cmb_x_max.findData(bc_x_max))
        self.cmb_y_min.setCurrentIndex(self.cmb_y_min.findData(bc_y_min))
        self.cmb_y_max.setCurrentIndex(self.cmb_y_max.findData(bc_y_max))

    def _on_reset_clicked(self):
        self._state.reset_settings_to_default()
        self._sync_from_state()

    def _on_save_clicked(self):
        data = {
            "use_arc_length": self.chk_al.isChecked(),
            "use_pardiso": self.chk_pardiso.isChecked(),
            "max_log_files": self.spn_max_logs.value(),
            "k_w": self.spn_kw.value(),
            "bc_x_min": self.cmb_x_min.currentData() or "roller_x",
            "bc_x_max": self.cmb_x_max.currentData() or "roller_x",
            "bc_y_min": self.cmb_y_min.currentData() or "fixed",
            "bc_y_max": self.cmb_y_max.currentData() or "free"
        }
        self._state.update_settings(data)

        # Persist global preferences to QSettings
        from PySide6.QtCore import QSettings
        qs = QSettings("DaharEngineer", "TerraSim")
        qs.setValue("max_log_files", data["max_log_files"])
        qs.setValue("k_w", data["k_w"])

        self.accept()
