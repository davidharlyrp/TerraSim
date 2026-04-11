# ui/mesh_bar.py
# ===========================================================================
# MeshBar — Minimalist settings bar for mesh generation parameters
# ===========================================================================

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QDoubleSpinBox, QFrame, QSizePolicy,
    QAbstractSpinBox, QPushButton
)
from PySide6.QtCore import Qt, Signal
from core.state import ProjectState

class MeshBar(QWidget):
    """
    A compact horizontal bar for adjusting mesh settings.
    Visible only in the MESH tab.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFixedHeight(34)
        
        # Modern minimalist styling
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
            QLabel#SummaryValue {
                color: #0f172a;
                font-weight: 700;
            }
            QDoubleSpinBox {
                background: #ffffff;
                border: 1px solid #cbd5e1;
                border-radius: 4px;
                padding: 2px 4px;
                font-size: 11px;
                min-width: 60px;
            }
            QDoubleSpinBox:focus {
                border-color: #3b82f6;
            }
            QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
                width: 0px;
                border: none;
            }
            QPushButton {
                background-color: #ffffff;
                border: 1px solid #cbd5e1;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 11px;
                font-weight: 500;
                color: #334155;
            }
            QPushButton:hover {
                background-color: #f1f5f9;
                border-color: #94a3b8;
            }
            QPushButton:pressed {
                background-color: #e2e8f0;
            }
            QPushButton[active="true"] {
                background-color: #eff6ff;
                border-color: #3b82f6;
                color: #2563eb;
            }
            QPushButton#SaveButton {
                background-color: #3b82f6;
                border-color: #2563eb;
                color: #ffffff;
            }
            QPushButton#SaveButton:hover {
                background-color: #2563eb;
            }
        """)

        self._state = ProjectState.instance()
        self._is_updating = False
        
        self._build_ui()
        
        # Connect to state
        self._state.mesh_settings_changed.connect(self._on_state_settings_changed)
        self._state.mesh_response_changed.connect(self._on_mesh_response_changed)
        self._state.tool_mode_changed.connect(self._on_tool_mode_changed)
        
        # Initialize
        self._on_state_settings_changed(self._state.mesh_settings)

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(16)

        # --- 1. MESH SIZE ---
        layout.addWidget(QLabel("Mesh Size (m)"))
        self.spn_size = QDoubleSpinBox()
        self.spn_size.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.spn_size.setRange(0.1, 50.0)
        self.spn_size.setSingleStep(0.1)
        self.spn_size.setDecimals(1)
        self.spn_size.valueChanged.connect(self._on_ui_changed)
        layout.addWidget(self.spn_size)

        # --- 2. REFINEMENT ---
        layout.addWidget(QLabel("Boundary Refinement"))
        self.spn_refine = QDoubleSpinBox()
        self.spn_refine.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.spn_refine.setRange(0.1, 10.0)
        self.spn_refine.setSingleStep(0.1)
        self.spn_refine.setDecimals(1)
        self.spn_refine.valueChanged.connect(self._on_ui_changed)
        layout.addWidget(self.spn_refine)

        layout.addSpacing(20)
        
        # Vertical Separator
        line = QFrame()
        line.setFrameShape(QFrame.VLine)
        line.setStyleSheet("background-color: #e2e8f0; border: none; min-width: 1px; max-width: 1px; margin: 8px 0;")
        layout.addWidget(line)

        # --- 3. SUMMARY (Nodes/Elements) ---
        layout.addWidget(QLabel("Nodes:"))
        self.lbl_nodes = QLabel("0")
        self.lbl_nodes.setObjectName("SummaryValue")
        layout.addWidget(self.lbl_nodes)

        layout.addWidget(QLabel("Elements:"))
        self.lbl_elems = QLabel("0")
        self.lbl_elems.setObjectName("SummaryValue")
        layout.addWidget(self.lbl_elems)

        layout.addStretch()

        # --- 4. TRACK POINT BUTTONS ---
        self.btn_track = QPushButton("Track Point")
        self.btn_track.setCheckable(True)
        self.btn_track.clicked.connect(self._on_track_clicked)
        layout.addWidget(self.btn_track)

        self.btn_save_track = QPushButton("Save Selection")
        self.btn_save_track.setObjectName("SaveButton")
        self.btn_save_track.clicked.connect(self._on_save_track_clicked)
        self.btn_save_track.setVisible(False) # Only show during active picking
        layout.addWidget(self.btn_save_track)

    def _on_ui_changed(self):
        if self._is_updating: return
        self._state.set_mesh_settings({
            "mesh_size": self.spn_size.value(),
            "boundary_refinement_factor": self.spn_refine.value()
        })

    def _on_state_settings_changed(self, settings: dict):
        self._is_updating = True
        self.spn_size.setValue(settings.get("mesh_size", 2.0))
        self.spn_refine.setValue(settings.get("boundary_refinement_factor", 1.0))
        self._is_updating = False

    def _on_mesh_response_changed(self, response: dict | None):
        has_mesh = response is not None and response.get("success", False)
        # We keep btn_track enabled so clicking it can show the "generate mesh" hint
        self.btn_save_track.setEnabled(has_mesh and self._state.tool_mode == "PICK_POINT")
        
        if not response or not response.get("success"):
            self.lbl_nodes.setText("0")
            self.lbl_elems.setText("0")
            return
            
        self.lbl_nodes.setText(str(len(response.get("nodes", []))))
        self.lbl_elems.setText(str(len(response.get("elements", []))))

    def _on_track_clicked(self):
        # Restriction: Only allow tracking if mesh exists
        if not self._state.mesh_response:
            self.btn_track.setChecked(False)
            self._state.log("[WARN] Generate mesh first before pick a track point.")
            return

        if self.btn_track.isChecked():
            self._state.set_tool_mode("PICK_POINT")
            self._state.log("Pick Point mode active. Select nodes/GPs on the mesh.")
        else:
            self._state.set_tool_mode("SELECT")

    def _on_tool_mode_changed(self, mode: str):
        is_picking = mode == "PICK_POINT"
        self.btn_track.setChecked(is_picking)
        self.btn_track.setProperty("active", "true" if is_picking else "false")
        self.btn_track.style().unpolish(self.btn_track)
        self.btn_track.style().polish(self.btn_track)
        
        # Update Save button: only visible if picker is active AND mesh exists
        has_mesh = self._state.mesh_response is not None
        self.btn_save_track.setVisible(is_picking)
        self.btn_save_track.setEnabled(is_picking and has_mesh)

    def _on_save_track_clicked(self):
        # The points are actually managed in the canvas while in PICK_POINT mode.
        # This button triggers the final commit if needed, or just logs.
        # However, it's better if the canvas handles selection and this button
        # just finalizes it to ProjectState.tracked_points.
        
        # Access selection from temporary state in canvas? 
        # Actually, let's have the canvas emit a signal or just have a singleton property.
        # For now, we'll assume the points are already in a temporary buffer in ProjectState 
        # similar to drawing_points.
        
        points = self._state.tracked_points
        self._state.log(f"Tracked points saved: {len(points)} points total.")
        # Switch back to SELECT mode
        self._state.set_tool_mode("SELECT")
