from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QComboBox, QCheckBox, QPushButton, QFrame, QListView, QWidget,
    QMessageBox
)
from PySide6.QtGui import QDoubleValidator
from PySide6.QtCore import Qt
from core.state import ProjectState

class PhaseDialog(QDialog):
    """
    Dialog for editing an analysis phase's properties.
    """
    def __init__(self, phase_index: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Analysis Phase Settings")
        self.setMinimumWidth(320)
        self.setModal(True)
        
        self._state = ProjectState.instance()
        self._phase_index = phase_index
        
        # Defensive check
        if phase_index < 0 or phase_index >= len(self._state.phases):
            self.reject()
            return

        self._phase = dict(self._state.phases[phase_index])
        
        self.setStyleSheet("""
            QDialog {
                background-color: #ffffff;
            }
            .ItemLabel {
                font-weight: 500;
                font-size: 10px;
                color: #a1a1aa;
                margin-top: 8px;
                margin-bottom: 2px;
            }
            QLineEdit, QComboBox {
                background-color: #ffffff;
                border: 1px solid #e4e4e7;
                border-radius: 4px;
                padding: 6px;
                font-size: 12px;
                color: #18181b;
                combobox-popup: 0;
            }
            QPushButton#SaveBtn {
                background-color: #18181b;
                color: #ffffff;
                border-radius: 4px;
                padding: 6px 16px;
                font-weight: 600;
            }
            QPushButton#CancelBtn {
                background-color: #f4f4f5;
                color: #18181b;
                border-radius: 4px;
                padding: 6px 16px;
            }
        """)

        self._init_ui()
        self._load_data()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        # Name
        lbl_name = QLabel("Phase Name")
        lbl_name.setProperty("class", "ItemLabel")
        layout.addWidget(lbl_name)
        
        self.name_edit = QLineEdit()
        layout.addWidget(self.name_edit)

        # Analysis Type
        lbl_type = QLabel("Analysis Type")
        lbl_type.setProperty("class", "ItemLabel")
        layout.addWidget(lbl_type)
        
        self.type_cmb = QComboBox()
        self.type_cmb.setView(QListView())
        if self._phase_index == 0:
            self.type_cmb.addItem("K0 Procedure (Stress Init)", "K0_PROCEDURE")
            self.type_cmb.addItem("Gravity Loading (Total Stress)", "GRAVITY_LOADING")
        else:
            self.type_cmb.addItem("Plastic Analysis", "PLASTIC")
            self.type_cmb.addItem("Safety Analysis (SRM)", "SAFETY_ANALYSIS")
        layout.addWidget(self.type_cmb)

        # Water Level
        lbl_wl = QLabel("Active Water Level")
        lbl_wl.setProperty("class", "ItemLabel")
        layout.addWidget(lbl_wl)
        
        self.wl_cmb = QComboBox()
        self.wl_cmb.setView(QListView())
        self.wl_cmb.addItem("(None)", None)
        for wl in self._state.water_levels:
            self.wl_cmb.addItem(wl.get("name", f"Water Level #{wl['id']}"), wl["id"])
        layout.addWidget(self.wl_cmb)

        # Parent Selection
        if self._phase_index > 0:
            lbl_parent = QLabel("Start from (Parent)")
            lbl_parent.setProperty("class", "ItemLabel")
            layout.addWidget(lbl_parent)
            
            self.parent_cmb = QComboBox()
            self.parent_cmb.setView(QListView())
            for i, ph in enumerate(self._state.phases):
                if i != self._phase_index:
                    self.parent_cmb.addItem(ph.get("name", "Unnamed"), ph["id"])
            layout.addWidget(self.parent_cmb)

        # Reset Displacements
        self.reset_cb = QCheckBox("Reset Displacements")
        if self._phase_index > 0:
            layout.addWidget(self.reset_cb)
        else:
            self.reset_cb.setVisible(False)

        # Pseudo-static Analysis
        self.pseudo_group = QWidget()
        ps_layout = QVBoxLayout(self.pseudo_group)
        ps_layout.setContentsMargins(0, 5, 0, 5)
        ps_layout.setSpacing(8)
        
        ps_lbl = QLabel("Pseudo-static Coefficients")
        ps_lbl.setProperty("class", "ItemLabel")
        ps_layout.addWidget(ps_lbl)
        
        coeff_row = QHBoxLayout()
        # kh
        kh_layout = QVBoxLayout()
        kh_lbl = QLabel("kh (Horizontal)")
        kh_lbl.setStyleSheet("font-size: 10px; color: #71717a;")
        self.kh_edit = QLineEdit()
        self.kh_edit.setPlaceholderText("0.0")
        self.kh_edit.setValidator(QDoubleValidator(-1.0, 1.0, 4))
        kh_layout.addWidget(kh_lbl)
        kh_layout.addWidget(self.kh_edit)
        coeff_row.addLayout(kh_layout)
        
        # kv
        kv_layout = QVBoxLayout()
        kv_lbl = QLabel("kv (Vertical)")
        kv_lbl.setStyleSheet("font-size: 10px; color: #71717a;")
        self.kv_edit = QLineEdit()
        self.kv_edit.setPlaceholderText("0.0")
        self.kv_edit.setValidator(QDoubleValidator(-1.0, 1.0, 4))
        kv_layout.addWidget(kv_lbl)
        kv_layout.addWidget(self.kv_edit)
        coeff_row.addLayout(kv_layout)
        
        ps_layout.addLayout(coeff_row)
        layout.addWidget(self.pseudo_group)

        # Solver Group Settings
        self.solver_group = QWidget()
        solver_layout = QVBoxLayout(self.solver_group)
        solver_layout.setContentsMargins(0, 5, 0, 5)
        solver_layout.setSpacing(8)

        solver_lbl = QLabel("Solver Settings")
        solver_lbl.setProperty("class", "ItemLabel")
        solver_layout.addWidget(solver_lbl)

        solver_row = QHBoxLayout()

        # max_iterations
        max_iterations_layout = QVBoxLayout()
        max_iterations_lbl = QLabel("Max Iterations")
        max_iterations_lbl.setStyleSheet("font-size: 10px; color: #71717a;")
        self.max_iterations_edit = QLineEdit()
        self.max_iterations_edit.setPlaceholderText("60")
        self.max_iterations_edit.setValidator(QDoubleValidator(1, 1000, 0))
        max_iterations_layout.addWidget(max_iterations_lbl)
        max_iterations_layout.addWidget(self.max_iterations_edit)
        solver_row.addLayout(max_iterations_layout)

        # min_desired_iterations
        min_desired_iterations_layout = QVBoxLayout()
        min_desired_iterations_lbl = QLabel("Min Desired Iterations")
        min_desired_iterations_lbl.setStyleSheet("font-size: 10px; color: #71717a;")
        self.min_desired_iterations_edit = QLineEdit()
        self.min_desired_iterations_edit.setPlaceholderText("3")
        self.min_desired_iterations_edit.setValidator(QDoubleValidator(1, 1000, 0))
        min_desired_iterations_layout.addWidget(min_desired_iterations_lbl)
        min_desired_iterations_layout.addWidget(self.min_desired_iterations_edit)
        solver_row.addLayout(min_desired_iterations_layout)

        # max_desired_iterations
        max_desired_iterations_layout = QVBoxLayout()
        max_desired_iterations_lbl = QLabel("Max Desired Iterations")
        max_desired_iterations_lbl.setStyleSheet("font-size: 10px; color: #71717a;")
        self.max_desired_iterations_edit = QLineEdit()
        self.max_desired_iterations_edit.setPlaceholderText("15")
        self.max_desired_iterations_edit.setValidator(QDoubleValidator(1, 1000, 0))
        max_desired_iterations_layout.addWidget(max_desired_iterations_lbl)
        max_desired_iterations_layout.addWidget(self.max_desired_iterations_edit)
        solver_row.addLayout(max_desired_iterations_layout)

        # initial_step_size
        initial_step_size_layout = QVBoxLayout()
        initial_step_size_lbl = QLabel("Initial Step Size")
        initial_step_size_lbl.setStyleSheet("font-size: 10px; color: #71717a;")
        self.initial_step_size_edit = QLineEdit()
        self.initial_step_size_edit.setPlaceholderText("0.05")
        self.initial_step_size_edit.setValidator(QDoubleValidator(0.001, 1.0, 3))
        initial_step_size_layout.addWidget(initial_step_size_lbl)
        initial_step_size_layout.addWidget(self.initial_step_size_edit)
        solver_row.addLayout(initial_step_size_layout)

        # tolerance
        tolerance_layout = QVBoxLayout()
        tolerance_lbl = QLabel("Error Tolerance")
        tolerance_lbl.setStyleSheet("font-size: 10px; color: #71717a;")
        self.tolerance_edit = QLineEdit()
        self.tolerance_edit.setPlaceholderText("0.01")
        self.tolerance_edit.setValidator(QDoubleValidator(0.0001, 0.1, 4))
        tolerance_layout.addWidget(tolerance_lbl)
        tolerance_layout.addWidget(self.tolerance_edit)
        solver_row.addLayout(tolerance_layout)

        # max_step
        max_step_layout = QVBoxLayout()
        max_step_lbl = QLabel("Max Total Steps")
        max_step_lbl.setStyleSheet("font-size: 10px; color: #71717a;")
        self.max_step_edit = QLineEdit()
        self.max_step_edit.setPlaceholderText("100")
        self.max_step_edit.setValidator(QDoubleValidator(1, 1000, 0))
        max_step_layout.addWidget(max_step_lbl)
        max_step_layout.addWidget(self.max_step_edit)
        solver_row.addLayout(max_step_layout)

        # max_displacement_limit
        max_displacement_limit_layout = QVBoxLayout()
        max_displacement_limit_lbl = QLabel("Max Displacement Limit")
        max_displacement_limit_lbl.setStyleSheet("font-size: 10px; color: #71717a;")
        self.max_displacement_limit_edit = QLineEdit()
        self.max_displacement_limit_edit.setPlaceholderText("10.0")
        self.max_displacement_limit_edit.setValidator(QDoubleValidator(0.001, 100.0, 2))
        max_displacement_limit_layout.addWidget(max_displacement_limit_lbl)
        max_displacement_limit_layout.addWidget(self.max_displacement_limit_edit)
        solver_row.addLayout(max_displacement_limit_layout)

        solver_layout.addLayout(solver_row)
        layout.addWidget(self.solver_group)

        
        # Connect type change for visibility
        self.type_cmb.currentIndexChanged.connect(self._update_visibility)

        self._update_visibility()

        layout.addStretch()

        # Buttons
        btn_layout = QHBoxLayout()
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("CancelBtn")
        self.cancel_btn.clicked.connect(self.reject)
        
        self.save_btn = QPushButton("Save Changes")
        self.save_btn.setObjectName("SaveBtn")
        self.save_btn.clicked.connect(self._on_save)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.save_btn)
        layout.addLayout(btn_layout)

    def _load_data(self):
        ph = self._phase
        self.name_edit.setText(ph.get("name", ""))
        
        # Type
        ptype = ph.get("phase_type", "PLASTIC")
        t_idx = self.type_cmb.findData(ptype)
        if t_idx >= 0: self.type_cmb.setCurrentIndex(t_idx)
        
        # Water Level
        wl_idx = self.wl_cmb.findData(ph.get("active_water_level_id"))
        if wl_idx >= 0: self.wl_cmb.setCurrentIndex(wl_idx)
        
        # Parent
        if self._phase_index > 0:
            p_idx = self.parent_cmb.findData(ph.get("parent_id"))
            if p_idx >= 0: self.parent_cmb.setCurrentIndex(p_idx)
            self.reset_cb.setChecked(ph.get("reset_displacements", False))
            
        self.kh_edit.setText(str(ph.get("kh", "0.0")))
        self.kv_edit.setText(str(ph.get("kv", "0.0")))
        self.max_iterations_edit.setText(str(ph.get("max_iterations", "60")))
        self.min_desired_iterations_edit.setText(str(ph.get("min_desired_iterations", "3")))
        self.max_desired_iterations_edit.setText(str(ph.get("max_desired_iterations", "15")))
        self.initial_step_size_edit.setText(str(ph.get("initial_step_size", "0.05")))
        self.tolerance_edit.setText(str(ph.get("tolerance", "0.001")))
        self.max_step_edit.setText(str(ph.get("max_steps", "100")))
        self.max_displacement_limit_edit.setText(str(ph.get("max_displacement_limit", "10.0")))

    def _update_visibility(self):
        ptype = self.type_cmb.currentData()
        # pseudo-static is only relevant for plastic or gravity loading
        can_ps = ptype in ["PLASTIC", "GRAVITY_LOADING"]
        is_safety = ptype == "SAFETY_ANALYSIS"
        self.pseudo_group.setVisible(can_ps)
        self.wl_cmb.setEnabled(not is_safety)
        if self._phase_index > 0:
            self.reset_cb.setEnabled(not is_safety)
        self.kh_edit.setEnabled(not is_safety)
        self.kv_edit.setEnabled(not is_safety)

    def _parse_int(self, edit, default: int) -> int:
        text = edit.text().strip()
        return int(text) if text else default

    def _parse_float(self, edit, default: float) -> float:
        text = edit.text().strip()
        return float(text) if text else default

    def _on_save(self):
        ph = self._phase
        ptype = self.type_cmb.currentData()
        can_ps = ptype in ["PLASTIC", "GRAVITY_LOADING"]

        updates = {
            "name": self.name_edit.text(),
            "phase_type": ptype,
            "max_iterations": self._parse_int(self.max_iterations_edit, ph.get("max_iterations", 60)),
            "min_desired_iterations": self._parse_int(self.min_desired_iterations_edit, ph.get("min_desired_iterations", 3)),
            "max_desired_iterations": self._parse_int(self.max_desired_iterations_edit, ph.get("max_desired_iterations", 15)),
            "initial_step_size": self._parse_float(self.initial_step_size_edit, ph.get("initial_step_size", 0.05)),
            "tolerance": self._parse_float(self.tolerance_edit, ph.get("tolerance", 0.001)),
            "max_steps": self._parse_int(self.max_step_edit, ph.get("max_steps", 100)),
            "max_displacement_limit": self._parse_float(self.max_displacement_limit_edit, ph.get("max_displacement_limit", 10.0)),
        }

        if can_ps:
            try:
                updates["kh"] = float(self.kh_edit.text() or 0.0)
                updates["kv"] = float(self.kv_edit.text() or 0.0)
            except ValueError:
                updates["kh"] = 0.0
                updates["kv"] = 0.0
        elif ptype == "K0_PROCEDURE":
            updates["kh"] = 0.0
            updates["kv"] = 0.0
        # SAFETY_ANALYSIS: kh/kv and model structure synced from parent via propagate_phase_changes

        if ptype != "SAFETY_ANALYSIS":
            updates["active_water_level_id"] = self.wl_cmb.currentData()

        if self._phase_index > 0:
            updates["parent_id"] = self.parent_cmb.currentData()
            if ptype != "SAFETY_ANALYSIS":
                updates["reset_displacements"] = self.reset_cb.isChecked()

        self._state.update_phase(self._phase_index, updates)
        self.accept()
