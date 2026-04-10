from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QComboBox, QCheckBox, QPushButton, QFrame, QListView,
    QMessageBox
)
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
                text-transform: uppercase;
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

        # Disabling inputs if SAFETY_ANALYSIS
        if self._phase.get("phase_type") == "SAFETY_ANALYSIS":
            self.wl_cmb.setEnabled(False)
            self.reset_cb.setEnabled(False)
            # parent_cmb is left enabled because changing parent is a valid structural change, 
            # but it will re-sync in _on_save.

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

    def _on_save(self):
        # Update phase dictionary
        self._phase["name"] = self.name_edit.text()
        self._phase["phase_type"] = self.type_cmb.currentData()
        self._phase["active_water_level_id"] = self.wl_cmb.currentData()
        
        if self._phase_index > 0:
            self._phase["parent_id"] = self.parent_cmb.currentData()
            self._phase["reset_displacements"] = self.reset_cb.isChecked()
            
            # Safety Analysis state propagation logic
            if self._phase["phase_type"] == "SAFETY_ANALYSIS" and self._phase["parent_id"]:
                 parent = next((p for p in self._state.phases if p["id"] == self._phase["parent_id"]), None)
                 if parent:
                      self._phase["active_polygon_indices"] = list(parent.get("active_polygon_indices", []))
                      self._phase["active_load_ids"] = list(parent.get("active_load_ids", []))
                      self._phase["active_water_level_id"] = parent.get("active_water_level_id")
                      self._phase["active_beam_ids"] = list(parent.get("active_beam_ids", []))
                      self._phase["current_material"] = dict(parent.get("current_material", {}))

        self._state.update_phase(self._phase_index, self._phase)
        self.accept()
