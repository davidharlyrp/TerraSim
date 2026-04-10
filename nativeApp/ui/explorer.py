# ui/explorer.py
# ===========================================================================
# BrowserExplorer — Left sidebar showing project data tree
# ===========================================================================
# Shows expandable lists of Polygons and Materials. Materials can be
# dragged from the list and dropped onto polygons in the canvas to
# assign them. Polygons show a colored badge indicating their
# assigned material.
# ===========================================================================

from __future__ import annotations
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem,
    QLabel, QFrame, QAbstractItemView, QHBoxLayout, QSizePolicy,
    QPushButton, QMenu
)
from PySide6.QtCore import Qt, QMimeData, Signal
from PySide6.QtGui import QDrag, QColor, QIcon, QPixmap, QPainter, QBrush

from core.state import ProjectState


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _color_icon(hex_color: str, size: int = 12) -> QIcon:
    """Create a small square icon filled with the given color."""
    pix = QPixmap(size, size)
    pix.fill(QColor(hex_color))
    # Draw a 1px border
    p = QPainter(pix)
    p.setPen(QColor("#888888"))
    p.drawRect(0, 0, size - 1, size - 1)
    p.end()
    return QIcon(pix)


# Custom MIME type for drag-and-drop material assignment
MIME_MATERIAL_ID = "application/x-terrasim-material-id"


class DraggableTreeWidget(QTreeWidget):
    """
    QTreeWidget subclass that supports dragging material items.
    Only items parented under the 'Materials' branch can be dragged.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setDragDropMode(QAbstractItemView.DragOnly)
        self.setDefaultDropAction(Qt.CopyAction)
        self.setSelectionMode(QAbstractItemView.SingleSelection)

    def startDrag(self, supportedActions):
        """
        Override to create custom MIME data when a material item is dragged.
        """
        item = self.currentItem()
        if not item:
            return

        # Only allow dragging material items (they have material_id data)
        material_id = item.data(0, Qt.UserRole)
        item_type = item.data(0, Qt.UserRole + 1)

        if item_type not in ["material", "beam_material"] or not material_id:
            return

        # Create drag with material ID as MIME data
        drag = QDrag(self)
        mime = QMimeData()
        mime.setData(MIME_MATERIAL_ID, material_id.encode("utf-8"))
        mime.setText(f"Material: {item.text(0)}")
        drag.setMimeData(mime)

        # Create a visual drag pixmap (small colored swatch + name)
        color = item.data(0, Qt.UserRole + 2) or "#888"
        pix = QPixmap(140, 22)
        pix.fill(Qt.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.Antialiasing)
        p.setBrush(QBrush(QColor(color)))
        p.setPen(QColor("#666"))
        p.drawRoundedRect(0, 0, 139, 21, 3, 3)
        p.setPen(QColor("#FFFFFF"))
        p.drawText(16, 15, item.text(0))
        p.end()
        drag.setPixmap(pix)

        drag.exec(Qt.CopyAction)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Delete:
            from core.state import ProjectState
            state = ProjectState.instance()
            
            # Don't allow deletion outside of INPUT mode
            if state.active_tab in ["STAGING", "RESULT", "MESH"]:
                 return
                 
            item = self.currentItem()
            if item:
                item_type = item.data(0, Qt.UserRole + 1)
                if item_type == "material":
                    mat_id = item.data(0, Qt.UserRole)
                    state.remove_material(mat_id)
                elif item_type == "beam_material":
                    mat_id = item.data(0, Qt.UserRole)
                    state.remove_beam_material(mat_id)
                elif item_type == "polygon":
                    poly_idx = item.data(0, Qt.UserRole)
                    state.remove_polygon(poly_idx)
                elif item_type == "embedded_beam":
                    beam_id = item.data(0, Qt.UserRole)
                    state.remove_embedded_beam(beam_id)
                
                state.set_selected_entity(None)
                event.accept()
                return
        super().keyPressEvent(event)


class BrowserExplorer(QWidget):
    """
    Left sidebar panel showing a tree view of project data.

    Structure:
        ▸ Polygons
            Polygon 1  [■ Clay]
            Polygon 2  [unassigned]
        ▸ Materials
            ■ Clay    (drag to assign)
            ■ Sand

    Signals
    -------
    edit_material_requested : str
        Emitted with material ID when user double-clicks a material item.
    delete_material_requested : str
        Emitted with material ID for deletion.
    delete_polygon_requested : int
        Emitted with polygon index for deletion.
    """

    edit_material_requested = Signal(str)
    delete_material_requested = Signal(str)
    delete_polygon_requested = Signal(int)
    edit_beam_material_requested = Signal(str)
    delete_beam_material_requested = Signal(str)
    delete_beam_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        self._state = ProjectState.instance()

        self._build_ui()

        # Connect state signals to refresh the tree
        self._state.polygons_changed.connect(self._rebuild_tree)
        self._state.materials_changed.connect(self._rebuild_tree)
        self._state.point_loads_changed.connect(self._rebuild_tree)
        self._state.line_loads_changed.connect(self._rebuild_tree)
        self._state.water_levels_changed.connect(self._rebuild_tree)
        self._state.embedded_beams_changed.connect(self._rebuild_tree)
        self._state.beam_materials_changed.connect(self._rebuild_tree)
        self._state.selection_changed.connect(self._on_global_selection_changed)
        self._state.active_tab_changed.connect(self._request_tree_rebuild)
        self._state.current_phase_changed.connect(self._request_tree_rebuild)
        self._state.phases_changed.connect(self._request_tree_rebuild)
        self._tree.itemChanged.connect(self._on_item_changed)

        # Debounce timer for tree rebuilds to prevent signal storms
        from PySide6.QtCore import QTimer
        self._rebuild_timer = QTimer(self)
        self._rebuild_timer.setSingleShot(True)
        self._rebuild_timer.setInterval(20) # 20ms debounce
        self._rebuild_timer.timeout.connect(self._rebuild_tree)

        self._is_handling_click = False

        # Initial build
        self._rebuild_tree()

    def _request_tree_rebuild(self):
        """Request a deferred tree rebuild to debounce rapid signals."""
        self._rebuild_timer.start()

    # ==================================================================
    # UI Build
    # ==================================================================

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QLabel("Explorer")
        header.setStyleSheet(
            "font-weight: semibold; padding: 4px 6px; color: #888;"
        )
        layout.addWidget(header)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setFrameShadow(QFrame.Sunken)
        layout.addWidget(sep)

        # Tree widget
        self._tree = DraggableTreeWidget()
        self._tree.setHeaderHidden(True)
        self._tree.setRootIsDecorated(True)
        self._tree.setIndentation(14)
        self._tree.setAnimated(True)
        self._tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self._tree.customContextMenuRequested.connect(self._on_context_menu)
        self._tree.itemDoubleClicked.connect(self._on_item_double_clicked)
        self._tree.itemSelectionChanged.connect(self._on_tree_selection_changed)

        layout.addWidget(self._tree)

    def _on_tree_selection_changed(self):
        """User clicked an item in the tree, push selection to global state."""
        selected = self._tree.selectedItems()
        if not selected:
            self._state.set_selected_entity(None)
            return

        item = selected[0]
        item_type = item.data(0, Qt.UserRole + 1)
        if item_type == "polygon":
            idx = item.data(0, Qt.UserRole)
            self._state.set_selected_entity({"type": "polygon", "index": idx})
        elif item_type == "material":
            mat_id = item.data(0, Qt.UserRole)
            self._state.set_selected_entity({"type": "material", "id": mat_id})
        elif item_type == "point_load":
            load_id = item.data(0, Qt.UserRole)
            self._state.set_selected_entity({"type": "point_load", "id": load_id})
        elif item_type == "line_load":
            load_id = item.data(0, Qt.UserRole)
            self._state.set_selected_entity({"type": "line_load", "id": load_id})
        elif item_type == "water_level":
            wl_id = item.data(0, Qt.UserRole)
            self._state.set_selected_entity({"type": "water_level", "id": wl_id})
        elif item_type == "embedded_beam":
            beam_id = item.data(0, Qt.UserRole)
            self._state.set_selected_entity({"type": "embedded_beam", "id": beam_id})
        elif item_type == "beam_material":
            mat_id = item.data(0, Qt.UserRole)
            self._state.set_selected_entity({"type": "beam_material", "id": mat_id})

    def _on_global_selection_changed(self, selection: dict | None):
        """Global state selection changed (e.g. from Canvas), update UI."""
        self._tree.blockSignals(True)
        self._tree.clearSelection()

        if selection:
            # We must iterate over tree items to find the matching node
            root = self._tree.invisibleRootItem()
            
            def recurse_select(parent_item):
                for i in range(parent_item.childCount()):
                    child = parent_item.child(i)
                    item_type = child.data(0, Qt.UserRole + 1)
                    if item_type == selection.get("type"):
                        if item_type == "polygon" and child.data(0, Qt.UserRole) == selection.get("index"):
                            child.setSelected(True)
                            self._tree.scrollToItem(child)
                            return True
                        elif item_type == "material" and child.data(0, Qt.UserRole) == selection.get("id"):
                            child.setSelected(True)
                            self._tree.scrollToItem(child)
                            return True
                        elif item_type in ["point_load", "line_load", "water_level", "embedded_beam"] and child.data(0, Qt.UserRole) == selection.get("id"):
                            child.setSelected(True)
                            self._tree.scrollToItem(child)
                            return True
                        elif item_type == "beam_material" and child.data(0, Qt.UserRole) == selection.get("id"):
                            child.setSelected(True)
                            self._tree.scrollToItem(child)
                            return True
                    if recurse_select(child):
                        return True
                return False

            recurse_select(root)

        self._tree.blockSignals(False)

    # ==================================================================
    # Tree Build / Refresh
    # ==================================================================

    def _rebuild_tree(self, _data=None):
        """Rebuild the entire tree from ProjectState data."""
        self._tree.blockSignals(True)
        self._tree.clear()

        polygons = self._state.polygons
        materials = self._state.materials
        active_tab = self._state.active_tab
        current_phase = self._state.current_phase
        is_staging = (active_tab == "STAGING") and (current_phase is not None)

        # Build a material lookup for badge display
        mat_lookup = {m.get("id"): m for m in materials}

        # ---- Materials Branch ----
        mat_count = len(materials)
        mat_root = QTreeWidgetItem(self._tree, [f"Materials ({mat_count})"])
        mat_root.setFlags(mat_root.flags() & ~Qt.ItemIsDragEnabled)
        mat_root.setExpanded(True)

        for mat in materials:
            mat_id = mat.get("id", "")
            mat_name = mat.get("name", "Unnamed")
            mat_color = mat.get("color", "#888")

            item = QTreeWidgetItem(mat_root, [mat_name])
            item.setIcon(0, _color_icon(mat_color))
            item.setToolTip(0, f"Drag onto a polygon to assign · ID: {mat_id}")

            # Store data for drag-and-drop
            item.setData(0, Qt.UserRole, mat_id)
            item.setData(0, Qt.UserRole + 1, "material")
            item.setData(0, Qt.UserRole + 2, mat_color)

            # Make draggable
            item.setFlags(item.flags() | Qt.ItemIsDragEnabled)

        # ---- Beam Materials Branch ----
        beam_materials = self._state.beam_materials
        bm_root = QTreeWidgetItem(self._tree, [f"Beam Materials ({len(beam_materials)})"])
        bm_root.setExpanded(True)
        for mat in beam_materials:
            mat_id = mat.get("id", "")
            mat_name = mat.get("name", "Unnamed")
            mat_color = mat.get("color", "#2563EB")
            item = QTreeWidgetItem(bm_root, [mat_name])
            item.setIcon(0, _color_icon(mat_color))
            item.setData(0, Qt.UserRole, mat_id)
            item.setData(0, Qt.UserRole + 1, "beam_material")
            item.setData(0, Qt.UserRole + 2, mat_color)
            item.setFlags(item.flags() | Qt.ItemIsDragEnabled)

        # ---- Polygons Branch ----
        poly_count = len(polygons)
        poly_root = QTreeWidgetItem(self._tree, [f"Polygons ({poly_count})"])
        poly_root.setFlags(poly_root.flags() & ~Qt.ItemIsDragEnabled)
        poly_root.setExpanded(True)

        for i, poly in enumerate(polygons):
            n_verts = len(poly.get("vertices", []))
            mat_id = poly.get("materialId", "")
            
            # STAGING: Apply Material Override for label
            if is_staging:
                mat_map = current_phase.get("current_material", {})
                if str(i) in mat_map:
                    mat_id = mat_map[str(i)]
            
            mat_info = mat_lookup.get(mat_id)

            # Build display text
            if mat_info:
                mat_name = mat_info.get("name", "?")
                mat_color = mat_info.get("color", "#888")
                label = f"Polygon #{i}  [{mat_name}]"
                icon = _color_icon(mat_color)
            else:
                label = f"Polygon #{i}  [unassigned]"
                icon = _color_icon("#555555")

            item = QTreeWidgetItem(poly_root, [label])
            item.setIcon(0, icon)
            item.setToolTip(0, f"{n_verts} vertices · Material: {mat_id or 'none'}")

            # Store data
            item.setData(0, Qt.UserRole, i)  # polygon index
            item.setData(0, Qt.UserRole + 1, "polygon")

            # Staging activation
            if is_staging:
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                active_polys = current_phase.get("active_polygon_indices", [])
                item.setCheckState(0, Qt.Checked if i in active_polys else Qt.Unchecked)
            else:
                item.setFlags(item.flags() & ~Qt.ItemIsUserCheckable)

            # Polygons are not draggable
            item.setFlags(item.flags() & ~Qt.ItemIsDragEnabled)

        # ---- Embedded Beams Branch ----
        beams = self._state.embedded_beams
        beam_root = QTreeWidgetItem(self._tree, [f"Embedded Beams ({len(beams)})"])
        beam_root.setExpanded(True)
        bm_lookup = {m.get("id"): m for m in beam_materials}
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
            item.setData(0, Qt.UserRole + 1, "embedded_beam")
            if is_staging:
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                active_beams = current_phase.get("active_beam_ids", [])
                item.setCheckState(0, Qt.Checked if bid in active_beams else Qt.Unchecked)

        # ---- Loads Branch ----
        point_loads = self._state.point_loads
        line_loads = self._state.line_loads
        load_root = QTreeWidgetItem(self._tree, [f"Loads ({len(point_loads) + len(line_loads)})"])
        load_root.setExpanded(True)

        for l in point_loads:
            lid = l.get("id", "")
            item = QTreeWidgetItem(load_root, [f"Point Load #{lid}"])
            item.setIcon(0, _color_icon("#ef4444")) # red-500
            item.setData(0, Qt.UserRole, lid)
            item.setData(0, Qt.UserRole + 1, "point_load")
            if is_staging:
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                active_loads = current_phase.get("active_load_ids", [])
                item.setCheckState(0, Qt.Checked if lid in active_loads else Qt.Unchecked)

        for l in line_loads:
            lid = l.get("id", "")
            item = QTreeWidgetItem(load_root, [f"Line Load #{lid}"])
            item.setIcon(0, _color_icon("#f97316")) # orange-500
            item.setData(0, Qt.UserRole, lid)
            item.setData(0, Qt.UserRole + 1, "line_load")
            if is_staging:
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                active_loads = current_phase.get("active_load_ids", [])
                item.setCheckState(0, Qt.Checked if lid in active_loads else Qt.Unchecked)

        # ---- Water Levels Branch ----
        water_levels = self._state.water_levels
        wl_root = QTreeWidgetItem(self._tree, [f"Water Levels ({len(water_levels)})"])
        wl_root.setExpanded(True)

        for wl in water_levels:
            wlid = wl.get("id", "")
            name = wl.get("name", f"Water Level #{wlid}")
            item = QTreeWidgetItem(wl_root, [name])
            item.setIcon(0, _color_icon("#3b82f6")) # blue-500
            item.setData(0, Qt.UserRole, wlid)
            item.setData(0, Qt.UserRole + 1, "water_level")
            if is_staging:
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                active_wl = current_phase.get("active_water_level_id")
                item.setCheckState(0, Qt.Checked if wlid == active_wl else Qt.Unchecked)
        
        self._tree.blockSignals(False)

    # ==================================================================
    # Context Menu
    # ==================================================================

    def _on_context_menu(self, position):
        """Show right-click context menu for items."""
        item = self._tree.itemAt(position)
        if not item:
            return

        item_type = item.data(0, Qt.UserRole + 1)

        menu = QMenu(self)

        if item_type == "material":
            mat_id = item.data(0, Qt.UserRole)
            action_edit = menu.addAction("Edit Material")
            action_delete = menu.addAction("Delete Material")

            chosen = menu.exec(self._tree.mapToGlobal(position))
            if chosen == action_edit:
                self.edit_material_requested.emit(mat_id)
            elif chosen == action_delete:
                self.delete_material_requested.emit(mat_id)

        elif item_type == "polygon":
            poly_idx = item.data(0, Qt.UserRole)
            
            # Don't allow deletion outside of INPUT mode
            if self._state.active_tab in ["STAGING", "RESULT", "MESH"]:
                 return
                 
            chosen = menu.exec(self._tree.mapToGlobal(position))
            if chosen == action_delete:
                self.delete_polygon_requested.emit(poly_idx)
        
        elif item_type == "beam_material":
            mat_id = item.data(0, Qt.UserRole)
            action_edit = menu.addAction("Edit Beam Material")
            action_delete = menu.addAction("Delete Beam Material")
            chosen = menu.exec(self._tree.mapToGlobal(position))
            if chosen == action_edit:
                self.edit_beam_material_requested.emit(mat_id)
            elif chosen == action_delete:
                self.delete_beam_material_requested.emit(mat_id)
        
        elif item_type == "embedded_beam":
            beam_id = item.data(0, Qt.UserRole)
            action_delete = menu.addAction("Delete Beam")
            chosen = menu.exec(self._tree.mapToGlobal(position))
            if chosen == action_delete:
                self.delete_beam_requested.emit(beam_id)

    def _on_item_double_clicked(self, item, column):
        """Double-click to edit a material or beam material."""
        item_type = item.data(0, Qt.UserRole + 1)
        if item_type == "material":
            mat_id = item.data(0, Qt.UserRole)
            self.edit_material_requested.emit(mat_id)
        elif item_type == "beam_material":
            mat_id = item.data(0, Qt.UserRole)
            self.edit_beam_material_requested.emit(mat_id)

    def _on_item_changed(self, item, column):
        """Handle checkbox clicks in Staging tab."""
        if self._is_handling_click or self._state.active_tab != "STAGING":
            return
            
        self._is_handling_click = True
        try:
            self._handle_staging_toggle(item)
        finally:
            self._is_handling_click = False

    def _handle_staging_toggle(self, item):
        item_type = item.data(0, Qt.UserRole + 1)
        if item_type not in ["polygon", "point_load", "line_load", "water_level", "embedded_beam"]:
            return

        # Check for Safety Phase restriction
        current_ph = self._state.current_phase
        if current_ph and current_ph.get("phase_type") == "SAFETY_ANALYSIS":
            self._tree.blockSignals(True)
            val = item.data(0, Qt.UserRole)
            # Sync back to what's in the data (block the UI change)
            is_active = False
            if item_type == "polygon":
                is_active = val in current_ph.get("active_polygon_indices", [])
            elif item_type in ["point_load", "line_load"]:
                is_active = val in current_ph.get("active_load_ids", [])
            elif item_type == "water_level":
                is_active = (val == current_ph.get("active_water_level_id"))
            elif item_type == "embedded_beam":
                is_active = val in current_ph.get("active_beam_ids", [])
            
            item.setCheckState(0, Qt.Checked if is_active else Qt.Unchecked)
            self._tree.blockSignals(False)
            self._state.log(f"Cannot modify elements in '{current_ph.get('name')}'. Safety Analysis stages are immutable.")
            return

        checked = (item.checkState(0) == Qt.Checked)
        val = item.data(0, Qt.UserRole)
        
        ph_idx = self._state.current_phase_index
        phase = dict(self._state.phases[ph_idx])
        
        # Update state
        if item_type == "polygon":
            # Sync active list
            active_list = set(phase.get("active_polygon_indices", []))
            if checked: active_list.add(val)
            else: active_list.discard(val)
            phase["active_polygon_indices"] = list(active_list)

            # Sync material map
            cur_mat = phase.get("current_material", {})
            if checked:
                # Use parent material or base polygon material
                parent_mat = phase.get("parent_material", {})
                if str(val) in parent_mat:
                    cur_mat[str(val)] = parent_mat[str(val)]
                else:
                    poly_data = self._state.polygons[val]
                    cur_mat[str(val)] = poly_data.get("materialId", "default")
            else:
                if str(val) in cur_mat:
                    del cur_mat[str(val)]
            phase["current_material"] = cur_mat
        
        elif item_type in ["point_load", "line_load"]:
            active_list = set(phase.get("active_load_ids", []))
            if checked: active_list.add(val)
            else: active_list.discard(val)
            phase["active_load_ids"] = list(active_list)
            
        elif item_type == "water_level":
            # For water level, it's a direct ID or None
            if checked:
                phase["active_water_level_id"] = val
            else:
                if phase.get("active_water_level_id") == val:
                    phase["active_water_level_id"] = None
        
        elif item_type == "embedded_beam":
            active_list = set(phase.get("active_beam_ids", []))
            if checked: active_list.add(val)
            else: active_list.discard(val)
            phase["active_beam_ids"] = list(active_list)

        self._state.update_phase(ph_idx, phase)
