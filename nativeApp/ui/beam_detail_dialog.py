# ui/beam_detail_dialog.py
# ===========================================================================
# BeamDetailDialog — Structural visualization for Embedded Beam Rows (EBR)
# ===========================================================================

import math
import numpy as np
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFrame, QRadioButton, QButtonGroup,
    QGraphicsView, QGraphicsScene, QGraphicsPathItem, QWidget,
    QTableWidget, QTableWidgetItem, QHeaderView
)
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QColor, QPen, QBrush, QPainter, QPainterPath

from core.state import ProjectState

class BeamDetailDialog(QDialog):
    """
    Detailed output window for a specific Embedded Beam Row.
    Displays FBD and internal force diagrams (Axial, Shear, Moment).
    """
    def __init__(self, beam_id, parent=None):
        super().__init__(parent)
        self._beam_id = beam_id
        self._state = ProjectState.instance()
        
        self.setWindowTitle(f"Beam Detail: {self._beam_id}")
        self.setMinimumSize(1100, 650)
        self.setAttribute(Qt.WA_DeleteOnClose)
        
        self.setStyleSheet("""
            QDialog { background-color: #ffffff; }
            .Sidebar { 
                background-color: #f8fafc; 
                border-right: 1px solid #e2e8f0; 
                min-width: 220px; 
            }
            QLabel#Title { 
                font-weight: bold; 
                font-size: 14px; 
                color: #1e293b; 
                margin-bottom: 4px;
                 background-color: transparent;
            }
            QLabel#SubTitle { 
                font-size: 11px; 
                color: #64748b; 
                margin-bottom: 12px;
                 background-color: transparent;
            }
            
            QLabel { 
                font-size: 12px; 
                color: #334155; 
                margin-bottom: 12px;
                 background-color: transparent;
            }
            QRadioButton { 
                font-size: 12px; 
                color: #334155; 
                padding: 4px;
                 background-color: transparent;
            }
            QPushButton#CloseButton {
                background-color: #f1f5f9;
                border: 1px solid #cbd5e1;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 12px;
                font-weight: 600;
                color: #475569;
            }
            QPushButton#CloseButton:hover { background-color: #e2e8f0; }
            QTableWidget {
                border: 1px solid #e2e8f0;
                border-radius: 4px;
                gridline-color: #f1f5f9;
                font-size: 11px;
            }
            QHeaderView::section {
                background-color: #f8fafc;
                padding: 4px;
                border: none;
                border-bottom: 1px solid #e2e8f0;
                font-weight: bold;
                color: #475569;
            }
        """)

        self._init_ui()
        self._update_data()
        self._render_diagram()

    def _init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Left Sidebar
        sidebar = QFrame()
        sidebar.setProperty("class", "Sidebar")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(16, 20, 16, 20)
        sidebar_layout.setSpacing(8)

        self.lbl_title = QLabel(f"EBR: {self._beam_id}")
        self.lbl_title.setObjectName("Title")
        sidebar_layout.addWidget(self.lbl_title)

        self._beam_obj = next((b for b in self._state.embedded_beams if b["id"] == self._beam_id), None)
        mat_name = "N/A"
        self._beam_color = QColor("#555") # Default
        if self._beam_obj:
            mid = self._beam_obj.get("materialId")
            mat = next((m for m in self._state.beam_materials if m["id"] == mid), None)
            if mat: 
                mat_name = mat.get("name", "Unknown")
                self._beam_color = QColor(mat.get("color", "#2563eb"))
        
        self.lbl_subtitle = QLabel(f"Material: {mat_name}")
        self.lbl_subtitle.setObjectName("SubTitle")
        sidebar_layout.addWidget(self.lbl_subtitle)

        sidebar_layout.addWidget(QLabel("Result Type"))
        
        self._group = QButtonGroup(self)
        self.radio_axial = QRadioButton("Axial Force (N)")
        self.radio_shear = QRadioButton("Shear Force (V)")
        self.radio_moment = QRadioButton("Bending Moment (M)")
        self.radio_disp_xg = QRadioButton("X-Global")
        self.radio_disp_yg = QRadioButton("Y-Global")
        self.radio_disp_total = QRadioButton("Total Displacement")

        self.radio_moment.setChecked(True)
        
        types = [
            (self.radio_axial, "N"), (self.radio_shear, "V"), (self.radio_moment, "M"),
            (self.radio_disp_xg, "UXG"), (self.radio_disp_yg, "UYG"), (self.radio_disp_total, "UT")
        ]
        for rb, val in types:
            self._group.addButton(rb)
            sidebar_layout.addWidget(rb)
        
        self._group.buttonClicked.connect(self._render_diagram)
        sidebar_layout.addStretch()

        btn_close = QPushButton("Close")
        btn_close.setObjectName("CloseButton")
        btn_close.clicked.connect(self.accept)
        sidebar_layout.addWidget(btn_close)

        main_layout.addWidget(sidebar)

        # 2. Content Area (Canvas + Table)
        content_area = QWidget()
        content_layout = QHBoxLayout(content_area)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(16)

        # 2a. Left Column (Canvas + Summary)
        canvas_column = QWidget()
        canvas_col_layout = QVBoxLayout(canvas_column)
        canvas_col_layout.setContentsMargins(0, 0, 0, 0)
        canvas_col_layout.setSpacing(12)

        self.view = QGraphicsView()
        self.view.setRenderHint(QPainter.Antialiasing)
        self.view.setStyleSheet("border: 1px solid #e2e8f0; border-radius: 8px; background: white;")
        self.scene = QGraphicsScene()
        self.view.setScene(self.scene)
        canvas_col_layout.addWidget(self.view)

        # Summary Bar Below Canvas
        self.summary_bar = QFrame()
        self.summary_bar.setStyleSheet("""
            QFrame { 
                background-color: #f8fafc; 
                border: 1px solid #e2e8f0; 
                border-radius: 6px; 
            }
            QLabel { color: #475569; font-size: 11px; background-color: transparent; }
            QLabel#Val { font-weight: 600; color: #1e293b; font-size: 12px; background-color: transparent; }
        """)
        summary_layout = QHBoxLayout(self.summary_bar)
        summary_layout.setContentsMargins(12, 8, 12, 8)
        
        summary_layout.addWidget(QLabel("Min:"))
        self.lbl_min_val = QLabel("0.00")
        self.lbl_min_val.setObjectName("Val")
        summary_layout.addWidget(self.lbl_min_val)
        
        summary_layout.addSpacing(20)
        
        summary_layout.addWidget(QLabel("Max:"))
        self.lbl_max_val = QLabel("0.00")
        self.lbl_max_val.setObjectName("Val")
        summary_layout.addWidget(self.lbl_max_val)
        
        summary_layout.addStretch()
        canvas_col_layout.addWidget(self.summary_bar)

        content_layout.addWidget(canvas_column, 3)

        # 2b. Data Table
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["X (m)", "Y (m)", "Value"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setFixedWidth(280)
        content_layout.addWidget(self.table, 1)

        main_layout.addWidget(content_area)

    def _update_data(self):
        """Extract beam geometry and results for the current phase."""
        self._beam_data = [] # List of segments: {coords, results}
        
        curr_ph = self._state.current_phase
        if not curr_ph: return
        
        res = self._state.get_phase_results(curr_ph["id"])
        if not res or 'beam_results' not in res: return
        
        # Get all segments for this beam
        all_br = res.get('beam_results', [])
        beam_results = []
        for r in all_br:
            # Handle both objects (Active) and dicts (Loaded)
            bid = r.beam_id if hasattr(r, 'beam_id') else r.get('beam_id')
            if bid == self._beam_id:
                beam_results.append(r)
        
        def get_seg_idx(r):
            return r.segment_index if hasattr(r, 'segment_index') else r.get('segment_index', 0)
            
        beam_results.sort(key=get_seg_idx)
        
        eb_assigns = self._state.mesh_response.get('embedded_beam_assignments', [])
        assign = next((a for a in eb_assigns if a.get('beam_id') == self._beam_id), None)
        if not assign: return
        
        nodes = self._state.mesh_response.get('nodes', [])
        beam_nodes = [nid - 1 for nid in assign.get('nodes', [])]
        
        raw_disps = res.get('displacements', [])
        disp_map = {}
        for dr in raw_disps:
            did = dr.id if hasattr(dr, 'id') else dr.get('id')
            if did is not None:
                disp_map[did - 1] = dr
        
        for br in beam_results:
            idx = get_seg_idx(br)
            if idx + 1 >= len(beam_nodes): continue
            n1, n2 = beam_nodes[idx], beam_nodes[idx+1]
            self._beam_data.append({
                'segment': br,
                'p1': nodes[n1], 'p2': nodes[n2],
                'd1': disp_map.get(n1), 'd2': disp_map.get(n2)
            })

    def _render_diagram(self):
        self.scene.clear()
        if not self._beam_data:
            self.scene.addText("No result data available for this phase.")
            self.table.setRowCount(0)
            return

        # 1. Geometry and Orientation
        p_first = self._beam_data[0]['p1']
        p_last = self._beam_data[-1]['p2']
        beam_vec_x = p_last[0] - p_first[0]
        beam_vec_y = p_last[1] - p_first[1]
        total_L = math.sqrt(beam_vec_x**2 + beam_vec_y**2)
        if total_L < 1e-6: return

        ux, uy = beam_vec_x / total_L, beam_vec_y / total_L
        nx, ny = -uy, ux 
        
        btn = self._group.checkedButton()
        mode = "M"
        if btn == self.radio_axial: mode = "N"
        elif btn == self.radio_shear: mode = "V"
        elif btn == self.radio_disp_xg: mode = "UXG"
        elif btn == self.radio_disp_yg: mode = "UYG"
        elif btn == self.radio_disp_total: mode = "UT"

        max_val = 1e-9
        plot_points = [] 
        table_data = [] # List of (x, y, v)

        curr_dist = 0
        for item in self._beam_data:
            br = item['segment']
            p1, p2 = item['p1'], item['p2']
            L = math.sqrt((p2[0]-p1[0])**2 + (p2[1]-p1[1])**2)
            dx, dy = p2[0]-p1[0], p2[1]-p1[1]
            seg_L = math.sqrt(dx**2 + dy**2)
            c_seg, s_seg = dx/seg_L, dy/seg_L

            def get_attr(obj, key, default=0.0):
                if not obj: return default
                if isinstance(obj, dict):
                    return obj.get(key, default)
                return getattr(obj, key, default)

            def get_val(is_node2=False):
                if mode == "N": return get_attr(br, 'n')
                elif mode == "V": return get_attr(br, 'v2' if is_node2 else 'v1')
                elif mode == "M": return get_attr(br, 'm2' if is_node2 else 'm1')
                elif mode == "UXG": return get_attr(br, 'urx2' if is_node2 else 'urx1')
                elif mode == "UYG": return get_attr(br, 'ury2' if is_node2 else 'ury1')
                elif mode == "UT": return get_attr(br, 'ut2' if is_node2 else 'ut1', 
                                                  math.sqrt(get_attr(br, 'ux2' if is_node2 else 'ux1')**2 + 
                                                           get_attr(br, 'uy2' if is_node2 else 'uy1')**2))
                return 0.0

            v1, v2 = get_val(False), get_val(True)
            ux1, uy1 = get_attr(br, 'ux1'), get_attr(br, 'uy1')
            ux2, uy2 = get_attr(br, 'ux2'), get_attr(br, 'uy2')
            
            plot_points.append((curr_dist, v1, ux1, uy1))
            plot_points.append((curr_dist + L, v2, ux2, uy2))
            
            # Table Data (deduplicate points at junctions)
            if not table_data:
                table_data.append((p1[0], p1[1], v1))
            table_data.append((p2[0], p2[1], v2))

            max_val = max(max_val, abs(v1), abs(v2))
            curr_dist += L

        # Update Table
        self.table.setRowCount(len(table_data))
        for i, (tx, ty, tv) in enumerate(table_data):
            self.table.setItem(i, 0, QTableWidgetItem(f"{tx:.3f}"))
            self.table.setItem(i, 1, QTableWidgetItem(f"{ty:.3f}"))
            self.table.setItem(i, 2, QTableWidgetItem(f"{tv:.4f}"))

        # 3. Scaling and Centering
        view_w = self.view.width() - 150
        view_h = self.view.height() - 150
        if view_w < 100: view_w = 700
        if view_h < 100: view_h = 400
        scale_geo = min(view_w, view_h) / total_L if total_L > 0 else 1.0
        scale_res = (min(view_w, view_h) * 0.3) / max_val if max_val > 1e-9 else 1.0

        # Update Labels
        all_vals = [pt[1] for pt in plot_points]
        v_min_actual = min(all_vals)
        v_max_actual = max(all_vals)
        unit = "kN"
        if mode == "M": unit = "kN·m"
        elif mode in ["UXG", "UYG", "UT"]: unit = "m"
        self.lbl_min_val.setText(f"{v_min_actual:.4f} {unit}")
        self.lbl_max_val.setText(f"{v_max_actual:.4f} {unit}")

        color_fill = QColor("#3b82f6")
        if mode == "M": color_fill = QColor("#8b5cf6")
        elif mode == "V": color_fill = QColor("#ec4899")
        elif mode == "N": color_fill = QColor("#10b981")
        color_fill.setAlpha(40)
        pen_diag = QPen(color_fill.darker(150), 1.5)
        brush_diag = QBrush(color_fill)
        pen_beam = QPen(QColor("#94a3b8"), 3)
        
        start_pt = QPointF(0, 0)
        end_pt = QPointF(beam_vec_x * scale_geo, -beam_vec_y * scale_geo)
        self.scene.addLine(start_pt.x(), start_pt.y(), end_pt.x(), end_pt.y(), pen_beam)
        
        poly_points = [start_pt]
        sux, suy = ux, -uy
        snx, sny = nx, -ny

        for d, v, dv_ux, dv_uy in plot_points:
            bx = d * sux * scale_geo
            by = d * suy * scale_geo
            
            # Global or Local Diagram Orientation
            if mode == "UXG":
                px = bx + (v * scale_res)
                py = by
            elif mode == "UYG":
                px = bx
                py = by - (v * scale_res)
            elif mode == "UT":
                px = bx + (dv_ux * scale_res)
                py = by - (dv_uy * scale_res)
            else:
                px = bx + (v * scale_res) * snx
                py = by + (v * scale_res) * sny
            
            poly_points.append(QPointF(px, py))
        
        poly_points.append(end_pt)
        self.scene.addPolygon(poly_points, pen_diag, brush_diag)

        # Labels for Orientation ONLY (Numeric data is in table/summary now)
        font = self.lbl_subtitle.font()
        font.setPointSize(10)
        font.setBold(True)
        
        # Labels and Symbols for Orientation
        font = self.lbl_subtitle.font()
        font.setPointSize(10)
        font.setBold(True)
        
        marker_color = self._beam_color
        head_pen = QPen(marker_color, 1.5)
        head_brush = QBrush(marker_color)
        
        # 4. Draw Connection Marker at Head (Start Point)
        head_conn = "FIXED"
        if self._beam_obj:
            head_conn = str(self._beam_obj.get('head_connection_type', 'FIXED')).upper()
        
        marker_size = 10
        if head_conn in ["FIXED", "FIX"]:
            # Red Square for Fixed
            self.scene.addRect(-marker_size/2, -marker_size/2, marker_size, marker_size, head_pen, head_brush)
        else:
            # Red Triangle for Pinned (points along the beam towards the Tip)
            angle_rad = math.atan2(-beam_vec_y, beam_vec_x)
            
            # Vertices: Apex at (0,0), base at +marker_size (pointing into beam along X)
            # Then rotated by beam angle
            p_tri = [QPointF(0, 0), QPointF(marker_size, -marker_size/2), QPointF(marker_size, marker_size/2)]
            from PySide6.QtGui import QPolygonF
            q_poly = QPolygonF(p_tri)
            
            from PySide6.QtGui import QTransform
            trans = QTransform().rotateRadians(angle_rad)
            rotated_poly = trans.map(q_poly)
            self.scene.addPolygon(rotated_poly, head_pen, head_brush)

        lbl_head = self.scene.addText("HEAD", font)
        lbl_head.setDefaultTextColor(marker_color)
        lbl_head.setPos(-20, -35)
        
        lbl_tip = self.scene.addText("TIP", font)
        lbl_tip.setDefaultTextColor(QColor("#64748b"))
        lbl_tip.setPos(end_pt.x() - 10, end_pt.y() + 10)
        
        self.view.centerOn(self.scene.itemsBoundingRect().center())
