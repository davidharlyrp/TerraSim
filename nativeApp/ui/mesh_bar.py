# ui/mesh_bar.py
# ===========================================================================
# MeshBar — Settings bar for mesh generation (Quad9 + edge overrides)
# ===========================================================================

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QDoubleSpinBox, QFrame, QSizePolicy,
    QAbstractSpinBox, QPushButton, QSpinBox, QCheckBox,
)
from PySide6.QtCore import Qt, Signal
from core.state import ProjectState


class MeshBar(QWidget):
    """
    Compact horizontal bar for mesh parameters, edge override editing, and summary.
  Visible only in the MESH tab.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFixedHeight(68)

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
            QLabel#EdgeInfo {
                color: #2563eb;
                font-weight: 600;
            }
            QDoubleSpinBox, QSpinBox {
                background: #ffffff;
                border: 1px solid #cbd5e1;
                border-radius: 4px;
                padding: 2px 4px;
                font-size: 11px;
                min-width: 52px;
            }
            QDoubleSpinBox:focus, QSpinBox:focus {
                border-color: #3b82f6;
            }
            QDoubleSpinBox::up-button, QDoubleSpinBox::down-button,
            QSpinBox::up-button, QSpinBox::down-button {
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
            QCheckBox {
                font-size: 11px;
                color: #475569;
            }
        """)

        self._state = ProjectState.instance()
        self._is_updating = False
        self._build_ui()

        self._state.mesh_settings_changed.connect(self._on_state_settings_changed)
        self._state.mesh_response_changed.connect(self._on_mesh_response_changed)
        self._state.tool_mode_changed.connect(self._on_tool_mode_changed)
        self._state.mesh_edge_selection_changed.connect(self._on_edge_selection_changed)
        self._state.custom_overrides_changed.connect(self._on_custom_overrides_changed)

        self._on_state_settings_changed(self._state.mesh_settings)

    def _build_ui(self):
        outer = QHBoxLayout(self)
        outer.setContentsMargins(12, 4, 12, 4)
        outer.setSpacing(0)

        row1 = QHBoxLayout()
        row1.setSpacing(14)
        row2 = QHBoxLayout()
        row2.setSpacing(14)

        row1.addWidget(QLabel("Mesh Size (m)"))
        self.spn_size = QDoubleSpinBox()
        self.spn_size.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.spn_size.setRange(0.1, 50.0)
        self.spn_size.setSingleStep(0.1)
        self.spn_size.setDecimals(1)
        self.spn_size.valueChanged.connect(self._on_ui_changed)
        row1.addWidget(self.spn_size)

        row1.addWidget(QLabel("Boundary Refinement"))
        self.spn_refine = QDoubleSpinBox()
        self.spn_refine.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.spn_refine.setRange(0.1, 10.0)
        self.spn_refine.setSingleStep(0.1)
        self.spn_refine.setDecimals(1)
        self.spn_refine.valueChanged.connect(self._on_ui_changed)
        row1.addWidget(self.spn_refine)

        self.chk_load_refine = QCheckBox("Refine at loads")
        self.chk_load_refine.setChecked(True)
        self.chk_load_refine.toggled.connect(self._on_ui_changed)
        row1.addWidget(self.chk_load_refine)

        self.chk_ebr_refine = QCheckBox("Refine at EBR")
        self.chk_ebr_refine.setChecked(True)
        self.chk_ebr_refine.toggled.connect(self._on_ui_changed)
        row1.addWidget(self.chk_ebr_refine)

        line = QFrame()
        line.setFrameShape(QFrame.VLine)
        line.setStyleSheet(
            "background-color: #e2e8f0; border: none; min-width: 1px; max-width: 1px; margin: 4px 0;"
        )
        row1.addWidget(line)

        row1.addWidget(QLabel("Nodes:"))
        self.lbl_nodes = QLabel("0")
        self.lbl_nodes.setObjectName("SummaryValue")
        row1.addWidget(self.lbl_nodes)
        row1.addWidget(QLabel("Elements:"))
        self.lbl_elems = QLabel("0")
        self.lbl_elems.setObjectName("SummaryValue")
        row1.addWidget(self.lbl_elems)
        row1.addStretch()

        self.btn_edge = QPushButton("Pick Polygon Edge")
        self.btn_edge.setCheckable(True)
        self.btn_edge.clicked.connect(self._on_edge_pick_clicked)
        row1.addWidget(self.btn_edge)

        self.btn_track = QPushButton("Track Point")
        self.btn_track.setCheckable(True)
        self.btn_track.clicked.connect(self._on_track_clicked)
        row1.addWidget(self.btn_track)

        self.btn_save_track = QPushButton("Save Selection")
        self.btn_save_track.setObjectName("SaveButton")
        self.btn_save_track.clicked.connect(self._on_save_track_clicked)
        self.btn_save_track.setVisible(False)
        row1.addWidget(self.btn_save_track)

        row2.addWidget(QLabel("Edge override:"))
        self.lbl_edge_info = QLabel("(click a polygon edge)")
        self.lbl_edge_info.setObjectName("EdgeInfo")
        row2.addWidget(self.lbl_edge_info)

        row2.addWidget(QLabel("Elements"))
        self.spn_edge_elems = QSpinBox()
        self.spn_edge_elems.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.spn_edge_elems.setRange(2, 500)
        self.spn_edge_elems.setSingleStep(2)
        self.spn_edge_elems.setValue(10)
        self.spn_edge_elems.setEnabled(False)
        row2.addWidget(self.spn_edge_elems)

        row2.addWidget(QLabel("Bias"))
        self.spn_edge_bias = QDoubleSpinBox()
        self.spn_edge_bias.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.spn_edge_bias.setRange(0.1, 10.0)
        self.spn_edge_bias.setSingleStep(0.1)
        self.spn_edge_bias.setDecimals(2)
        self.spn_edge_bias.setValue(1.0)
        self.spn_edge_bias.setEnabled(False)
        row2.addWidget(self.spn_edge_bias)

        self.btn_apply_edge = QPushButton("Apply")
        self.btn_apply_edge.setEnabled(False)
        self.btn_apply_edge.clicked.connect(self._on_apply_edge_override)
        row2.addWidget(self.btn_apply_edge)

        self.btn_clear_edge = QPushButton("Clear")
        self.btn_clear_edge.setEnabled(False)
        self.btn_clear_edge.clicked.connect(self._on_clear_edge_override)
        row2.addWidget(self.btn_clear_edge)

        row2.addStretch()

        from PySide6.QtWidgets import QVBoxLayout
        col = QVBoxLayout()
        col.setSpacing(4)
        col.setContentsMargins(0, 0, 0, 0)
        col.addLayout(row1)
        col.addLayout(row2)
        outer.addLayout(col)

    def _on_ui_changed(self):
        if self._is_updating:
            return
        self._state.set_mesh_settings({
            "mesh_size": self.spn_size.value(),
            "boundary_refinement_factor": self.spn_refine.value(),
            "element_type": "quad9",
            "load_refinement_enabled": self.chk_load_refine.isChecked(),
            "ebr_refinement_enabled": self.chk_ebr_refine.isChecked(),
        })

    def _on_state_settings_changed(self, settings: dict):
        self._is_updating = True
        self.spn_size.setValue(settings.get("mesh_size", 2.0))
        self.spn_refine.setValue(settings.get("boundary_refinement_factor", 1.0))
        self.chk_load_refine.setChecked(settings.get("load_refinement_enabled", True))
        self.chk_ebr_refine.setChecked(settings.get("ebr_refinement_enabled", True))
        self._is_updating = False

    def _on_mesh_response_changed(self, response: dict | None):
        has_mesh = response is not None and response.get("success", False)
        self.btn_save_track.setEnabled(has_mesh and self._state.tool_mode == "PICK_POINT")
        if not response or not response.get("success"):
            self.lbl_nodes.setText("0")
            self.lbl_elems.setText("0")
            et = response.get("element_type", "quad9") if response else "quad9"
            self.lbl_elems.setToolTip("")
            return
        self.lbl_nodes.setText(str(len(response.get("nodes", []))))
        n_el = len(response.get("elements", []))
        et = response.get("element_type", "quad9")
        self.lbl_elems.setText(f"{n_el} ({et})")

    def _on_edge_pick_clicked(self):
        if self.btn_edge.isChecked():
            self._state.set_tool_mode("PICK_POLYGON_EDGE")
            self._state.log("Pick Polygon Edge: klik sisi polygon untuk atur custom_overrides.")
        else:
            self._state.set_selected_mesh_edge(None)
            if self._state.tool_mode == "PICK_POLYGON_EDGE":
                self._state.set_tool_mode("SELECT")

    def _on_track_clicked(self):
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
        is_edge = mode == "PICK_POLYGON_EDGE"
        self.btn_track.setChecked(is_picking)
        self.btn_edge.setChecked(is_edge)
        for btn in (self.btn_track, self.btn_edge):
            btn.setProperty("active", "true" if btn.isChecked() else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        has_mesh = self._state.mesh_response is not None
        self.btn_save_track.setVisible(is_picking)
        self.btn_save_track.setEnabled(is_picking and has_mesh)

    def _on_edge_selection_changed(self, edge: dict | None):
        has_edge = edge is not None
        self.spn_edge_elems.setEnabled(has_edge)
        self.spn_edge_bias.setEnabled(has_edge)
        self.btn_apply_edge.setEnabled(has_edge)
        self.btn_clear_edge.setEnabled(has_edge)
        if not has_edge:
            self.lbl_edge_info.setText("(klik sisi polygon)")
            return
        pi = edge["polygon_index"]
        vs = edge["vertex_start"]
        ve = edge["vertex_end"]
        self.lbl_edge_info.setText(f"Polygon {pi + 1}: V{vs + 1} → V{ve + 1}")
        ov = self._find_override(pi, vs, ve)
        if ov:
            self.spn_edge_elems.setValue(int(ov.get("num_elements", 10)))
            self.spn_edge_bias.setValue(float(ov.get("bias", 1.0)))
        else:
            self.spn_edge_elems.setValue(10)
            self.spn_edge_bias.setValue(1.0)

    def _on_custom_overrides_changed(self, _overrides: list):
        edge = self._state.selected_mesh_edge
        if edge:
            self._on_edge_selection_changed(edge)

    def _find_override(self, polygon_index: int, vs: int, ve: int) -> dict | None:
        for ov in self._state.custom_overrides:
            if ov.get("polygon_index") != polygon_index:
                continue
            if (ov.get("vertex_start"), ov.get("vertex_end")) in ((vs, ve), (ve, vs)):
                return ov
        return None

    def _on_apply_edge_override(self):
        edge = self._state.selected_mesh_edge
        if not edge:
            return
        n_elems = self.spn_edge_elems.value()
        if n_elems % 2 != 0:
            n_elems += 1
            self.spn_edge_elems.setValue(n_elems)
        self._state.upsert_mesh_edge_override(
            edge["polygon_index"],
            edge["vertex_start"],
            edge["vertex_end"],
            n_elems,
            self.spn_edge_bias.value(),
        )
        self._state.log(
            f"Edge override disimpan: Polygon {edge['polygon_index'] + 1}, "
            f"{n_elems} elemen, bias={self.spn_edge_bias.value():.2f}"
        )

    def _on_clear_edge_override(self):
        edge = self._state.selected_mesh_edge
        if not edge:
            return
        self._state.remove_mesh_edge_override(
            edge["polygon_index"], edge["vertex_start"], edge["vertex_end"]
        )
        self._state.log("Edge override dihapus.")

    def _on_save_track_clicked(self):
        points = self._state.tracked_points
        self._state.log(f"Tracked points saved: {len(points)} points total.")
        self._state.set_tool_mode("SELECT")
