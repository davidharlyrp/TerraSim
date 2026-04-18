# ui/result_explorer.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem,
    QLabel, QFrame
)
from PySide6.QtGui import QIcon, QPixmap, QColor, QPainter
from PySide6.QtCore import Qt
from core.state import ProjectState

def _color_icon(hex_color: str, size: int = 12) -> QIcon:
    pix = QPixmap(size, size)
    pix.fill(QColor(hex_color))
    p = QPainter(pix)
    p.setPen(QColor("#888888"))
    p.drawRect(0, 0, size - 1, size - 1)
    p.end()
    return QIcon(pix)

class ResultExplorer(QWidget):
    """
    Lightweight Explorer panel exclusively for the RESULT tab.
    Displays only Polygons, Loads, and Embedded Beams.
    Includes eye-toggle checkboxes to hide/show items in the Result Canvas.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self._state = ProjectState.instance()
        
        self._build_ui()
        
        # Connections
        self._state.polygons_changed.connect(self._rebuild_tree)
        self._state.point_loads_changed.connect(self._rebuild_tree)
        self._state.line_loads_changed.connect(self._rebuild_tree)
        self._state.embedded_beams_changed.connect(self._rebuild_tree)
        self._state.materials_changed.connect(self._rebuild_tree)
        self._state.beam_materials_changed.connect(self._rebuild_tree)
        self._state.current_phase_changed.connect(self._rebuild_tree)
        self._tree.itemChanged.connect(self._on_item_changed)
        
        self._is_handling_click = False
        self._rebuild_tree()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QLabel("Result Explorer")
        header.setStyleSheet("font-weight: semibold; padding: 4px 6px; color: #888;")
        layout.addWidget(header)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setFrameShadow(QFrame.Sunken)
        layout.addWidget(sep)

        self._tree = QTreeWidget()
        self._tree.setHeaderHidden(True)
        self._tree.setRootIsDecorated(True)
        self._tree.setIndentation(14)
        self._tree.setAnimated(True)
        layout.addWidget(self._tree)

    def _rebuild_tree(self, _=None):
        self._tree.blockSignals(True)
        self._tree.clear()

        polygons = self._state.polygons
        materials = self._state.materials
        beam_materials = self._state.beam_materials
        current_phase = self._state.current_phase
        mat_lookup = {m.get("id"): m for m in materials}
        bm_lookup = {bm.get("id"): bm for bm in beam_materials}

        # Polygons
        poly_root = QTreeWidgetItem(self._tree, [f"Polygons ({len(polygons)})"])
        poly_root.setExpanded(True)

        for i, poly in enumerate(polygons):
            mat_id = poly.get("materialId", "")
            if current_phase:
                mat_map = current_phase.get("current_material", {})
                if str(i) in mat_map:
                    mat_id = mat_map[str(i)]
            
            mat_info = mat_lookup.get(mat_id)
            if mat_info:
                label = f"Polygon #{i} [{mat_info.get('name')}]"
                icon = _color_icon(mat_info.get("color", "#888"))
            else:
                label = f"Polygon #{i} [unassigned]"
                icon = _color_icon("#555")

            item = QTreeWidgetItem(poly_root, [label])
            item.setIcon(0, icon)
            item.setData(0, Qt.UserRole, i)
            item.setData(0, Qt.UserRole + 1, "polygon")
            
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            is_visible = i not in self._state.result_hidden_polygons
            item.setCheckState(0, Qt.Checked if is_visible else Qt.Unchecked)

        # Loads
        point_loads = self._state.point_loads
        line_loads = self._state.line_loads
        load_root = QTreeWidgetItem(self._tree, [f"Loads ({len(point_loads) + len(line_loads)})"])
        load_root.setExpanded(True)

        for l in point_loads:
            lid = l.get("id", "")
            item = QTreeWidgetItem(load_root, [f"Point Load #{lid}"])
            item.setIcon(0, _color_icon("#ef4444"))
            item.setData(0, Qt.UserRole, lid)
            item.setData(0, Qt.UserRole + 1, "load")
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            is_visible = lid not in self._state.result_hidden_loads
            item.setCheckState(0, Qt.Checked if is_visible else Qt.Unchecked)

        for l in line_loads:
            lid = l.get("id", "")
            item = QTreeWidgetItem(load_root, [f"Line Load #{lid}"])
            item.setIcon(0, _color_icon("#f97316"))
            item.setData(0, Qt.UserRole, lid)
            item.setData(0, Qt.UserRole + 1, "load")
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            is_visible = lid not in self._state.result_hidden_loads
            item.setCheckState(0, Qt.Checked if is_visible else Qt.Unchecked)

        # Embedded Beams
        beams = self._state.embedded_beams
        beam_root = QTreeWidgetItem(self._tree, [f"Embedded Beams ({len(beams)})"])
        beam_root.setExpanded(True)

        for b in beams:
            bid = b.get("id", "")
            mid = b.get("materialId", "")
            m_info = bm_lookup.get(mid)
            label = f"Beam #{bid}"
            if m_info:
                label += f" [{m_info.get('name')}]"
                icon = _color_icon(m_info.get("color"))
            else:
                label += " [unassigned]"
                icon = _color_icon("#555")
            
            item = QTreeWidgetItem(beam_root, [label])
            item.setIcon(0, icon)
            item.setData(0, Qt.UserRole, bid)
            item.setData(0, Qt.UserRole + 1, "beam")
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            is_visible = bid not in self._state.result_hidden_beams
            item.setCheckState(0, Qt.Checked if is_visible else Qt.Unchecked)

        self._tree.blockSignals(False)

    def _on_item_changed(self, item, column):
        if self._is_handling_click:
            return
            
        self._is_handling_click = True
        try:
            item_type = item.data(0, Qt.UserRole + 1)
            val = item.data(0, Qt.UserRole)
            is_visible = (item.checkState(0) == Qt.Checked)
            
            if item_type == "polygon":
                self._state.toggle_result_polygon_visibility(val, is_visible)
            elif item_type == "load":
                self._state.toggle_result_load_visibility(val, is_visible)
            elif item_type == "beam":
                self._state.toggle_result_beam_visibility(val, is_visible)
                
        finally:
            self._is_handling_click = False
