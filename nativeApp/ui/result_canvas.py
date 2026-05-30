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


def _quad9_contour_triangles(elem: list) -> list[tuple]:
    """
    Subdivide a Quad9 into sub-triangles for matplotlib tricontourf.
    Uses all 9 nodes (corner + midside + center) so contours are smooth quads, not T3 shards.
    """
    if len(elem) >= 9:
        n = elem
        return [
            (n[0], n[4], n[8]),
            (n[4], n[1], n[8]),
            (n[1], n[5], n[8]),
            (n[5], n[2], n[8]),
            (n[2], n[6], n[8]),
            (n[6], n[3], n[8]),
            (n[3], n[7], n[8]),
            (n[7], n[0], n[8]),
        ]
    if len(elem) >= 4:
        n = elem
        return [(n[0], n[1], n[2]), (n[0], n[2], n[3])]
    return [tuple(elem[:3])]


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
        self._bc_items: list[QGraphicsItem] = []
        self._current_mouse_scene_pos = QPointF(0, 0)

        # Trigger full refresh when settings change (BCs, etc.)
        self._state.settings_changed.connect(lambda s: self._refresh_view())

        # Connect signals
        self._state.polygons_changed.connect(self._refresh_view)
        self._state.mesh_response_changed.connect(self._on_mesh_response_changed)
        self._state.current_phase_changed.connect(self._refresh_view)
        self._state.active_tab_changed.connect(self._on_tab_changed)
        self._state.output_settings_changed.connect(lambda _: self._refresh_view())
        self._state.solver_response_changed.connect(lambda _: self._refresh_view())
        self._state.result_visibility_changed.connect(self._refresh_view)

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
        self._render_loads()
        self._render_bc_markers()
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
            if i in self._state.result_hidden_polygons: continue

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
        self._el_to_poly = { em["element_id"] - 1: em.get("polygon_id") for em in el_mats }

        # 5. Populate Nodal Values for Heatmap/Contour
        self._last_nodal_vals = {} 
        nodal_raw = []
        if is_contour and phase_results:
            ot_str = str(out_type).lower()
            if "stresses" in phase_results and ("sigma" in ot_str or "pwp" in ot_str):
                stress_gp_map = {} 
                for s in phase_results["stresses"]:
                    eid = u_get(s, "element_id")
                    from engine.solver.element_quad9 import (
                        GAUSS_POINTS_2D,
                        NUM_GAUSS_POINTS,
                        shape_functions_quad9,
                    )
                    if eid not in stress_gp_map:
                        stress_gp_map[eid] = [None] * NUM_GAUSS_POINTS
                    gp_id = u_get(s, "gp_id", 1)
                    if 1 <= gp_id <= NUM_GAUSS_POINTS:
                        stress_gp_map[eid][gp_id - 1] = s

                for eid, gps in stress_gp_map.items():
                    if None in gps:
                        continue
                    elem = elements[eid - 1]
                    if len(elem) < 9:
                        continue
                    pid = self._el_to_poly.get(eid - 1)
                    if pid in self._state.result_hidden_polygons:
                        continue

                    gp_vals = [self._get_stress_value(g, out_type) for g in gps]
                    node_accum = [0.0] * 9
                    node_w = [0.0] * 9
                    for gp_idx, (xi, eta) in enumerate(GAUSS_POINTS_2D):
                        n_vals = shape_functions_quad9(xi, eta)
                        for ni in range(9):
                            node_accum[ni] += n_vals[ni] * gp_vals[gp_idx]
                            node_w[ni] += n_vals[ni]

                    for ni in range(9):
                        node_idx = elem[ni]
                        val = node_accum[ni] / node_w[ni] if node_w[ni] > 1e-12 else 0.0
                        # Per-polygon key for sharp material boundary discontinuities
                        key = (node_idx, pid)
                        if key not in self._last_nodal_vals: self._last_nodal_vals[key] = [0.0, 0]
                        self._last_nodal_vals[key][0] += val; self._last_nodal_vals[key][1] += 1
                        nodal_raw.append(val)
            elif "displacements" in phase_results:
                for d in phase_results["displacements"]:
                    n_idx = u_get(d, "id") - 1
                    ux, uy = u_get(d, "ux"), u_get(d, "uy")
                    if out_type == OutputType.DEFORMED_CONTOUR: val = math.sqrt(ux*ux + uy*uy)
                    elif out_type == OutputType.DEFORMED_CONTOUR_UX: val = abs(ux)
                    elif out_type == OutputType.DEFORMED_CONTOUR_UY: val = abs(uy)
                    else: val = 0.0
                    # For displacements, average GLOBAL (across all polygons) for C0 continuity
                    key = (n_idx, None)
                    if key not in self._last_nodal_vals: self._last_nodal_vals[key] = [0.0, 0]
                    self._last_nodal_vals[key][0] += val; self._last_nodal_vals[key][1] += 1
                    nodal_raw.append(val)

        # 6. Color range — simple min/max (matching proven T6 approach)
        def get_jet_color(v: float, alpha: int = 255) -> QColor:
            v = max(0.0, min(1.0, v))
            r, g, b = 0, 0, 0
            if v < 0.25: r, g, b = 0, int(v*4*255), 255
            elif v < 0.5: r, g, b = 0, 255, int((0.5-v)*4*255)
            elif v < 0.75: r, g, b = int((v-0.5)*4*255), 255, 0
            else: r, g, b = 255, int((1.0-v)*4*255), 0
        v_min, v_max = 0.0, 1.0
        _invert_cmap = False
        if self._last_nodal_vals:
            avg_vals = [v[0]/v[1] for v in self._last_nodal_vals.values()]
            v_min, v_max = min(avg_vals), max(avg_vals)
            if v_min == v_max: v_max += 1e-9
            
            # Expand by a tiny epsilon so edge floats are fully enclosed without needing extend='both'
            eps = (v_max - v_min) * 1e-5
            if eps == 0.0: eps = 1e-9
            v_min -= eps
            v_max += eps
            # Zero-relative color mapping
            if abs(v_min) > abs(v_max):
                _invert_cmap = True

        # 7. PER-POLYGON CONTOUR GENERATION (Layer 1: Fills at Z=12)
        # Quad9: subdivide each element into 8 sub-triangles (all 9 nodes).
        if is_contour and self._last_nodal_vals:
            import matplotlib.tri as tri
            import matplotlib.cm as cm
            import numpy as np
            # Group elements by Polygon ID for localized contouring
            poly_to_elements = {}
            for idx, elem in enumerate(elements):
                pid = self._el_to_poly.get(idx)
                if pid is None or pid not in active_indices: continue
                if pid in self._state.result_hidden_polygons: continue
                if pid not in poly_to_elements: poly_to_elements[pid] = []
                poly_to_elements[pid].append(idx)

            # Increase contour levels to 30 for smoother color gradients
            num_levels = 30
            cmap = cm.get_cmap('jet')
            
            for pid, elem_indices in poly_to_elements.items():
                try:
                    # Collect nodes for this polygon subset
                    subset_tri_indices = []
                    involved_node_indices = set()
                    for idx in elem_indices:
                        e = elements[idx]
                        for tri_nodes in _quad9_contour_triangles(e):
                            subset_tri_indices.append(tri_nodes)
                        involved_node_indices.update(e[:9] if len(e) >= 9 else e[:4])
                    
                    sub_nodes_idx = sorted(list(involved_node_indices))
                    node_map = {old: new for new, old in enumerate(sub_nodes_idx)}
                    
                    sub_x = [nodes[i][0] for i in sub_nodes_idx]
                    sub_y = [nodes[i][1] for i in sub_nodes_idx]
                    
                    # Compute nodal values using polygon-specific key (sharp material boundaries)
                    sub_v = []
                    for i in sub_nodes_idx:
                        val_raw = self._last_nodal_vals.get((i, pid)) or self._last_nodal_vals.get((i, None), [0.0, 1])
                        sub_v.append(val_raw[0] / val_raw[1])
                    
                    # Apply deformation to local nodes if needed
                    if scale != 0:
                        for i, n_idx in enumerate(sub_nodes_idx):
                            if n_idx in disp_map:
                                dx, dy = disp_map[n_idx]
                                sub_x[i] += dx * scale; sub_y[i] += dy * scale

                    sub_tri = [[node_map[ni] for ni in t] for t in subset_tri_indices]
                    
                    if len(sub_x) < 3 or not sub_tri: continue
                    
                    # Create base triangulation and contour it directly. IDW extrapolation makes this smooth enough.
                    triang = tri.Triangulation(sub_x, sub_y, sub_tri)
                    levels = np.linspace(v_min, v_max, num_levels + 1)
                    
                    cntr = self._get_contourf_data(triang, sub_v, levels)
                    
                    for level_idx in range(len(levels) - 1):
                        t_val = (levels[level_idx] + levels[level_idx+1]) / 2.0
                        v_norm = (t_val - v_min) / (v_max - v_min)
                        if _invert_cmap: v_norm = 1.0 - v_norm
                        
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
            pid = self._el_to_poly.get(idx)
            if pid is not None and pid not in active_indices: continue
            if pid in self._state.result_hidden_polygons: continue
            if len(elem) < 3: continue
            
            # Base coordinates (deformed) — Quad9 perimeter or triangle fallback
            pts = []
            if len(elem) >= 9:
                perimeter = [0, 4, 1, 5, 2, 6, 3, 7]
            else:
                perimeter = list(range(min(3, len(elem))))
            for ni in perimeter:
                n_idx = elem[ni]
                x, y = nodes[n_idx][0], nodes[n_idx][1]
                if n_idx in disp_map:
                    dx, dy = disp_map[n_idx]
                    x += dx * scale
                    y += dy * scale
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
                from engine.solver.element_quad9 import (
                    NUM_GAUSS_POINTS,
                    gauss_point_physical_coords,
                )
                eid = idx + 1
                gp_yield_flags = [False] * NUM_GAUSS_POINTS
                if phase_results and "stresses" in phase_results:
                    for s in phase_results["stresses"]:
                        if u_get(s, "element_id") == eid:
                            gp_id = u_get(s, "gp_id", 1)
                            if 1 <= gp_id <= NUM_GAUSS_POINTS:
                                gp_yield_flags[gp_id - 1] = u_get(s, "is_yielded", False)

                if len(elem) < 9:
                    continue
                for gp_idx in range(NUM_GAUSS_POINTS):
                    gx, gy = gauss_point_physical_coords(nodes, elem, gp_idx)
                    
                    gp_fill = QBrush(QColor("#ef4444")) if gp_yield_flags[gp_idx] else QBrush(QColor("#10b981"))
                    
                    gp_item = self._scene.addEllipse(gx-0.025, gy-0.025, 0.05, 0.05, QPen(Qt.NoPen), gp_fill)
                    gp_item.setZValue(25)
                    gp_item.setData(10, "gp_status")
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
        bm_lookup = {m.get("id"): m for m in self._state.beam_materials}
        active_beam_ids = set(current_phase.get("active_beam_ids", [])) if current_phase else set()
        active_beam_ids.difference_update(self._state.result_hidden_beams)
            
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
        self._update_legend(v_min, v_max, out_type, invert=_invert_cmap)

    def _update_legend(self, v_min, v_max, out_type, invert=False):
        """Show/Hide and update the dynamic results legend."""
        if not hasattr(self, "_legend_panel"):
            self._legend_panel = self._create_legend_panel()

        is_contour = out_type not in [OutputType.DEFORMED_MESH, OutputType.YIELD_STATUS]
        self._legend_panel.setVisible(is_contour)
        
        if is_contour:
            # Determine physical unit
            unit = ""
            if "contour" in str(out_type):
                unit = " m"
            elif "sigma" in str(out_type) or "pwp" in str(out_type):
                unit = " kN/m\u00b2"
            
            # Update gradient bar direction to match contour colormap
            if invert:
                # Inverted: Red (left/min) -> Blue (right/max)
                self._legend_bar.setStyleSheet("""
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                        stop:0 #7f0000, stop:0.25 #ffff00, stop:0.5 #00ff00, stop:0.75 #00ffff, stop:1 #00007f);
                    border: 1px solid #94a3b8;
                """)
            else:
                # Normal: Blue (left/min) -> Red (right/max)
                self._legend_bar.setStyleSheet("""
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                        stop:0 #00007f, stop:0.25 #00ffff, stop:0.5 #00ff00, stop:0.75 #ffff00, stop:1 #7f0000);
                    border: 1px solid #94a3b8;
                """)
            
            self._lbl_min.setText(f"{v_min:.3f}{unit}")
            self._lbl_max.setText(f"{v_max:.3f}{unit}")
            self._lbl_title.setText(str(out_type).replace("OutputType.", "").replace("_", " ").upper())

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
        
        # Color bar (stored as instance var so we can update its gradient)
        self._legend_bar = QFrame()
        self._legend_bar.setFixedHeight(12)
        self._legend_bar.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                stop:0 #00007f, stop:0.25 #00ffff, stop:0.5 #00ff00, stop:0.75 #ffff00, stop:1 #7f0000);
            border: 1px solid #94a3b8;
        """)
        layout.addWidget(self._legend_bar)
        
        # Labels
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

        def pt_in_tri(p, p0, p1, p2):
            s = (p0[0] - p2[0]) * (p[1] - p2[1]) - (p0[1] - p2[1]) * (p[0] - p2[0])
            t = (p1[0] - p0[0]) * (p[1] - p0[1]) - (p1[1] - p0[1]) * (p[0] - p0[0])
            if (s < 0) != (t < 0) and s != 0 and t != 0:
                return False
            d = (p2[0] - p1[0]) * (p[1] - p2[1]) - (p2[1] - p1[1]) * (p[0] - p2[0])
            return (d < 0) == (s < 0) or d == 0

        def get_barycentric(p, p1, p2, p3):
            denom = (p2[1] - p3[1]) * (p1[0] - p3[0]) + (p3[0] - p2[0]) * (p1[1] - p3[1])
            if abs(denom) < 1e-12:
                return 1 / 3, 1 / 3, 1 / 3
            w1 = ((p2[1] - p3[1]) * (p[0] - p3[0]) + (p3[0] - p2[0]) * (p[1] - p3[1])) / denom
            w2 = ((p3[1] - p1[1]) * (p[0] - p3[0]) + (p1[0] - p3[0]) * (p[1] - p3[1])) / denom
            w3 = 1.0 - w1 - w2
            return w1, w2, w3

        px, py = scene_pos.x(), scene_pos.y()
        for elem_idx, elem in enumerate(elements):
            if len(elem) < 3:
                continue
            for t0, t1, t2 in _quad9_contour_triangles(elem):
                v1, v2, v3 = nodes[t0], nodes[t1], nodes[t2]
                min_x = min(v1[0], v2[0], v3[0])
                max_x = max(v1[0], v2[0], v3[0])
                min_y = min(v1[1], v2[1], v3[1])
                max_y = max(v1[1], v2[1], v3[1])
                if not (min_x <= px <= max_x and min_y <= py <= max_y):
                    continue
                if not pt_in_tri((px, py), v1, v2, v3):
                    continue

                pid = self._el_to_poly.get(elem_idx)

                def _get_v_poly(ni, p):
                    r = self._last_nodal_vals.get((ni, p)) or self._last_nodal_vals.get((ni, None))
                    return r[0] / r[1] if r else 0.0

                w1, w2, w3 = get_barycentric((px, py), v1, v2, v3)
                found_val = (
                    w1 * _get_v_poly(t0, pid)
                    + w2 * _get_v_poly(t1, pid)
                    + w3 * _get_v_poly(t2, pid)
                )
                break
            if found_val is not None:
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

    def _render_bc_markers(self):
        """Draw minimalist boundary condition symbols on affected nodes."""
        for item in self._bc_items: self._scene.removeItem(item)
        self._bc_items.clear()
        
        if not self._state.show_bc_markers or not self._mesh_data:
            return

        nodes = self._mesh_data.get("nodes", [])
        if not nodes: return
        
        # Calculate boundaries (same logic as solver)
        xs = [n[0] for n in nodes]
        ys = [n[1] for n in nodes]
        x_min, x_max = min(xs), max(xs)
        y_min, y_max = min(ys), max(ys)
        
        settings = self._state.settings
        bc_map = {
            "x_min": settings.get("bc_x_min", "roller_x").lower(),
            "x_max": settings.get("bc_x_max", "roller_x").lower(),
            "y_min": settings.get("bc_y_min", "fixed").lower(),
            "y_max": settings.get("bc_y_max", "free").lower(),
        }
        
        TOL = 1e-4
        SIZE = 0.05 # Standard marker size

        def add_marker(x, y, bc_type, side):
            if bc_type == "free": return
            
            marker_items = []
            
            pen = QPen(QColor("#111827"), 1.2)
            pen.setCosmetic(True)
            brush = QBrush(QColor("#111827")) # Solid black/dark
            opaque_brush = QBrush(QColor(17, 24, 39, 40)) # Light transparent for rollers
            
            if bc_type == "fixed":
                # Pin symbol: A filled triangle
                qpoly = QPolygonF([QPointF(0, 0), QPointF(-SIZE/2, SIZE), QPointF(SIZE/2, SIZE)])
                # Rotate based on side
                rotation = 0
                if side == "x_min": rotation = 90
                elif side == "x_max": rotation = -90
                elif side == "y_max": rotation = 0
                elif side == "y_min": rotation = 180
                
                t = QTransform().rotate(rotation)
                qpoly = t.map(qpoly)
                
                item = self._scene.addPolygon(qpoly, pen, brush)
                marker_items.append(item)
                
            elif bc_type == "roller_x" or bc_type == "roller_y":
                # Roller symbol: Triangle with a line underneath
                # If roller_x, it can't move X, so it rolls on a vertical wall? 
                # Wait, "roller_x" usually means fixed in X, free in Y. So it rolls along the Y axis.
                # Marker: triangle + small circles
                is_vert = (bc_type == "roller_x") # Rollins along Y
                
                qtri = QPolygonF([QPointF(0, 0), QPointF(-SIZE/2, SIZE), QPointF(SIZE/2, SIZE)])
                
                rotation = 0
                if side == "x_min": rotation = 90
                elif side == "x_max": rotation = -90
                elif side == "y_max": rotation = 0
                elif side == "y_min": rotation = 180
                
                t = QTransform().rotate(rotation)
                qtri = t.map(qtri)
                
                # Add triangle
                item_tri = self._scene.addPolygon(qtri, pen, QBrush(Qt.NoBrush))
                marker_items.append(item_tri)
                
                # Add two small rollers (circles)
                r_size = SIZE/4
                if side == "y_max":
                    c1 = self._scene.addEllipse(-SIZE/2, SIZE, r_size, r_size, pen, brush)
                    c2 = self._scene.addEllipse(SIZE/2 - r_size, SIZE, r_size, r_size, pen, brush)
                    marker_items.append(c1); marker_items.append(c2)
                elif side == "x_max":
                    c1 = self._scene.addEllipse(SIZE, -SIZE/2, r_size, r_size, pen, brush)
                    c2 = self._scene.addEllipse(SIZE, SIZE/2 - r_size, r_size, r_size, pen, brush)
                    marker_items.append(c1); marker_items.append(c2)
                elif side == "x_min":
                    c1 = self._scene.addEllipse(-SIZE-r_size, -SIZE/2, r_size, r_size, pen, brush)
                    c2 = self._scene.addEllipse(-SIZE-r_size, SIZE/2 - r_size, r_size, r_size, pen, brush)
                    marker_items.append(c1); marker_items.append(c2)
                elif side == "y_min":
                    c1 = self._scene.addEllipse(-SIZE/2, -SIZE-r_size, r_size, r_size, pen, brush)
                    c2 = self._scene.addEllipse(SIZE/2 - r_size, -SIZE-r_size, r_size, r_size, pen, brush)
                    marker_items.append(c1); marker_items.append(c2)
                else:
                    c1 = self._scene.addEllipse(SIZE, -SIZE/2, r_size, r_size, pen, brush)
                    c2 = self._scene.addEllipse(SIZE, SIZE/2 - r_size, r_size, r_size, pen, brush)
                    marker_items.append(c1); marker_items.append(c2)

            if marker_items:
                group = self._scene.createItemGroup(marker_items)
                group.setPos(x, y)
                group.setZValue(30) # Above mesh & loads
                self._bc_items.append(group)

        # To avoid overcrowding, we only draw markers at a subset of boundary nodes if the mesh is dense
        # But for professional FEA, seeing all boundary nodes is often preferred. 
        # We'll skip every other mid-node for T15 if needed, but let's draw all first.
        for i, (x, y) in enumerate(nodes):
            if abs(y - y_min) < TOL: add_marker(x, y, bc_map["y_min"], "y_min")
            if abs(y - y_max) < TOL: add_marker(x, y, bc_map["y_max"], "y_max")
            if abs(x - x_min) < TOL: add_marker(x, y, bc_map["x_min"], "x_min")
            if abs(x - x_max) < TOL: add_marker(x, y, bc_map["x_max"], "x_max")

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

    def _render_loads(self):
        """Render Point Loads and Line Loads if they are active in the current phase and not hidden."""
        for item in self._load_items:
            self._scene.removeItem(item)
        self._load_items.clear()

        current_phase = self._state.current_phase
        if not current_phase:
            return

        active_ids = current_phase.get("active_load_ids", [])
        hidden_ids = getattr(self._state, "result_hidden_loads", set())
        
        import math
        
        # 1. Point Loads
        pen_pl = QColor('#ef4444')
        for l in self._state.point_loads:
            lid = l.get("id")
            if lid not in active_ids or lid in hidden_ids:
                continue
            
            px, py = l["x"], l["y"]
            fx, fy = l.get("fx", 0), -l.get("fy", 0) # FY mapping logic typically assumes vertical axis
            mag = math.sqrt(fx*fx + fy*fy)
            if mag < 1e-5: continue
            
            ux, uy = fx/mag, -fy/mag
            arrow_len = 1.0
            tx, ty = px - ux * arrow_len, py - uy * arrow_len
            
            pen = QPen(pen_pl, 0)
            pen.setCosmetic(True)
            line = self._scene.addLine(tx, ty, px, py, pen)
            line.setZValue(150)
            line.setData(Qt.UserRole + 1, "point_load")
            
            perp_x, perp_y = -uy, ux
            hw, hl = 0.2, 0.3
            head_pts = [
                QPointF(px, py),
                QPointF(px - ux*hl + perp_x*hw, py - uy*hl + perp_y*hw),
                QPointF(px - ux*hl - perp_x*hw, py - uy*hl - perp_y*hw)
            ]
            head_item = self._scene.addPolygon(QPolygonF(head_pts), pen, QBrush(pen_pl))
            head_item.setZValue(150)
            head_item.setData(Qt.UserRole + 1, "point_load")
            self._load_items.extend([line, head_item])

        # 2. Line Loads
        pen_ll = QColor('#f97316')
        for l in self._state.line_loads:
            lid = l.get("id")
            if lid not in active_ids or lid in hidden_ids:
                continue
            
            x1, y1 = l["x1"], l["y1"]
            x2, y2 = l["x2"], l["y2"]
            fx, fy = l.get("fx", 0), -l.get("fy", 0)
            mag = math.sqrt(fx*fx + fy*fy)
            
            pen = QPen(pen_ll, 0)
            pen.setCosmetic(True)
            
            main_line = self._scene.addLine(x1, y1, x2, y2, pen)
            main_line.setZValue(140)
            main_line.setData(Qt.UserRole + 1, "line_load")
            self._load_items.append(main_line)
            
            if mag < 1e-5: continue
            
            ux, uy = fx/mag, -fy/mag
            num_ticks = 4
            arrow_len, hw, hl = 0.6, 0.1, 0.15
            perp_x, perp_y = -uy, ux
            
            for i in range(num_ticks + 1):
                f = i / num_ticks
                px = x1 + f * (x2 - x1)
                py = y1 + f * (y2 - y1)
                tx, ty = px - ux * arrow_len, py - uy * arrow_len
                
                tick = self._scene.addLine(tx, ty, px, py, pen)
                tick.setZValue(140)
                tick.setData(Qt.UserRole + 1, "line_load")
                
                head_pts = [
                    QPointF(px, py),
                    QPointF(px - ux*hl + perp_x*hw, py - uy*hl + perp_y*hw),
                    QPointF(px - ux*hl - perp_x*hw, py - uy*hl - perp_y*hw)
                ]
                head_item = self._scene.addPolygon(QPolygonF(head_pts), pen, QBrush(pen_ll))
                head_item.setZValue(140)
                head_item.setData(Qt.UserRole + 1, "line_load")
                self._load_items.extend([tick, head_item])
