import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QComboBox, QTableWidget, QTableWidgetItem, QHeaderView, QFrame,
    QListView
)
from PySide6.QtCore import Qt, Signal
from core.state import ProjectState

class PropertiesSidebar(QWidget):
    """
    Panel on the right showing properties of the selected element.
    Allows editing Name, Material, and Vertices.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(220)
        self.setObjectName("PropertiesSidebar")
        
        # Consistent styling with Explorer
        self.setStyleSheet("""
            QWidget#PropertiesSidebar {
                border-left: 1px solid #e4e4e7; /* zinc-200 */
            }
            QLabel#Header {
                font-weight: semibold; 
                padding: 4px 6px; 
                color: #888;
            }
            QLabel.SectionTitle {
                font-weight: 500;
                font-size: 11px;
                color: #71717a; /* zinc-500 */
                margin-top: 12px;
                margin-bottom: 2px;
            }
            QLineEdit, QComboBox {
                background-color: #ffffff;
                border: 1px solid #e4e4e7;
                border-radius: 4px;
                padding: 4px;
                font-size: 13px;
                color: #18181b;
                combobox-popup: 0;
            }
            QTableWidget {
                border: 1px solid #e4e4e7;
                background-color: transparent;
                gridline-color: #f4f4f5;
                font-size: 12px;
            }
            QHeaderView::section {
                background-color: #f4f4f5;
                padding: 4px;
                border: 1px solid #e4e4e7;
                font-weight: 500;
                font-size: 11px;
            }
        """)

        self._state = ProjectState.instance()
        self._current_index = -1
        self._is_updating = False

        self._init_ui()

        # Connect to state
        self._state.selection_changed.connect(self._on_selection_changed)
        self._state.materials_changed.connect(self._sync_materials)
        self._state.beam_materials_changed.connect(self._sync_beam_materials)
        self._state.polygons_changed.connect(self._sync_current_polygon)
        self._state.embedded_beams_changed.connect(self._sync_current_beam)
        
        # Initial Clear
        self._on_selection_changed(None)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        self.header_lbl = QLabel("Properties")
        self.header_lbl.setObjectName("Header")
        layout.addWidget(self.header_lbl)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setFrameShadow(QFrame.Sunken)
        layout.addWidget(sep)

        # Content container
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(12, 12, 12, 12)
        self.content_layout.setSpacing(10)
        layout.addWidget(self.content_widget)
        
        # Empty Label (Placeholder when nothing is selected)
        self.empty_lbl = QLabel("Select an element on the canvas to edit its properties.")
        self.empty_lbl.setAlignment(Qt.AlignCenter)
        self.empty_lbl.setWordWrap(True)
        self.empty_lbl.setStyleSheet("color: #a1a1aa; font-style: italic;")
        self.empty_lbl.setContentsMargins(20, 40, 20, 0)
        layout.addWidget(self.empty_lbl)
        
        # --- 1. POLYGON GROUP ---
        self.poly_group = QWidget()
        self.poly_vbox = QVBoxLayout(self.poly_group)
        self.poly_vbox.setContentsMargins(0, 0, 0, 0)
        
        lbl_mat = QLabel("Material")
        lbl_mat.setProperty("class", "SectionTitle")
        self.poly_vbox.addWidget(lbl_mat)
        
        self.material_cmb = QComboBox()
        self.material_cmb.setView(QListView())
        self.material_cmb.currentIndexChanged.connect(self._on_material_changed)
        self.poly_vbox.addWidget(self.material_cmb)
        
        lbl_v = QLabel("Vertices (X, Y)")
        lbl_v.setProperty("class", "SectionTitle")
        self.poly_vbox.addWidget(lbl_v)
        
        self.points_table = QTableWidget(0, 2)
        self.points_table.setHorizontalHeaderLabels(["X", "Y"])
        self.points_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.points_table.verticalHeader().setVisible(False)
        self.points_table.itemChanged.connect(self._on_poly_table_changed)
        self.poly_vbox.addWidget(self.points_table)
        
        self.content_layout.addWidget(self.poly_group)

        # --- 2. POINT LOAD GROUP ---
        self.point_load_group = QWidget()
        self.point_vbox = QVBoxLayout(self.point_load_group)
        self.point_vbox.setContentsMargins(0, 0, 0, 0)
        
        lbl_coords = QLabel("Position (X, Y)")
        lbl_coords.setProperty("class", "SectionTitle")
        self.point_vbox.addWidget(lbl_coords)
        
        self.point_xy_table = QTableWidget(1, 2)
        self.point_xy_table.setHorizontalHeaderLabels(["X", "Y"])
        self.point_xy_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.point_xy_table.verticalHeader().setVisible(False)
        self.point_xy_table.itemChanged.connect(self._on_point_data_changed)
        self.point_vbox.addWidget(self.point_xy_table)
        
        lbl_mag = QLabel("Magnitude (Fx, Fy)")
        lbl_mag.setProperty("class", "SectionTitle")
        self.point_vbox.addWidget(lbl_mag)
        
        self.point_f_table = QTableWidget(1, 2)
        self.point_f_table.setHorizontalHeaderLabels(["Fx", "Fy"])
        self.point_f_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.point_f_table.verticalHeader().setVisible(False)
        self.point_f_table.itemChanged.connect(self._on_point_data_changed)
        self.point_vbox.addWidget(self.point_f_table)
        
        self.content_layout.addWidget(self.point_load_group)

        # --- 3. LINE LOAD GROUP ---
        self.line_load_group = QWidget()
        self.line_vbox = QVBoxLayout(self.line_load_group)
        self.line_vbox.setContentsMargins(0, 0, 0, 0)
        
        lbl_line_coords = QLabel("Endpoints (P1, P2)")
        lbl_line_coords.setProperty("class", "SectionTitle")
        self.line_vbox.addWidget(lbl_line_coords)
        
        self.line_xy_table = QTableWidget(2, 2)
        self.line_xy_table.setHorizontalHeaderLabels(["X", "Y"])
        self.line_xy_table.setVerticalHeaderLabels(["P1", "P2"])
        self.line_xy_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.line_xy_table.itemChanged.connect(self._on_line_data_changed)
        self.line_vbox.addWidget(self.line_xy_table)
        
        lbl_line_mag = QLabel("Magnitude (Fx, Fy)")
        lbl_line_mag.setProperty("class", "SectionTitle")
        self.line_vbox.addWidget(lbl_line_mag)
        
        self.line_f_table = QTableWidget(1, 2)
        self.line_f_table.setHorizontalHeaderLabels(["Fx", "Fy"])
        self.line_f_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.line_f_table.verticalHeader().setVisible(False)
        self.line_f_table.itemChanged.connect(self._on_line_data_changed)
        self.line_vbox.addWidget(self.line_f_table)
        
        self.content_layout.addWidget(self.line_load_group)

        # --- 4. WATER LEVEL GROUP ---
        self.wl_group = QWidget()
        self.wl_vbox = QVBoxLayout(self.wl_group)
        self.wl_vbox.setContentsMargins(0, 0, 0, 0)
        
        lbl_wl_v = QLabel("Polyline Vertices (X, Y)")
        lbl_wl_v.setProperty("class", "SectionTitle")
        self.wl_vbox.addWidget(lbl_wl_v)
        
        self.wl_table = QTableWidget(0, 2)
        self.wl_table.setHorizontalHeaderLabels(["X", "Y"])
        self.wl_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.wl_table.verticalHeader().setVisible(False)
        self.wl_table.itemChanged.connect(self._on_wl_table_changed)
        self.wl_vbox.addWidget(self.wl_table)
        
        self.content_layout.addWidget(self.wl_group)
        
        # --- 5. BEAM GROUP ---
        self.beam_group = QWidget()
        self.beam_vbox = QVBoxLayout(self.beam_group)
        self.beam_vbox.setContentsMargins(0, 0, 0, 0)
        
        lbl_b_mat = QLabel("Structural Material")
        lbl_b_mat.setProperty("class", "SectionTitle")
        self.beam_vbox.addWidget(lbl_b_mat)
        
        self.beam_material_cmb = QComboBox()
        self.beam_material_cmb.setView(QListView())
        self.beam_material_cmb.currentIndexChanged.connect(self._on_beam_material_changed)
        self.beam_vbox.addWidget(self.beam_material_cmb)
        
        lbl_b_v = QLabel("Endpoints (P1, P2)")
        lbl_b_v.setProperty("class", "SectionTitle")
        self.beam_vbox.addWidget(lbl_b_v)
        
        self.beam_table = QTableWidget(2, 2)
        self.beam_table.setHorizontalHeaderLabels(["X", "Y"])
        self.beam_table.setVerticalHeaderLabels(["P1", "P2"])
        self.beam_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.beam_table.itemChanged.connect(self._on_beam_table_changed)
        self.beam_vbox.addWidget(self.beam_table)

        # Head Definition
        lbl_head = QLabel("Head Definition")
        lbl_head.setProperty("class", "SectionTitle")
        self.beam_vbox.addWidget(lbl_head)

        h_head_layout = QHBoxLayout()
        self.beam_head_point_cmb = QComboBox()
        self.beam_head_point_cmb.addItem("Point 1 (Start)", 0)
        self.beam_head_point_cmb.addItem("Point 2 (End)", 1)
        self.beam_head_point_cmb.currentIndexChanged.connect(self._on_beam_head_changed)
        h_head_layout.addWidget(self.beam_head_point_cmb)

        self.beam_head_conn_cmb = QComboBox()
        self.beam_head_conn_cmb.addItem("Pinned", "PIN")
        self.beam_head_conn_cmb.addItem("Fixed", "FIXED")
        self.beam_head_conn_cmb.currentIndexChanged.connect(self._on_beam_head_changed)
        h_head_layout.addWidget(self.beam_head_conn_cmb)

        self.beam_vbox.addLayout(h_head_layout)
        
        self.content_layout.addWidget(self.beam_group)

        layout.addStretch()

    def _sync_materials(self):
        """Populate material combo box."""
        if self._is_updating: return
        self._is_updating = True
        
        current_id = self.material_cmb.currentData()
        self.material_cmb.clear()
        self.material_cmb.addItem("No Material", "")
        
        for mat in self._state.materials:
            self.material_cmb.addItem(mat.get("name", "Unnamed"), mat.get("id"))
            
        # Try restore
        idx = self.material_cmb.findData(current_id)
        if idx >= 0: self.material_cmb.setCurrentIndex(idx)
        self._is_updating = False

    def _sync_beam_materials(self):
        """Populate structural material combo box."""
        if self._is_updating: return
        self._is_updating = True
        
        current_id = self.beam_material_cmb.currentData()
        self.beam_material_cmb.clear()
        self.beam_material_cmb.addItem("No Material", "")
        
        for mat in self._state.beam_materials:
            self.beam_material_cmb.addItem(mat.get("name", "Unnamed"), mat.get("id"))
            
        # Try restore
        idx = self.beam_material_cmb.findData(current_id)
        if idx >= 0: self.beam_material_cmb.setCurrentIndex(idx)
        self._is_updating = False

    def _on_selection_changed(self, selection: dict | None):
        self._current_selection = selection
        self.poly_group.hide()
        self.point_load_group.hide()
        self.line_load_group.hide()
        self.wl_group.hide()
        self.beam_group.hide()

        if not selection:
            self.header_lbl.setText("Properties")
            self.content_widget.hide()
            return

        self.content_widget.show()
        stype = selection.get("type")
        
        if stype == "polygon":
            self.poly_group.show()
            self._current_index = selection.get("index", -1)
            self._sync_current_polygon()
        elif stype == "point_load":
            self.point_load_group.show()
            self._sync_current_point_load(selection.get("id"))
        elif stype == "line_load":
            self.line_load_group.show()
            self._sync_current_line_load(selection.get("id"))
        elif stype == "water_level":
            self.wl_group.show()
            self._sync_current_water_level(selection.get("id"))
        elif stype == "embedded_beam":
            self.beam_group.show()
            self._sync_current_beam(selection.get("id"))

    def _sync_current_polygon(self):
        if self._is_updating: return
        idx = self._current_index
        if idx < 0 or idx >= len(self._state.polygons): return
        
        self._is_updating = True
        self.header_lbl.setText(f"Polygon #{idx}")
        poly = self._state.polygons[idx]
        
        self._sync_materials()
        
        # Check if we should show the base material or a phase override
        is_staging = (self._state.active_tab == "STAGING")
        current_phase = self._state.current_phase
        
        if is_staging and current_phase:
            # Show override for this phase
            overrides = current_phase.get("current_material", {})
            mat_id = overrides.get(str(idx), poly.get("materialId", ""))
            self.header_lbl.setText(f"Polygon #{idx} (Phase Override)")
        else:
            # Show base material
            mat_id = poly.get("materialId", "")
            self.header_lbl.setText(f"Polygon #{idx}")

        mat_combo_idx = self.material_cmb.findData(mat_id)
        if mat_combo_idx >= 0: self.material_cmb.setCurrentIndex(mat_combo_idx)
        
        verts = poly.get("vertices", [])
        self.points_table.setRowCount(len(verts))
        for i, v in enumerate(verts):
            self.points_table.setItem(i, 0, QTableWidgetItem(f"{v['x']:.3f}"))
            self.points_table.setItem(i, 1, QTableWidgetItem(f"{v['y']:.3f}"))
        self._is_updating = False

    def _on_material_changed(self):
        if self._is_updating or not self._current_selection: return
        if self._current_selection.get("type") == "polygon":
            mat_id = self.material_cmb.currentData()
            
            is_staging = (self._state.active_tab == "STAGING")
            if is_staging:
                # Update override for current phase
                self._state.update_phase_material(self._state.current_phase_index, self._current_index, mat_id)
            else:
                # Update base project material
                self._state.update_polygon(self._current_index, {"materialId": mat_id})

    def _on_poly_table_changed(self, item):
        if self._is_updating: return
        try:
            verts = []
            for r in range(self.points_table.rowCount()):
                x = float(self.points_table.item(r, 0).text())
                y = float(self.points_table.item(r, 1).text())
                verts.append({"x": x, "y": y})
            self._state.update_polygon(self._current_index, {"vertices": verts})
        except: self._sync_current_polygon()

    # --- Load & WL Syncs ---

    def _sync_current_point_load(self, lid):
        if self._is_updating: return
        target = next((l for l in self._state.point_loads if l.get("id") == lid), None)
        if not target: return
        self._is_updating = True
        self.header_lbl.setText(f"Point Load #{lid}")
        self.point_xy_table.setItem(0, 0, QTableWidgetItem(f"{target['x']:.3f}"))
        self.point_xy_table.setItem(0, 1, QTableWidgetItem(f"{target['y']:.3f}"))
        self.point_f_table.setItem(0, 0, QTableWidgetItem(f"{target['fx']:.2f}"))
        self.point_f_table.setItem(0, 1, QTableWidgetItem(f"{target['fy']:.2f}"))
        self._is_updating = False

    def _on_point_data_changed(self, item):
        if self._is_updating: return
        try:
            lid = self._current_selection.get("id")
            data = {
                "x": float(self.point_xy_table.item(0,0).text()),
                "y": float(self.point_xy_table.item(0,1).text()),
                "fx": float(self.point_f_table.item(0,0).text()),
                "fy": float(self.point_f_table.item(0,1).text())
            }
            # Add point load update method to ProjectState if not exists or use set_point_loads
            loads = self._state.point_loads
            for l in loads:
                if l["id"] == lid:
                    l.update(data)
                    break
            self._state.set_point_loads(loads)
        except: self._sync_current_point_load(self._current_selection.get("id"))

    def _sync_current_line_load(self, lid):
        if self._is_updating: return
        target = next((l for l in self._state.line_loads if l.get("id") == lid), None)
        if not target: return
        self._is_updating = True
        self.header_lbl.setText(f"Line Load #{lid}")
        self.line_xy_table.setItem(0, 0, QTableWidgetItem(f"{target['x1']:.3f}"))
        self.line_xy_table.setItem(0, 1, QTableWidgetItem(f"{target['y1']:.3f}"))
        self.line_xy_table.setItem(1, 0, QTableWidgetItem(f"{target['x2']:.3f}"))
        self.line_xy_table.setItem(1, 1, QTableWidgetItem(f"{target['y2']:.3f}"))
        self.line_f_table.setItem(0, 0, QTableWidgetItem(f"{target['fx']:.2f}"))
        self.line_f_table.setItem(0, 1, QTableWidgetItem(f"{target['fy']:.2f}"))
        self._is_updating = False

    def _on_line_data_changed(self, item):
        if self._is_updating: return
        try:
            lid = self._current_selection.get("id")
            data = {
                "x1": float(self.line_xy_table.item(0,0).text()),
                "y1": float(self.line_xy_table.item(0,1).text()),
                "x2": float(self.line_xy_table.item(1,0).text()),
                "y2": float(self.line_xy_table.item(1,1).text()),
                "fx": float(self.line_f_table.item(0,0).text()),
                "fy": float(self.line_f_table.item(0,1).text())
            }
            loads = self._state.line_loads
            for l in loads:
                if l["id"] == lid:
                    l.update(data)
                    break
            self._state.set_line_loads(loads)
        except: self._sync_current_line_load(self._current_selection.get("id"))

    def _sync_current_water_level(self, wlid):
        if self._is_updating: return
        target = next((wl for wl in self._state.water_levels if wl.get("id") == wlid), None)
        if not target: return
        self._is_updating = True
        self.header_lbl.setText(target.get("name", "Water Level"))
        verts = target.get("points", [])
        self.wl_table.setRowCount(len(verts))
        for i, v in enumerate(verts):
            self.wl_table.setItem(i, 0, QTableWidgetItem(f"{v['x']:.3f}"))
            self.wl_table.setItem(i, 1, QTableWidgetItem(f"{v['y']:.3f}"))
        self._is_updating = False

    def _on_wl_table_changed(self, item):
        if self._is_updating: return
        try:
            wlid = self._current_selection.get("id")
            pts = []
            for r in range(self.wl_table.rowCount()):
                pts.append({"x": float(self.wl_table.item(r, 0).text()), "y": float(self.wl_table.item(r, 1).text())})
            levels = self._state.water_levels
            for wl in levels:
                if wl["id"] == wlid:
                    wl["points"] = pts
                    break
            self._state.set_water_levels(levels)
        except: self._sync_current_water_level(self._current_selection.get("id"))

    def _sync_current_beam(self, bid=None):
        if self._is_updating: return
        if not bid and self._current_selection and self._current_selection.get("type") == "embedded_beam":
            bid = self._current_selection.get("id")
        if not bid: return
        
        target = next((b for b in self._state.embedded_beams if b.get("id") == bid), None)
        if not target: return

        self._is_updating = True
        self.header_lbl.setText(f"Embedded Beam Row")
        
        self._sync_beam_materials()
        
        mat_id = target.get("materialId", "")
        mat_combo_idx = self.beam_material_cmb.findData(mat_id)
        if mat_combo_idx >= 0: self.beam_material_cmb.setCurrentIndex(mat_combo_idx)
        
        self.beam_table.setItem(0, 0, QTableWidgetItem(f"{target['x1']:.3f}"))
        self.beam_table.setItem(0, 1, QTableWidgetItem(f"{target['y1']:.3f}"))
        self.beam_table.setItem(1, 0, QTableWidgetItem(f"{target['x2']:.3f}"))
        self.beam_table.setItem(1, 1, QTableWidgetItem(f"{target['y2']:.3f}"))

        # Sync Head Definition
        h_idx = target.get("head_point_index", 0)
        h_conn = target.get("head_connection_type", "FIXED")
        idx_p = self.beam_head_point_cmb.findData(h_idx)
        if idx_p >= 0: self.beam_head_point_cmb.setCurrentIndex(idx_p)
        idx_c = self.beam_head_conn_cmb.findData(h_conn)
        if idx_c >= 0: self.beam_head_conn_cmb.setCurrentIndex(idx_c)

        self._is_updating = False

    def _on_beam_material_changed(self):
        if self._is_updating or not self._current_selection: return
        if self._current_selection.get("type") == "embedded_beam":
            bid = self._current_selection.get("id")
            mat_id = self.beam_material_cmb.currentData()
            self._state.update_embedded_beam_material(bid, mat_id)

    def _on_beam_table_changed(self, item):
        if self._is_updating: return
        try:
            bid = self._current_selection.get("id")
            data = {
                "x1": float(self.beam_table.item(0, 0).text()),
                "y1": float(self.beam_table.item(0, 1).text()),
                "x2": float(self.beam_table.item(1, 0).text()),
                "y2": float(self.beam_table.item(1, 1).text()),
            }
            self._state.update_embedded_beam(bid, data)
        except: 
            if self._current_selection:
                self._sync_current_beam(self._current_selection.get("id"))

    def _on_beam_head_changed(self):
        if self._is_updating or not self._current_selection: return
        if self._current_selection.get("type") == "embedded_beam":
            bid = self._current_selection.get("id")
            data = {
                "head_point_index": self.beam_head_point_cmb.currentData(),
                "head_connection_type": self.beam_head_conn_cmb.currentData()
            }
            self._state.update_embedded_beam(bid, data)
