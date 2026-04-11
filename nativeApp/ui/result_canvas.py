# ui/result_canvas.py
# ===========================================================================
# ResultCanvas — specialized viewer for simulation results
# ===========================================================================

import math
import numpy as np
import matplotlib.tri as tri
import matplotlib.cm as cm
from PySide6.QtWidgets import (
    QGraphicsView, QGraphicsScene, QGraphicsEllipseItem,
    QGraphicsLineItem, QGraphicsPolygonItem, QGraphicsPathItem, QGraphicsItem,
    QFrame, QVBoxLayout, QLabel, QToolTip
)
from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import (
    QPen, QBrush, QColor, QPolygonF, QPainter, QPainterPath,
    QWheelEvent, QMouseEvent, QTransform
)

from core.state import ProjectState, OutputType

def u_get(obj, key, default=None):
    """Universal getter for both dicts and objects."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)

# Constants
GRID_EXTENT  = 200.0
POINT_RADIUS = 0.15
COLOR_AXIS_X       = QColor("#f87171")
COLOR_AXIS_Y       = QColor("#60a5fa")
COLOR_MESH_EDGE    = QColor(148, 163, 184, 150)
ZOOM_FACTOR       = 1.15

def get_jet_color(v: float) -> QColor:
    """Map 0-1 value to Jet color scale (Blue -> Cyan -> Green -> Yellow -> Red)."""
    t = max(0.0, min(1.0, v))
    if t < 0.125: return QColor(0, 0, int(127 + 1020 * t))
    if t < 0.375: return QColor(0, int(1020 * (t - 0.125)), 255)
    if t < 0.625: return QColor(int(1020 * (t - 0.375)), 255, int(255 - 1020 * (t - 0.375)))
    if t < 0.875: return QColor(255, int(255 - 1020 * (t - 0.625)), 0)
    return QColor(int(255 - 127 * (t - 0.875)), 0, 0)

def get_stress_color(v: float) -> QColor:
    """Inverted Jet for stresses (Min=Red, Max=Blue)."""
    return get_jet_color(1.0 - v)

class ResultScene(QGraphicsScene):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSceneRect(-GRID_EXTENT, -GRID_EXTENT, GRID_EXTENT * 2, GRID_EXTENT * 2)

    def drawBackground(self, painter: QPainter, rect: QRectF):
        """Draw a clean solid background with origin axes (No Grid as requested)."""
        super().drawBackground(painter, rect)
        painter.fillRect(rect, QColor("#fafafa"))

        # Origin axes
        left, right = rect.left(), rect.right()
        top, bottom = rect.top(), rect.bottom()
        
        painter.setPen(QPen(COLOR_AXIS_X, 0))
        painter.drawLine(QPointF(left, 0), QPointF(right, 0))
        painter.setPen(QPen(COLOR_AXIS_Y, 0))
        painter.drawLine(QPointF(0, top), QPointF(0, bottom))

class ResultCanvas(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._scene = ResultScene(self)
        self.setScene(self._scene)

        # View configuration
        self.setRenderHint(QPainter.Antialiasing, True)
        self.setDragMode(QGraphicsView.NoDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorViewCenter)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setMouseTracking(True)

        # Flip Y (Y-up) and apply scale
        self.scale(1, -1)
        self.scale(30, 30)

        self._state = ProjectState.instance()
        self._polygon_items: list[QGraphicsPolygonItem] = []
        self._mesh_items: list[QGraphicsPathItem] = []
        self._mesh_data: dict | None = None
        self._load_items: list[QGraphicsItem] = []
        self._water_items: list[QGraphicsItem] = []
        self._heatmap_item: QGraphicsItem | None = None
        self._current_mouse_scene_pos = QPointF(0, 0)

        # Trigger repaint when settings change (grid/rulers)
        self._state.settings_changed.connect(lambda s: self.viewport().update())

        # Connect signals
        self._state.polygons_changed.connect(self._refresh_view)
        self._state.mesh_response_changed.connect(self._on_mesh_response_changed)
        self._state.current_phase_changed.connect(self._refresh_view)
        self._state.active_tab_changed.connect(self._on_tab_changed)
        self._state.output_settings_changed.connect(lambda _: self._refresh_view())
        self._state.solver_response_changed.connect(lambda _: self._refresh_view())

        # Initial render
        self._refresh_view()
        if self._state.mesh_response:
            self._on_mesh_response_changed(self._state.mesh_response)

        # Pan state
        self._is_panning = False
        self._pan_start = QPointF()

    def _refresh_view(self):
        """Full re-render of model components based on current phase results."""
        self._render_polygons()
        self._render_mesh()
        self.viewport().update()

    def _on_tab_changed(self, tab):
        if tab == "RESULT":
            self._refresh_view()

    def _render_polygons(self):
        """Draw the base geometry polygons, filtered by phase."""
        for item in self._polygon_items: self._scene.removeItem(item)
        self._polygon_items.clear()
        if not self._state.polygons: return

        current_phase = self._state.current_phase
        active_indices = current_phase.get("active_polygon_indices", []) if current_phase else []

        for i, poly_data in enumerate(self._state.polygons):
            if i not in active_indices: continue

            qpoly = QPolygonF()
            # Polygons in state have 'points' (x, y)
            for pt in poly_data.get("points", []):
                qpoly.append(QPointF(pt["x"], pt["y"]))

            # Material-based coloring
            fill_color = QColor("#4CAF50")
            mat_id = poly_data.get("materialId")
            
            mat_overrides = current_phase.get("current_material", {}) if current_phase else {}
            if str(i) in mat_overrides: mat_id = mat_overrides[str(i)]
            
            if mat_id:
                for mat in self._state.materials:
                    if mat.get("id") == mat_id:
                        fill_color = QColor(mat.get("color", "#4CAF50"))
                        break
            
            fill_color.setAlpha(40) # Subtle background
            
            pen = QPen(QColor("#BBBBBB"), 0)
            pen.setCosmetic(True)
            item = self._scene.addPolygon(qpoly, pen, QBrush(fill_color))
            item.setZValue(5)
            self._polygon_items.append(item)

    def _on_mesh_response_changed(self, mesh_data: dict | None):
        """Handle new mesh data from the backend."""
        self._mesh_data = mesh_data
        self._render_mesh()

    def _get_stress_value(self, s: any, out_type: OutputType) -> float:
        """Calculate scalar value for a Gauss Point result using universal access."""
        p_total = u_get(s, "pwp_total", 0.0)
        
        if out_type == OutputType.PWP_STEADY: return u_get(s, "pwp_steady", 0.0)
        if out_type == OutputType.PWP_EXCESS: return u_get(s, "pwp_excess", 0.0)
        if out_type == OutputType.PWP_TOTAL:  return p_total

        sig_xx = u_get(s, "sig_xx", 0.0)
        sig_yy = u_get(s, "sig_yy", 0.0)
        sig_xy = u_get(s, "sig_xy", 0.0)
        
        # Principal Stresses
        avg = (sig_xx + sig_yy) / 2.0
        diff = (sig_xx - sig_yy) / 2.0
        radius = math.sqrt(diff*diff + sig_xy*sig_xy)
        
        if out_type == OutputType.SIGMA_1: return avg - radius
        if out_type == OutputType.SIGMA_3: return avg + radius
        if out_type == OutputType.SIGMA_1_EFF: return (avg - radius) - p_total
        if out_type == OutputType.SIGMA_3_EFF: return (avg + radius) - p_total
        
        return 0.0

    def _render_mesh(self):
        """Draw the FEM mesh, applying deformation and professional heatmap contours."""
        # 1. Cleanup
        for item in self._mesh_items: self._scene.removeItem(item)
        self._mesh_items.clear()
        if self._heatmap_item:
            self._scene.removeItem(self._heatmap_item)
            self._heatmap_item = None

        if not self._mesh_data: return

        # 0. Build Clip Path (Union of active polygons)
        clip_path = QPainterPath()
        actual_polys = self._state.polygons
        current_phase = self._state.current_phase
        active_indices = set(current_phase.get("active_polygon_indices", [])) if current_phase else set()
        
        # If no active indices but we have polys, show all for debugging/safety
        if not active_indices and actual_polys:
            active_indices = set(range(len(actual_polys)))

        for idx in active_indices:
            if idx < len(actual_polys):
                pts = actual_polys[idx].get("points", [])
                if len(pts) > 2:
                    qpoly = QPolygonF()
                    for pt in pts: qpoly.append(QPointF(pt["x"], pt["y"]))
                    clip_path.addPolygon(qpoly)

        nodes = self._mesh_data.get("nodes", [])
        elements = self._mesh_data.get("elements", [])
        el_mats = self._mesh_data.get("element_materials", [])
        
        current_phase = self._state.current_phase
        phase_results = self._state.get_phase_results(current_phase["id"]) if current_phase else None
        active_indices = set(current_phase.get("active_polygon_indices", [])) if current_phase else set()
        
        out_type = self._state.output_type
        # 2. Context-aware scale: only apply to DEFORMED_MESH view per user request
        scale = self._state.deformation_scale if out_type == OutputType.DEFORMED_MESH else 0
        is_contour = out_type not in [OutputType.DEFORMED_MESH, OutputType.YIELD_STATUS]

        # 3. Build Nodal Displacement Map
        disp_map = {} 
        if phase_results and "displacements" in phase_results:
            for d in phase_results["displacements"]:
                disp_map[u_get(d, "id") - 1] = (u_get(d, "ux"), u_get(d, "uy"))

        # 4. Map Elements to Polygons
        el_to_poly = { em["element_id"] - 1: em.get("polygon_id") for em in el_mats }

        # 5. Populate Nodal Values for Heatmap/Contour
        self._last_nodal_vals = {} 
        nodal_raw = []
        if is_contour and phase_results:
            ot_str = str(out_type).lower()
            if "stresses" in phase_results and ("sigma" in ot_str or "pwp" in ot_str):
                stress_gp_map = {} 
                for s in phase_results["stresses"]:
                    eid = u_get(s, "element_id")
                    if eid not in stress_gp_map: stress_gp_map[eid] = [None, None, None]
                    gp_id = u_get(s, "gp_id", 1)
                    if 1 <= gp_id <= 3: stress_gp_map[eid][gp_id-1] = s

                EXTRAP = [ [1.666, -0.333, -0.333], [-0.333, 1.666, -0.333], [-0.333, -0.333, 1.666] ]
                for eid, gps in stress_gp_map.items():
                    if None in gps: continue
                    elem = elements[eid-1]
                    gp_vals = [ self._get_stress_value(g, out_type) for g in gps ]
                    for ni in range(3): 
                        node_idx = elem[ni]
                        val = EXTRAP[ni][0]*gp_vals[0] + EXTRAP[ni][1]*gp_vals[1] + EXTRAP[ni][2]*gp_vals[2]
                        if node_idx not in self._last_nodal_vals: self._last_nodal_vals[node_idx] = [0.0, 0]
                        self._last_nodal_vals[node_idx][0] += val; self._last_nodal_vals[node_idx][1] += 1
                        nodal_raw.append(val)
            elif "displacements" in phase_results:
                for d in phase_results["displacements"]:
                    n_idx = u_get(d, "id") - 1
                    ux, uy = u_get(d, "ux"), u_get(d, "uy")
                    if out_type == OutputType.DEFORMED_CONTOUR: val = math.sqrt(ux*ux + uy*uy)
                    elif out_type == OutputType.DEFORMED_CONTOUR_UX: val = abs(ux)
                    elif out_type == OutputType.DEFORMED_CONTOUR_UY: val = abs(uy)
                    else: val = 0.0
                    self._last_nodal_vals[n_idx] = [val, 1]
                    nodal_raw.append(val)

        # 6. FACETED COLORING (Manual Element-by-Element)
        # We calculate a value per element and fill it directly.
        # This is inherently clipped to the mesh geometry.
        
        # Helper to map 0..1 to a Jet-style colormap color
        def get_jet_color(v: float, alpha: int = 255) -> QColor:
            v = max(0.0, min(1.0, v))
            r, g, b = 0, 0, 0
            if v < 0.25: r, g, b = 0, int(v*4*255), 255
            elif v < 0.5: r, g, b = 0, 255, int((0.5-v)*4*255)
            elif v < 0.75: r, g, b = int((v-0.5)*4*255), 255, 0
            else: r, g, b = 255, int((1.0-v)*4*255), 0
        v_min, v_max = 0.0, 1.0
        if self._last_nodal_vals:
            # Use averaged values for normalization to match Legend and avoid raw spikes
            avg_vals = [v[0]/v[1] for v in self._last_nodal_vals.values()]
            v_min, v_max = min(avg_vals), max(avg_vals)
            if v_min == v_max: v_max += 1e-9

        # 6. VECTOR CONTOUR GENERATION (Layer 1: Fills at Z=12)
        if is_contour and self._last_nodal_vals:
            import matplotlib.tri as tri
            import matplotlib.cm as cm
            import numpy as np
            # Group elements by Polygon ID for localized contouring
            poly_to_elements = {}
            for idx, elem in enumerate(elements):
                pid = el_to_poly.get(idx)
                if pid is None or pid not in active_indices: continue
                if pid not in poly_to_elements: poly_to_elements[pid] = []
                poly_to_elements[pid].append(idx)

            num_levels = 20
            # Use standard 'jet' and manual inversion logic to keep consistent with Legend CSS
            cmap = cm.get_cmap('jet')
            
            for pid, elem_indices in poly_to_elements.items():
                try:
                    # Collect nodes for this polygon subset
                    subset_tri_indices = []
                    involved_node_indices = set()
                    for idx in elem_indices:
                        e = elements[idx]
                        subset_tri_indices.append(e[:3]) # Only corner nodes for triangulation
                        involved_node_indices.update(e[:6]) # All nodes for value collection
                    
                    sub_nodes_idx = sorted(list(involved_node_indices))
                    node_map = {old: new for new, old in enumerate(sub_nodes_idx)}
                    
                    sub_x = [nodes[i][0] for i in sub_nodes_idx]
                    sub_y = [nodes[i][1] for i in sub_nodes_idx]
                    sub_v = [ (self._last_nodal_vals.get(i, [0.0, 1])[0]/self._last_nodal_vals.get(i, [0.0, 1])[1]) for i in sub_nodes_idx]
                    
                    # Apply deformation to local nodes if needed
                    if scale != 0:
                        for i, n_idx in enumerate(sub_nodes_idx):
                            if n_idx in disp_map:
                                dx, dy = disp_map[n_idx]
                                sub_x[i] += dx * scale; sub_y[i] += dy * scale

                    sub_tri = [[node_map[ni] for ni in tri] for tri in subset_tri_indices]
                    
                    if len(sub_x) < 3 or not sub_tri: continue
                    
                    triang = tri.Triangulation(sub_x, sub_y, sub_tri)
                    levels = np.linspace(v_min, v_max, num_levels + 1)
                    
                    cntr = self._get_contourf_data(triang, sub_v, levels)
                    
                    # Matplotlib 3.8+ Compatibility: use get_paths() directly on the ContourSet
                    # Each path in cntr.get_paths() corresponds to one contour band
                    paths = cntr.allsegs if hasattr(cntr, 'allsegs') else cntr.get_paths()
                    
                    for level_idx, path_data in enumerate(paths):
                        t_val = (levels[level_idx] + levels[level_idx+1]) / 2.0
                        v_norm = (t_val - v_min) / (v_max - v_min)
                        
                        color = cmap(v_norm)
                        qcolor = QColor(int(color[0]*255), int(color[1]*255), int(color[2]*255), 255)
                        
                        for path in cntr.get_paths()[level_idx:level_idx+1]:
                            qpath = QPainterPath()
                            for poly in path.to_polygons():
                                qpoly = QPolygonF()
                                for pt in poly: qpoly.append(QPointF(pt[0], pt[1]))
                                if not qpoly.isEmpty():
                                    qpath.addPolygon(qpoly)
                            
                            if not qpath.isEmpty():
                                c_item = self._scene.addPath(qpath, QPen(qcolor, 0), QBrush(qcolor))
                                c_item.setZValue(12)
                                self._mesh_items.append(c_item)

                except Exception as e:
                    print(f"Contour Warning for PID {pid}: {e}")

        # 7. ELEMENT LOOP (Layer 2 Grid + Material/Status Fills)
        mesh_pen = QPen(COLOR_MESH_EDGE, 0); mesh_pen.setCosmetic(True)
        mat_overrides = current_phase.get("current_material", {}) if current_phase else {}
        
        for idx, elem in enumerate(elements):
            pid = el_to_poly.get(idx)
            if pid is not None and pid not in active_indices: continue
            if len(elem) < 3: continue
            
            is_yielded = False

            if out_type == OutputType.YIELD_STATUS and phase_results and "stresses" in phase_results:
                eid = idx + 1
                for s in phase_results["stresses"]:
                    if u_get(s, "element_id") == eid and u_get(s, "is_yielded", False):
                        is_yielded = True; break

            # Base coordinates (deformed)
            pts = []
            for ni in range(3):
                n_idx = elem[ni]
                x, y = nodes[n_idx][0], nodes[n_idx][1]
                if n_idx in disp_map:
                    dx, dy = disp_map[n_idx]; x += dx * scale; y += dy * scale
                pts.append(QPointF(x, y))

            # --- Layer 1 Alternate: Material / Status Fills ---
            fill_color = Qt.NoBrush
            if out_type == OutputType.DEFORMED_MESH:
                m_color = QColor("#d4d4d8")
                mat_id = el_mats[idx].get("materialId") if idx < len(el_mats) else None
                if pid is not None and str(pid) in mat_overrides: mat_id = mat_overrides[str(pid)]
                if mat_id:
                    for m in self._state.materials:
                        if m.get("id") == mat_id:
                            m_color = QColor(m.get("color", "#d4d4d8")); break
                m_color.setAlpha(153)
                fill_color = QBrush(m_color)
                item = self._scene.addPolygon(pts, Qt.NoPen, fill_color)
                item.setZValue(12); self._mesh_items.append(item)

            elif out_type == OutputType.YIELD_STATUS:
                # SPECIAL TREATMENT: Draw Gauss Points (GPs) as small circles
                gp_fill = QBrush(QColor("#10b981")) # Default Green
                if is_yielded:
                    gp_fill = QBrush(QColor("#ef4444")) # Yielded Red
                
                # Barycentric GP positions for 3-point rule (approx)
                gp_coords = [(2/3, 1/6, 1/6), (1/6, 2/3, 1/6), (1/6, 1/6, 2/3)]
                tri_nodes = [nodes[elem[0]], nodes[elem[1]], nodes[elem[2]]]
                
                for b1, b2, b3 in gp_coords:
                    gx = b1*tri_nodes[0][0] + b2*tri_nodes[1][0] + b3*tri_nodes[2][0]
                    gy = b1*tri_nodes[0][1] + b2*tri_nodes[1][1] + b3*tri_nodes[2][1]
                    
                    # Apply deformation if needed
                    # Find nearest corner node for deformation or just interpolate
                    for j in range(3):
                        n_idx = elem[j]
                        if n_idx in disp_map:
                            dx, dy = disp_map[n_idx]
                            # Simple interpolation of displacement
                            gx += dx * scale * (1/3); gy += dy * scale * (1/3)

                    # Draw high-visibility Dot
                    gp_item = self._scene.addEllipse(gx-0.05, gy-0.05, 0.1, 0.1, QPen(Qt.NoPen), gp_fill)
                    gp_item.setZValue(25) # Top level
                    gp_item.setData(10, "gp_status") # Tag for hover identification
                    self._mesh_items.append(gp_item)

            # --- Layer 2: ORIGINAL MESH WIREFRAME (Z=15) ---
            wire_item = self._scene.addPolygon(pts, mesh_pen, Qt.NoBrush)
            wire_item.setZValue(15)
            self._mesh_items.append(wire_item)

        # --- Layer 3: PROJECT POLYGON BOUNDARIES (Z=20) ---
        nodes_lookup = {(round(n[0], 5), round(n[1], 5)): i for i, n in enumerate(nodes)}
        border_pen = QPen(QColor("#94a3b8"), 1.5) 
        border_pen.setCosmetic(True)
        
        for poly in self._state.polygons:
            vertices = poly.get("vertices", [])
            if not vertices: continue
            border_pts = []
            for v in vertices:
                vx, vy = v["x"], v["y"]
                border_pts.append(QPointF(vx, vy))
            if border_pts:
                p_item = self._scene.addPolygon(border_pts, border_pen, Qt.NoBrush)
                p_item.setZValue(20); self._mesh_items.append(p_item)

        # --- Layer 4: STRUCTURAL BEAMS (Z=22) ---
        show_ebr = getattr(self._state, "show_ebr", False)
        if show_ebr:
            bm_lookup = {m.get("id"): m for m in self._state.beam_materials}
            active_beam_ids = set(current_phase.get("active_beam_ids", [])) if current_phase else set()
            
            # Helper to get deformed positions
            def get_deformed_pos(n_idx):
                x, y = nodes[n_idx][0], nodes[n_idx][1]
                if n_idx in disp_map:
                    dx, dy = disp_map[n_idx]; x += dx * scale; y += dy * scale
                return QPointF(x, y)

            # Draw beams using assignments (segmented/curved)
            assignments = self._mesh_data.get("embedded_beam_assignments", [])
            beam_defs = {b.get("id"): b for b in self._state.embedded_beams}

            for assign in assignments:
                bid = assign.get("beam_id")
                if bid not in active_beam_ids: continue
                
                b_def = beam_defs.get(bid, {})
                mid = b_def.get("materialId")
                color = QColor(bm_lookup[mid].get("color", "#2563eb")) if mid and mid in bm_lookup else QColor("#2563eb")
                
                pen = QPen(color, 4)
                pen.setCosmetic(True)
                
                n_ids = assign.get("nodes", [])
                if len(n_ids) < 2: continue

                # Draw segments between nodes
                for i in range(len(n_ids) - 1):
                    p1 = get_deformed_pos(n_ids[i] - 1)
                    p2 = get_deformed_pos(n_ids[i+1] - 1)
                    
                    line_item = self._scene.addLine(p1.x(), p1.y(), p2.x(), p2.y(), pen)
                    line_item.setZValue(22)
                    line_item.setData(Qt.UserRole, bid)
                    line_item.setData(Qt.UserRole + 1, "embedded_beam")
                    self._mesh_items.append(line_item)

                # 5. Draw Connection Marker at Head
                h_idx = b_def.get("head_point_index", 0)
                h_node_gi = (n_ids[0] - 1) if h_idx == 0 else (n_ids[-1] - 1)
                neighbor_gi = (n_ids[1] - 1) if h_idx == 0 else (n_ids[-2] - 1)
                
                h_pos = get_deformed_pos(h_node_gi)
                n_pos = get_deformed_pos(neighbor_gi)
                
                head_conn = str(b_def.get("head_connection_type", "FIXED")).upper()
                marker_size = 0.15
                
                h_pen = QPen(color, 0.1)
                h_brush = QBrush(color)
                
                if head_conn in ["FIXED", "FIX"]:
                    # Square
                    box_sz = 0.15
                    rect_item = self._scene.addRect(
                        h_pos.x() - box_sz/2, h_pos.y() - box_sz/2, box_sz, box_sz,
                        h_pen, h_brush
                    )
                    rect_item.setZValue(25)
                    self._mesh_items.append(rect_item)
                else:
                    # Triangle pointing into beam along the first segment
                    angle_rad = math.atan2(n_pos.y() - h_pos.y(), n_pos.x() - h_pos.x())
                    
                    p_tri = [QPointF(0, 0), QPointF(marker_size, -marker_size/2.5), QPointF(marker_size, marker_size/2.5)]
                    q_poly = QPolygonF(p_tri)
                    
                    trans = QTransform().translate(h_pos.x(), h_pos.y()).rotateRadians(angle_rad)
                    rotated_poly = trans.map(q_poly)
                    
                    tri_item = self._scene.addPolygon(rotated_poly, h_pen, h_brush)
                    tri_item.setZValue(25)
                    self._mesh_items.append(tri_item)

        # Update Legend Panel
        self._update_legend(v_min, v_max, out_type)

    def _update_legend(self, v_min, v_max, out_type):
        """Show/Hide and update the dynamic results legend."""
        if not hasattr(self, "_legend_panel"):
            self._legend_panel = self._create_legend_panel()

        is_contour = out_type not in [OutputType.DEFORMED_MESH, OutputType.YIELD_STATUS]
        self._legend_panel.setVisible(is_contour)
        
        if is_contour:
            self._lbl_min.setText(f"{v_min:.3f}")
            self._lbl_max.setText(f"{v_max:.3f}")
            self._lbl_title.setText(str(out_type).replace("OutputType.", "").replace("_", " "))

    def _create_legend_panel(self):
        """Create a floating semi-transparent legend widget."""
        panel = QFrame(self)
        panel.setStyleSheet("""
            QFrame { background: rgba(255, 255, 255, 0.9); border: 1px solid #e2e8f0; border-radius: 6px; }
            QLabel { color: #475569; font-family: 'Segoe UI', sans-serif; font-size: 11px; border: none; }
        """)
        panel.setFixedSize(200, 60)
        
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(2)
        
        self._lbl_title = QLabel("Result")
        self._lbl_title.setStyleSheet("font-weight: bold; color: #1e293b;")
        layout.addWidget(self._lbl_title, 0, Qt.AlignCenter)
        
        # Color bar
        bar = QFrame()
        bar.setFixedHeight(12)
        bar.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                stop:0 #00007f, stop:0.25 #00ffff, stop:0.5 #00ff00, stop:0.75 #ffff00, stop:1 #7f0000);
            border: 1px solid #94a3b8;
        """)
        layout.addWidget(bar)
        
        # Labels
        lbl_box = QFrame()
        lbl_layout = QVBoxLayout(lbl_box) # Simplified for space
        lbl_layout.setContentsMargins(0,0,0,0)
        
        sub_layout = QVBoxLayout()
        sub_layout.setDirection(QVBoxLayout.LeftToRight)
        self._lbl_min = QLabel("0.000")
        self._lbl_max = QLabel("1.000")
        sub_layout.addWidget(self._lbl_min)
        sub_layout.addStretch()
        sub_layout.addWidget(self._lbl_max)
        layout.addLayout(sub_layout)
        
        panel.move(self.width() - 210, self.height() - 70)
        return panel

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "_legend_panel"):
            self._legend_panel.move(self.width() - 210, self.height() - 70)

    def wheelEvent(self, event: QWheelEvent):
        """Standard zoom behavior centered on the cursor."""
        angle = event.angleDelta().y()
        if angle > 0:
            factor = ZOOM_FACTOR
        elif angle < 0:
            factor = 1.0 / ZOOM_FACTOR
        else:
            return
        self.scale(factor, factor)

    def mousePressEvent(self, event: QMouseEvent):
        """Middle-mouse panning start."""
        if event.button() == Qt.MiddleButton:
            self._is_panning = True
            self._pan_start = event.position()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        """Combined tracking: Coordinate tooltip, Hover info, and Middle-mouse Pan."""
        # 1. Track scene coordinates
        scene_pos = self.mapToScene(event.position().toPoint())
        self._current_mouse_scene_pos = scene_pos
        
        # 2. Handle Panning
        if self._is_panning:
            delta = event.position() - self._pan_start
            self._pan_start = event.position()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - int(delta.x()))
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - int(delta.y()))
            event.accept()
        else:
            # 3. Handle Result Tooltips (only when not panning)
            out_type = self._state.output_type
            if out_type not in [OutputType.DEFORMED_MESH, OutputType.YIELD_STATUS]:
                self._handle_hover_tooltip(scene_pos, event.globalPos())
            super().mouseMoveEvent(event)
        
        # Repaint rulers/UI overlay
        self.viewport().update()

    def mouseReleaseEvent(self, event: QMouseEvent):
        """Middle-mouse panning end."""
        if event.button() == Qt.MiddleButton:
            self._is_panning = False
            self.setCursor(Qt.ArrowCursor)
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        """Handle double-click on EBR to show details."""
        item = self.itemAt(event.position().toPoint())
        if item:
            bid = item.data(Qt.UserRole)
            itype = item.data(Qt.UserRole + 1)
            
            if itype == "embedded_beam" and bid:
                self._open_beam_detail(bid)
                event.accept()
                return
        
        super().mouseDoubleClickEvent(event)

    def _open_beam_detail(self, beam_id):
        """Open the detailed output window for a specific beam."""
        from ui.beam_detail_dialog import BeamDetailDialog
        dlg = BeamDetailDialog(beam_id, self.window())
        dlg.show()
        dlg.raise_()
        dlg.activateWindow()

    def _on_output_settings_changed(self, settings):
        """Trigger re-render when contour type, scale, or EBR visibility changes."""
        self._render_mesh()

    def _handle_hover_tooltip(self, scene_pos, global_pos):
        """Find the element under the mouse and interpolate its value."""
        if not self._mesh_data: return
        
        # Use QGraphicsScene's efficient item lookup
        item = self.itemAt(self.mapFromGlobal(global_pos))
        if not item: 
            QToolTip.hideText()
            return

        # Check if we clicked a contour band or mesh item
        # Since we want to find the value at the point, we'll use the nodal lookup
        nodes = self._mesh_data.get("nodes", [])
        elements = self._mesh_data.get("elements", [])
        
        # Optimized lookup: find which triangle contain the point
        found_val = None
        
        # Performance trick: only check a small region around scene_pos
        items = self._scene.items(QRectF(scene_pos.x()-1, scene_pos.y()-1, 2, 2))
        
        # If hovering over a GP dot, show status
        for it in items:
            if it.data(10) == "gp_status":
                QToolTip.showText(global_pos, "Yield Point (Plastic)", self)
                return

        for elem in elements:
            if len(elem) < 3: continue
            v1, v2, v3 = nodes[elem[0]], nodes[elem[1]], nodes[elem[2]]
            
            # Fast BBox check first
            min_x, max_x = min(v1[0], v2[0], v3[0]), max(v1[0], v2[0], v3[0])
            min_y, max_y = min(v1[1], v2[1], v3[1]), max(v1[1], v2[1], v3[1])
            
            if not (min_x <= scene_pos.x() <= max_x and min_y <= scene_pos.y() <= max_y):
                continue
                
            # Point in triangle test
            def pt_in_tri(p, p0, p1, p2):
                s = (p0[0] - p2[0]) * (p[1] - p2[1]) - (p0[1] - p2[1]) * (p[0] - p2[0])
                t = (p1[0] - p0[0]) * (p[1] - p0[1]) - (p1[1] - p0[1]) * (p[0] - p0[0])
                if (s < 0) != (t < 0) and s != 0 and t != 0: return False
                d = (p2[0] - p1[0]) * (p[1] - p2[1]) - (p2[1] - p1[1]) * (p[0] - p2[0])
                return (d < 0) == (s < 0) or d == 0
                
            if pt_in_tri((scene_pos.x(), scene_pos.y()), v1, v2, v3):
                # Barycentric Interpolation for pinpoint accuracy
                def get_barycentric(p, p1, p2, p3):
                    denom = (p2[1]-p3[1])*(p1[0]-p3[0]) + (p3[0]-p2[0])*(p1[1]-p3[1])
                    if abs(denom) < 1e-12: return 1/3, 1/3, 1/3
                    w1 = ((p2[1]-p3[1])*(p[0]-p3[0]) + (p3[0]-p2[0])*(p[1]-p3[1])) / denom
                    w2 = ((p3[1]-p1[1])*(p[0]-p3[0]) + (p1[0]-p3[0])*(p[1]-p3[1])) / denom
                    w3 = 1.0 - w1 - w2
                    return w1, w2, w3

                w1, w2, w3 = get_barycentric((scene_pos.x(), scene_pos.y()), v1, v2, v3)
                
                # Retrieve individual nodal results
                nv1 = self._get_nodal_value_safe(elem[0])
                nv2 = self._get_nodal_value_safe(elem[1])
                nv3 = self._get_nodal_value_safe(elem[2])
                
                if None not in [nv1, nv2, nv3]:
                    found_val = w1*nv1 + w2*nv2 + w3*nv3
                break
        
        if found_val is not None:
            title = self._lbl_title.text()
            QToolTip.showText(global_pos, f"<b>{title}</b><br/>Value: {found_val:.4f}", self)
        else:
            QToolTip.hideText()

    def _get_nodal_value_safe(self, node_idx):
        """Retrieve the current result value at a specific node index."""
        if hasattr(self, "_last_nodal_vals") and node_idx in self._last_nodal_vals:
            raw = self._last_nodal_vals[node_idx]
            return raw[0] / raw[1]
        return None

    def _get_contourf_data(self, triang, values, levels):
        """Internal helper to bypass figure creation for tricontourf extraction."""
        import matplotlib.pyplot as plt
        fig = plt.figure() # Temporary figure
        ax = fig.add_subplot(111)
        cntr = ax.tricontourf(triang, values, levels=levels)
        plt.close(fig)
        return cntr

    def drawForeground(self, painter: QPainter, rect: QRectF):
        """Draw dynamic rulers and coordinate tooltip on top of the results view."""
        state = self._state

        painter.save()
        painter.resetTransform()

        view_rect = self.viewport().rect()
        W, H = view_rect.width(), view_rect.height()
        RULER_SIZE = 22

        if state.settings.get("show_ruler", True):
            # Draw backgrounds
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(255, 255, 255, 240))
            painter.drawRect(0, 0, W, RULER_SIZE)
            painter.drawRect(0, 0, RULER_SIZE, H)

            # Draw border lines
            painter.setPen(QColor("#d4d4d8"))
            painter.drawLine(0, RULER_SIZE, W, RULER_SIZE)
            painter.drawLine(RULER_SIZE, 0, RULER_SIZE, H)

            # Draw text & ticks
            font = painter.font()
            font.setPointSize(7)
            painter.setFont(font)
            painter.setPen(QColor("#71717a"))

            transform = self.viewportTransform()
            inv_transform, _ = transform.inverted()

            scene_width = inv_transform.mapRect(QRectF(view_rect)).width()
            step = 1.0
            if scene_width > 500: step = 100.0
            elif scene_width > 100: step = 10.0
            elif scene_width > 50: step = 5.0
            
            # Horizontal Ruler
            left_scene = inv_transform.map(QPointF(0, 0)).x()
            right_scene = inv_transform.map(QPointF(W, 0)).x()
            x = int(left_scene / step) * step
            while x <= right_scene:
                px = transform.map(QPointF(x, 0)).x()
                if px >= RULER_SIZE:
                    painter.drawLine(px, RULER_SIZE - 4, px, RULER_SIZE)
                    painter.drawText(px + 2, RULER_SIZE - 6, f"{x:g}")
                x += step

            # Vertical Ruler
            top_scene = inv_transform.map(QPointF(0, 0)).y()
            bottom_scene = inv_transform.map(QPointF(0, H)).y()
            min_y, max_y = min(top_scene, bottom_scene), max(top_scene, bottom_scene)
            y = int(min_y / step) * step
            while y <= max_y:
                py = transform.map(QPointF(0, y)).y()
                if py >= RULER_SIZE:
                    painter.drawLine(RULER_SIZE - 4, py, RULER_SIZE, py)
                    painter.save()
                    painter.translate(RULER_SIZE - 6, py - 6)
                    painter.rotate(-90)
                    painter.drawText(0, 0, f"{y:g}")
                    painter.restore()
                y += step
                
            # Top-left block
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(255, 255, 255, 255))
            painter.drawRect(0, 0, RULER_SIZE, RULER_SIZE)
            painter.setPen(QColor("#d4d4d8"))
            painter.drawLine(RULER_SIZE, 0, RULER_SIZE, RULER_SIZE)
            painter.drawLine(0, RULER_SIZE, RULER_SIZE, RULER_SIZE)

        # Coordinate Tooltip
        if hasattr(self, '_current_mouse_scene_pos') and self._current_mouse_scene_pos:
            coord_text = f"X: {self._current_mouse_scene_pos.x():g}  Y: {self._current_mouse_scene_pos.y():g}"
            font = painter.font(); font.setPointSize(8); painter.setFont(font)
            fm = painter.fontMetrics()
            tw, th = fm.horizontalAdvance(coord_text), fm.height()

            box_x = RULER_SIZE + 10 if state.settings.get("show_ruler", True) else 10
            box_y = H - th - 16
            
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(255, 255, 255, 230))
            painter.drawRoundedRect(box_x, box_y, tw + 16, th + 8, 4, 4)
            painter.setPen(QColor("#3f3f46")) # zinc-700
            painter.drawText(box_x + 8, box_y + th + 1, coord_text)

        painter.restore()

