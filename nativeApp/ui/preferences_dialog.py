# ui/preferences_dialog.py
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QDoubleSpinBox, QSpinBox, QCheckBox, QPushButton, QFrame, QWidget, QGroupBox
)
from PySide6.QtCore import Qt
from core.state import ProjectState

try:
    from pypardiso import spsolve
    HAS_PARDISO = True
except ImportError:
    HAS_PARDISO = False

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
            QGroupBox { font-weight: bold; border: 1px solid #e2e8f0; border-radius: 4px; margin-top: 10px; padding-top: 10px; }
            QGroupBox::title { subcontrol-origin: margin; left: 8px; padding: 0 3px; }
            QLabel { color: #475569; }
            QSpinBox, QDoubleSpinBox { padding: 2px; border: 1px solid #cbd5e1; border-radius: 3px; }
        """)

        # --- Numerical Control group ---
        num_group = QGroupBox("Numerical Control")
        num_layout = QVBoxLayout(num_group)
        num_layout.setSpacing(6)

        # Tolerance
        self.spn_tol = self._add_row(num_layout, "Convergence Tolerance:", QDoubleSpinBox())
        self.spn_tol.setRange(0.0001, 1.0)
        self.spn_tol.setDecimals(4)
        self.spn_tol.setSingleStep(0.001)

        # Max Iterations
        self.spn_iter = self._add_row(num_layout, "Max Iterations:", QSpinBox())
        self.spn_iter.setRange(1, 500)

        # Initial Step Size
        self.spn_step = self._add_row(num_layout, "Initial Step Size (fraction):", QDoubleSpinBox())
        self.spn_step.setRange(0.001, 1.0)
        self.spn_step.setDecimals(3)
        self.spn_step.setSingleStep(0.01)

        # Max Steps
        self.spn_max_steps = self._add_row(num_layout, "Max Total Steps:", QSpinBox())
        self.spn_max_steps.setRange(1, 1000)

        # Disp Limit
        self.spn_disp_limit = self._add_row(num_layout, "Max Displacement Limit (m):", QDoubleSpinBox())
        self.spn_disp_limit.setRange(0.1, 1000.0)
        self.spn_disp_limit.setDecimals(1)

        root_layout.addWidget(num_group)

        # --- Calculation Methods group ---
        meth_group = QGroupBox("Calculation Methods")
        meth_layout = QVBoxLayout(meth_group)
        meth_layout.setSpacing(8)

        self.chk_al = QCheckBox("Enable Arc-Length Calculation")
        self.chk_al.setToolTip("Uses Crisfield's arc-length method (recommended for slope failure/SRM).")
        meth_layout.addWidget(self.chk_al)

        self.chk_pardiso = QCheckBox("Push CPU Performance (Pardiso)")
        self.chk_pardiso.setToolTip("Uses Intel MKL Pypardiso for parallel solver execution.")
        
        if not HAS_PARDISO:
            self.chk_pardiso.setEnabled(False)
            self.chk_pardiso.setText(self.chk_pardiso.text() + " [Not Installed]")
            self.chk_pardiso.setStyleSheet("color: #94a3b8;")
        
        meth_layout.addWidget(self.chk_pardiso)

        root_layout.addWidget(meth_group)
        root_layout.addStretch()

        # --- Footer ---
        footer_layout = QHBoxLayout()
        
        btn_reset = QPushButton("Reset to Default")
        btn_reset.setFlat(True)
        btn_reset.setStyleSheet("color: #64748b; font-size: 11px;")
        btn_reset.clicked.connect(self._on_reset_clicked)
        
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setFixedWidth(80)
        btn_cancel.clicked.connect(self.reject)
        
        btn_save = QPushButton("Apply")
        btn_save.setFixedWidth(100)
        btn_save.setStyleSheet("background-color: #0f172a; color: white; font-weight: bold;")
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
        widget.setAlignment(Qt.AlignRight)
        widget.setButtonSymbols(QDoubleSpinBox.NoButtons) # Hide arrows
        row_lyt.addWidget(lbl)
        row_lyt.addStretch()
        row_lyt.addWidget(widget)
        layout.addWidget(row)
        return widget

    def _sync_from_state(self):
        s = self._state.settings
        self.spn_tol.setValue(s.get("tolerance", 0.01))
        self.spn_iter.setValue(s.get("max_iterations", 60))
        self.spn_step.setValue(s.get("initial_step_size", 0.05))
        self.spn_max_steps.setValue(s.get("max_steps", 100))
        self.spn_disp_limit.setValue(s.get("max_displacement_limit", 10.0))
        self.chk_al.setChecked(s.get("use_arc_length", False))
        self.chk_pardiso.setChecked(s.get("use_pardiso", True) and HAS_PARDISO)

    def _on_reset_clicked(self):
        self._state.reset_settings_to_default()
        self._sync_from_state()

    def _on_save_clicked(self):
        data = {
            "tolerance": self.spn_tol.value(),
            "max_iterations": self.spn_iter.value(),
            "initial_step_size": self.spn_step.value(),
            "max_steps": self.spn_max_steps.value(),
            "max_displacement_limit": self.spn_disp_limit.value(),
            "use_arc_length": self.chk_al.isChecked(),
            "use_pardiso": self.chk_pardiso.isChecked()
        }
        self._state.update_settings(data)
        self.accept()
