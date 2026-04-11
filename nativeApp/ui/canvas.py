# ui/canvas.py
# ===========================================================================
# TerraSimCanvas — QGraphicsView + QGraphicsScene for 2D Geotechnical Modeling
# ===========================================================================
# Replaces the React <InputCanvas> / Three.js canvas with native Qt Graphics
# View Framework.
#
# Features implemented:
#   1. Zoom (mouse wheel)
#   2. Pan  (middle-mouse drag)
#   3. Tool-mode-aware mouse handling (reads from ProjectState)
#   4. DRAW_POLYGON mode: click to add temp vertices, visual feedback with
#      QGraphicsEllipseItem markers and QGraphicsLineItem connectors
#   5. Right-click or double-click to finalize a polygon
#   6. Grid background for spatial reference
#
# Architecture notes:
#   - The scene uses a standard Y-up coordinate system (Qt Y is inverted,
#     so we apply a negative Y scale on the view).
#   - All tool-mode logic reads from ProjectState.instance().tool_mode.
#   - Drawing results are committed back to ProjectState, which emits
#     signals that other widgets (sidebar, property panel) can listen to.
# ===========================================================================

from __future__ import annotations
import time
from PySide6.QtWidgets import (
    QGraphicsView, QGraphicsScene, QGraphicsEllipseItem,
    QGraphicsLineItem, QGraphicsPolygonItem, QGraphicsPathItem, QGraphicsItem, QGraphicsRectItem
)
from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import (
    QPen, QBrush, QColor, QPolygonF, QPainter, QPainterPath,
    QWheelEvent, QMouseEvent, QDragEnterEvent, QDragMoveEvent, QDropEvent, QFont, QTransform
)

from core.state import ProjectState


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
GRID_SPACING = 1.0          # Scene-unit spacing between grid lines
GRID_EXTENT  = 200.0        # Half-width/height of the drawable grid area
POINT_RADIUS = 0.15         # Radius of vertex marker ellipses (scene units)
ZOOM_FACTOR  = 1.15         # Per-wheel-step zoom multiplier

# Colors for Modern Light Theme
COLOR_GRID_MAJOR   = QColor(212, 212, 216, 255)   # zinc-300
COLOR_GRID_MINOR   = QColor(228, 228, 231, 200)   # zinc-200
COLOR_DRAW_VERTEX  = QColor("#10b981")       # emerald-500
COLOR_DRAW_LINE    = QColor("#34d399")       # emerald-400
COLOR_POLYGON_FILL = QColor(128, 128, 128, 30) # emerald-fill translucent
COLOR_AXIS_X       = QColor("#f87171")       # red-400
COLOR_AXIS_Y       = QColor("#60a5fa")       # blue-400
COLOR_MESH_EDGE    = QColor(148, 163, 184, 150)  # slate-400



class TerraSimScene(QGraphicsScene):
    """
    The QGraphicsScene that holds all drawable items.

    Responsibilities:
      - Draws background grid + origin axes
      - Owns all QGraphicsItems (polygon fills, vertex markers, loads, etc.)
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        # Set a generous scene rect (can be expanded later)
        self.setSceneRect(
            -GRID_EXTENT, -GRID_EXTENT,
            GRID_EXTENT * 2, GRID_EXTENT * 2
        )

    # ------------------------------------------------------------------
    # Background grid painting (drawn every repaint, not as items)
    # ------------------------------------------------------------------
    def drawBackground(self, painter: QPainter, rect: QRectF):
        """Draw a faint engineering grid and origin axes behind all items."""
        super().drawBackground(painter, rect)
        painter.fillRect(rect, QColor("#fafafa"))

        state = ProjectState.instance()
        # Hide grid in MESH tab as requested, or if setting is Off
        draw_grid = (state.active_tab != "MESH" and state.active_tab != "STAGING") and state.settings.get("show_grid", True)
        grid_spacing = state.settings.get("grid_spacing", 1.0)
        
        if grid_spacing <= 0:
            grid_spacing = 1.0

        # Determine visible range snapped to grid
        left   = int(rect.left()   // grid_spacing) * grid_spacing
        right  = int(rect.right()  // grid_spacing + 1) * grid_spacing
        top    = int(rect.top()    // grid_spacing) * grid_spacing
        bottom = int(rect.bottom() // grid_spacing + 1) * grid_spacing

        # Safety: avoid drawing grid if it's too dense (e.g. at extreme zoom out)
        # This prevents the application from hanging.
        pixel_spacing = grid_spacing * painter.transform().m11()
        if pixel_spacing < 4:
            draw_grid = False

        if draw_grid:
            # Minor grid lines (every 1 unit)
            pen_minor = QPen(COLOR_GRID_MINOR, 0)  # cosmetic pen (1px)
            painter.setPen(pen_minor)
            x = left
            while x <= right:
                if abs(x) > 1e-5: # omit 0
                    painter.drawLine(QPointF(x, top), QPointF(x, bottom))
                old_x = x
                x += grid_spacing
                if x <= old_x: break # Prevent infinite loops
            y = top
            while y <= bottom:
                if abs(y) > 1e-5:
                    painter.drawLine(QPointF(left, y), QPointF(right, y))
                old_y = y
                y += grid_spacing
                if y <= old_y: break

            # Major grid lines (every 5 units)
            pen_major = QPen(COLOR_GRID_MAJOR, 0)
            painter.setPen(pen_major)
            major = grid_spacing * 5
            x = int(left // major) * major
            while x <= right:
                if abs(x) > 1e-5:
                    painter.drawLine(QPointF(x, top), QPointF(x, bottom))
                x += major
            y = int(top // major) * major
            while y <= bottom:
                if abs(y) > 1e-5:
                    painter.drawLine(QPointF(left, y), QPointF(right, y))
                y += major

        # Origin axes (thicker)
        pen_x = QPen(COLOR_AXIS_X, 0)
        pen_y = QPen(COLOR_AXIS_Y, 0)

        # X-axis (horizontal, red)
        painter.setPen(pen_x)
        painter.drawLine(QPointF(left, 0), QPointF(right, 0))

        # Y-axis (vertical, blue)
        painter.setPen(pen_y)
        painter.drawLine(QPointF(0, top), QPointF(0, bottom))


class TerraSimCanvas(QGraphicsView):
    """
    Main interactive canvas for the geotechnical modeler.

    Handles:
      - Zoom via mouse wheel
      - Pan via middle-mouse drag
      - Tool-mode dispatch (SELECT, DRAW_POLYGON, ADD_POINT_LOAD, etc.)
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        # Create and attach the scene
        self._scene = TerraSimScene(self)
        self.setScene(self._scene)

        # ---- View configuration ----
        self.setRenderHint(QPainter.Antialiasing, True)
        self.setDragMode(QGraphicsView.NoDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorViewCenter)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        self.setMouseTracking(True)

        # Flip Y so scene coordinates are Y-up (engineering convention)
        self.scale(1, -1)
        # Apply a default zoom so 1 scene-unit ≈ 30px
        self.scale(30, 30)

        # Trigger repaint when settings change (grid/rulers)
        ProjectState.instance().settings_changed.connect(lambda s: self.viewport().update())

        # ---- Pan state ----
        self._is_panning = False
        self._pan_start = QPointF()
        self._current_mouse_scene_pos = QPointF(0, 0)

        # ---- Drawing state (temporary items while drawing) ----
        # These are QGraphicsItems added to the scene during DRAW_POLYGON
        # and removed when the polygon is finalized or cancelled.
        self._temp_vertex_items: list[QGraphicsEllipseItem] = []
        self._temp_line_items: list[QGraphicsLineItem] = []

        # Grab reference to singleton state
        self._state = ProjectState.instance()

        # Connect to state signals so we can react to external changes
        self._state.tool_mode_changed.connect(self._on_tool_mode_changed)
        self._state.drawing_points_changed.connect(self._on_drawing_points_changed)
        self._state.polygons_changed.connect(self._on_polygons_changed)
        self._state.embedded_beams_changed.connect(self._on_embedded_beams_changed)
        self._state.beam_materials_changed.connect(lambda m: self._on_embedded_beams_changed(self._state.embedded_beams))
        self._state.selection_changed.connect(self._on_selection_changed)

        # Track committed polygon items for re-rendering
        self._polygon_items: list[QGraphicsPolygonItem] = []
        self._beam_items: list[QGraphicsLineItem] = []
        self._beam_head_items: list[QGraphicsRectItem] = []

        # Track mesh wireframe items (drawn after backend returns mesh)
        self._mesh_items: list[QGraphicsPathItem] = []
        
        # Track pickable markers for PICK_POINT mode
        self._pickable_items: list[QGraphicsItem] = []
        self._node_markers: dict[int, QGraphicsEllipseItem] = {} # node_idx -> item
        self._gp_markers: dict[str, QGraphicsEllipseItem] = {}   # "el_idx:gp_idx" -> item

        # Throttled Mesh Redraw Timer (to prevent crashes during rapid staging toggles)
        from PySide6.QtCore import QTimer
        self._mesh_redraw_timer = QTimer(self)
        self._mesh_redraw_timer.setSingleShot(True)
        self._mesh_redraw_timer.setInterval(80) # 80ms throttle for mesh redraws
        self._mesh_redraw_timer.timeout.connect(self._throttled_mesh_redraw)

        # Connect mesh_response_changed to auto-draw mesh
        self._state.mesh_response_changed.connect(self._on_mesh_response_changed)

        # Connect load and water level signals
        self._state.point_loads_changed.connect(self._on_point_loads_changed)
        self._state.line_loads_changed.connect(self._on_line_loads_changed)
        self._state.water_levels_changed.connect(self._on_water_levels_changed)
        self._state.tracked_points_changed.connect(self._on_tracked_points_changed)

        # Track items for persistent entities
        self._load_items: list[QGraphicsItem] = []
        self._water_items: list[QGraphicsItem] = []
        self._tracked_marker_items: list[QGraphicsItem] = []

        # ---- Drag-and-drop support (material assignment) ----
        self.setAcceptDrops(True)

        # Connect to tab changes to handle visibility and toolbar repositioning
        self._state.active_tab_changed.connect(self._on_tab_changed)
        self._state.tool_mode_changed.connect(self._on_tool_mode_changed)

        # Connect to phase changes for dynamic staging updates
        self._state.current_phase_changed.connect(self._on_current_phase_changed)
        self._state.phases_changed.connect(lambda p: self._on_current_phase_changed(self._state.current_phase_index))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._reposition_toolbar()

    def _on_tab_changed(self, tab_name: str):
        """React to wizard tab changes (show/hide mesh, reposition toolbar)."""
        self._reposition_toolbar()
        
        # Only show mesh in MESH tab for this canvas
        show_mesh = tab_name == "MESH"
        for item in self._mesh_items:
            item.setVisible(show_mesh)
            
        # Refresh all items to apply tab-specific styling (like staging greyscale)
        self._on_polygons_changed(self._state.polygons)
        self._on_point_loads_changed(self._state.point_loads)
        self._on_line_loads_changed(self._state.line_loads)
        self._on_water_levels_changed(self._state.water_levels)

        # Auto-deactivate PICK_POINT if leaving MESH tab (Reset to last save)
        if tab_name != "MESH" and self._state.tool_mode == "PICK_POINT":
            self._state.rollback_tracked_points()
            self._state.set_tool_mode("SELECT")

        # Refresh persistent tracked points (MESH ONLY)
        if tab_name == "MESH" and self._state.tool_mode != "PICK_POINT":
            self._render_tracked_points()
        else:
            self._clear_tracked_markers()

        # Refresh viewport to apply grid visibility changes (drawn in drawBackground)
        self.viewport().update()
        self._scene.update()

    def _on_current_phase_changed(self, index: int):
        """Refresh canvas elements to reflect active components in the selected phase."""
        if self._state.active_tab == "STAGING":
            self._on_polygons_changed(self._state.polygons)
            self._on_point_loads_changed(self._state.point_loads)
            self._on_line_loads_changed(self._state.line_loads)
            self._on_water_levels_changed(self._state.water_levels)
            self._on_embedded_beams_changed(self._state.embedded_beams)

    def _reposition_toolbar(self):
        """Calculate and apply position for the floating TopToolBar."""
        for child in self.children():
            # Check for name since we might have circular import if we use isinstance
            if type(child).__name__ == "TopToolBar":
                # Position top right with 16px marging
                child.move(self.width() - child.width() - 16, 24)
                break

    def drawForeground(self, painter: QPainter, rect: QRectF):
        """Draw dynamic rulers on top of the view if enabled."""
        state = ProjectState.instance()

        painter.save()
        # Detach from scene coordinates, paint in widget (pixel) coordinates
        painter.resetTransform()

        view_rect = self.viewport().rect()
        W, H = view_rect.width(), view_rect.height()
        RULER_SIZE = 22

        if state.settings.get("show_ruler", True):
            # Draw backgrounds
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(255, 255, 255, 240)) # Slightly translucent white
            painter.drawRect(0, 0, W, RULER_SIZE) # Top horizontal
            painter.drawRect(0, 0, RULER_SIZE, H) # Left vertical

            # Draw border lines
            painter.setPen(QColor("#d4d4d8"))
            painter.drawLine(0, RULER_SIZE, W, RULER_SIZE)
            painter.drawLine(RULER_SIZE, 0, RULER_SIZE, H)

            # Draw text & ticks
            font = painter.font()
            font.setPointSize(7)
            painter.setFont(font)
            painter.setPen(QColor("#71717a"))

            # We need the inverse transform to know which scene coordinates are visible
            transform = self.viewportTransform()
            inv_transform, _ = transform.inverted()

            # Generate tick intervals (heuristic based on zoom)
            scene_width = inv_transform.mapRect(QRectF(view_rect)).width()
            
            step = 1.0
            if scene_width > 500: step = 100.0
            elif scene_width > 100: step = 10.0
            elif scene_width > 50: step = 5.0
            
            # Horizontal Ruler (Top)
            left_scene = inv_transform.map(QPointF(0, 0)).x()
            right_scene = inv_transform.map(QPointF(W, 0)).x()
            
            start_x = int(left_scene / step) * step
            x = start_x
            while x <= right_scene:
                px = transform.map(QPointF(x, 0)).x()
                if px >= RULER_SIZE:
                    painter.drawLine(px, RULER_SIZE - 4, px, RULER_SIZE)
                    painter.drawText(px + 2, RULER_SIZE - 6, f"{x:g}")
                x += step

            # Vertical Ruler (Left)
            top_scene = inv_transform.map(QPointF(0, 0)).y()
            bottom_scene = inv_transform.map(QPointF(0, H)).y()

            min_y = min(top_scene, bottom_scene)
            max_y = max(top_scene, bottom_scene)
            
            start_y = int(min_y / step) * step
            y = start_y
            while y <= max_y:
                py = transform.map(QPointF(0, y)).y()
                if py >= RULER_SIZE:
                    painter.drawLine(RULER_SIZE - 4, py, RULER_SIZE, py)
                    
                    painter.save()
                    # Offset for vertical label
                    painter.translate(RULER_SIZE - 6, py - 6)
                    painter.rotate(-90)
                    painter.drawText(0, 0, f"{y:g}")
                    painter.restore()
                y += step
                
            # Draw top-left intersection block
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(255, 255, 255, 255))
            painter.drawRect(0, 0, RULER_SIZE, RULER_SIZE)
            painter.setPen(QColor("#d4d4d8"))
            painter.drawLine(RULER_SIZE, 0, RULER_SIZE, RULER_SIZE)
            painter.drawLine(0, RULER_SIZE, RULER_SIZE, RULER_SIZE)

        # Coordinate Tooltip
        if hasattr(self, '_current_mouse_scene_pos') and self._current_mouse_scene_pos:
            # Draw Dynamic Tracker Line for DRAW_POLYGON
            if state.active_tab == "INPUT" and state.tool_mode == "DRAW_POLYGON" and state.drawing_points:
                last_pt = state.drawing_points[-1]
                t_pen = QPen(COLOR_DRAW_LINE, 1.5)
                t_pen.setStyle(Qt.DashLine)
                t_pen.setCosmetic(True)
                painter.setPen(t_pen)
                
                # We need to map scene coordinates back to view coordinates for painter
                p1_px = transform.map(QPointF(last_pt["x"], last_pt["y"]))
                p2_px = transform.map(self._current_mouse_scene_pos)
                painter.drawLine(p1_px, p2_px)
                
                # Also draw an implicit closing line connecting back to the first point
                if len(state.drawing_points) >= 3:
                     first_px = transform.map(QPointF(state.drawing_points[0]["x"], state.drawing_points[0]["y"]))
                     close_pen = QPen(t_pen)
                     close_pen.setColor(QColor(100, 150, 255, 150))
                     painter.setPen(close_pen)
                     painter.drawLine(p2_px, first_px)

            elif state.active_tab == "INPUT" and state.tool_mode == "DRAW_RECTANGLE" and state.drawing_points:
                # Rectangle mode
                first_pt = state.drawing_points[0]
                t_pen = QPen(COLOR_DRAW_LINE, 1.5)
                t_pen.setStyle(Qt.DashLine)
                t_pen.setCosmetic(True)
                painter.setPen(t_pen)

                p1_px = transform.map(QPointF(first_pt["x"], first_pt["y"]))
                p2_px = transform.map(self._current_mouse_scene_pos)
                
                # Draw dynamic bounding box
                painter.drawLine(p1_px.x(), p1_px.y(), p2_px.x(), p1_px.y())
                painter.drawLine(p2_px.x(), p1_px.y(), p2_px.x(), p2_px.y())
                painter.drawLine(p2_px.x(), p2_px.y(), p1_px.x(), p2_px.y())
                painter.drawLine(p1_px.x(), p2_px.y(), p1_px.x(), p1_px.y())

            elif state.active_tab == "INPUT" and state.tool_mode == "DRAW_EMBEDDED_BEAM" and state.drawing_points:
                # Beam row dynamic line
                first_pt = state.drawing_points[0]
                t_pen = QPen(QColor("#2563eb"), 2)
                t_pen.setStyle(Qt.DashLine)
                t_pen.setCosmetic(True)
                painter.setPen(t_pen)
                
                p1_px = transform.map(QPointF(first_pt["x"], first_pt["y"]))
                p2_px = transform.map(self._current_mouse_scene_pos)
                painter.drawLine(p1_px, p2_px)

            # Draw Coordinate Tooltip
            coord_text = f"X: {self._current_mouse_scene_pos.x():g}  Y: {self._current_mouse_scene_pos.y():g}"
            
            font = painter.font()
            font.setPointSize(8)
            painter.setFont(font)
            
            fm = painter.fontMetrics()
            tw = fm.horizontalAdvance(coord_text)
            th = fm.height()

            # Draw bottom left coordinate box
            box_x = RULER_SIZE + 10 if state.settings.get("show_ruler", True) else 10
            box_y = H - th - 16
            
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(255, 255, 255, 230))
            painter.drawRoundedRect(box_x, box_y, tw + 16, th + 8, 4, 4)
            
            painter.setPen(QColor("#3f3f46")) # zinc-700
            painter.drawText(box_x + 8, box_y + th + 1, coord_text)

        painter.restore()
    # ==================================================================
    # State signal handlers
    # ==================================================================

    def _on_tool_mode_changed(self, mode: str):
        """
        React to tool-mode changes.
        Clears temporary drawing items when leaving a drawing mode.
        """
        # Clean up temp items when switching away from drawing mode
        self._clear_temp_items()

        # Change cursor based on mode
        if mode == "PICK_POINT":
            self.setCursor(Qt.PointingHandCursor)
            self._show_pickable_points()
        else:
            # Clear interactive markers for all other modes
            self._clear_pickable_points()
            self._render_tracked_points()

            if mode == "SELECT":
                self.setCursor(Qt.ArrowCursor)
            elif mode in ("DRAW_POLYGON", "DRAW_RECTANGLE", "DRAW_WATER_LEVEL", "DRAW_EMBEDDED_BEAM", "ADD_POINT_LOAD", "ADD_LINE_LOAD"):
                self.setCursor(Qt.CrossCursor)
            elif mode == "ASSIGN_MATERIAL":
                self.setCursor(Qt.PointingHandCursor)
            else:
                self.setCursor(Qt.ArrowCursor)

    def _on_drawing_points_changed(self, points: list[dict]):
        """
        Redraw temporary vertex markers + connecting lines whenever
        the drawing buffer in ProjectState changes.
        """
        self._clear_temp_items()

        if not points:
            return

        pen = QPen(COLOR_DRAW_VERTEX, 0)
        brush = QBrush(COLOR_DRAW_VERTEX)
        line_pen = QPen(COLOR_DRAW_LINE, 0)
        line_pen.setStyle(Qt.DashLine)

        for i, pt in enumerate(points):
            # Vertex marker (small filled circle)
            ellipse = self._scene.addEllipse(
                pt["x"] - POINT_RADIUS,
                pt["y"] - POINT_RADIUS,
                POINT_RADIUS * 2,
                POINT_RADIUS * 2,
                pen, brush
            )
            ellipse.setZValue(100)  # Above polygons
            self._temp_vertex_items.append(ellipse)

            # Connecting line to previous vertex
            if i > 0:
                prev = points[i - 1]
                line = self._scene.addLine(
                    prev["x"], prev["y"],
                    pt["x"], pt["y"],
                    line_pen
                )
                line.setZValue(99)
                self._temp_line_items.append(line)

    def _on_polygons_changed(self, polygons: list[dict]):
        """
        Re-render all committed polygons when ProjectState polygon data
        changes (added, removed, or modified).
        """
        # Remove old polygon items
        for item in self._polygon_items:
            self._scene.removeItem(item)
        self._polygon_items.clear()

        # Draw each polygon
        for i, poly_data in enumerate(polygons):
            vertices = poly_data.get("vertices", [])
            if len(vertices) < 3:
                continue

            # Build QPolygonF from vertices
            qpoly = QPolygonF()
            for v in vertices:
                qpoly.append(QPointF(v["x"], v["y"]))
            
            # Explicitly close the polygon outline to ensure the border stroke connects back to point 1
            if len(vertices) > 2 and vertices[-1] != vertices[0]:
                qpoly.append(QPointF(vertices[0]["x"], vertices[0]["y"]))

            # Determine fill color from material
            fill_color = QColor(COLOR_POLYGON_FILL)
            
            # STAGING Logic: Check if inactive
            is_staging = self._state.active_tab == "STAGING"
            current_phase = self._state.current_phase if is_staging else None
            
            is_active = True
            if is_staging and current_phase:
                active_indices = current_phase.get("active_polygon_indices", [])
                is_active = i in active_indices
            
            if not is_active:
                # Inactive: Light grey ghost
                fill_color = QColor("#f4f4f5") # zinc-100
                fill_color.setAlpha(30)
                pen = QPen(QColor("#e4e4e7"), 0) # zinc-200
            else:
                # Active: Material color
                mat_id = poly_data.get("materialId")
                # Try to get material override from phase if available
                if is_staging and current_phase:
                    mat_overrides = current_phase.get("current_material", {})
                    if str(i) in mat_overrides:
                        mat_id = mat_overrides[str(i)]
                
                if mat_id:
                    for mat in self._state.materials:
                        if mat.get("id") == mat_id:
                            c = QColor(mat.get("color", "#4CAF50"))
                            c.setAlpha(60)
                            fill_color = c
                            break
                pen = QPen(QColor("#AAAAAA"), 0)

            brush = QBrush(fill_color)
            item = self._scene.addPolygon(qpoly, pen, brush)
            item.setZValue(10)
            item.setData(Qt.UserRole, i) # Store index for selection sync
            
            self._polygon_items.append(item)

        # Force a repaint to eliminate any rendering artifacts (e.g. after deletion)
        self.viewport().update()
        self._scene.update()

        # Re-apply selection styling if active
        self._on_selection_changed(self._state.selected_entity)

    def _on_embedded_beams_changed(self, beams: list[dict]):
        """Render structural beams as lines colored by material."""
        # Clear old beams and heads
        for item in self._beam_items:
            self._scene.removeItem(item)
        self._beam_items.clear()
        for item in self._beam_head_items:
            self._scene.removeItem(item)
        self._beam_head_items.clear()

        bm_lookup = {m.get("id"): m for m in self._state.beam_materials}
        is_staging = self._state.active_tab == "STAGING"
        current_phase = self._state.current_phase if is_staging else None

        for b in beams:
            x1, y1 = b.get("x1"), b.get("y1")
            x2, y2 = b.get("x2"), b.get("y2")
            bid = b.get("id")
            mid = b.get("materialId")

            is_active = True
            if is_staging and current_phase:
                is_active = bid in current_phase.get("active_beam_ids", [])

            # Get material color
            color = QColor("#555")
            if is_active and mid and mid in bm_lookup:
                color = QColor(bm_lookup[mid].get("color", "#2563eb"))
            elif not is_active:
                color = QColor("#e4e4e7")
                color.setAlpha(100)

            pen = QPen(color, 3 if is_active else 1)
            pen.setCosmetic(True)
            
            # 1. Add Beam Line
            line = self._scene.addLine(x1, y1, x2, y2, pen)
            line.setZValue(60) # Above mesh (50), below loads (150)
            line.setData(Qt.UserRole, bid)
            line.setData(Qt.UserRole + 1, "embedded_beam")
            self._beam_items.append(line)
            
            # 2. Add Head Symbol
            h_idx = b.get("head_point_index", 0)
            px, py = (x1, y1) if h_idx == 0 else (x2, y2)
            tx, ty = (x2, y2) if h_idx == 0 else (x1, y1)
            
            head_conn = str(b.get("head_connection_type", "FIXED")).upper()
            marker_size = 0.15 # Scene units (meters)
            
            color_head = color if is_active else QColor("#d1d5db")
            if not is_active: color_head.setAlpha(120)
            h_pen = QPen(color_head, 0.1)
            h_brush = QBrush(color_head)

            if head_conn in ["FIXED", "FIX"]:
                # Square
                rect = self._scene.addRect(px - marker_size/2, py - marker_size/2, marker_size, marker_size, h_pen, h_brush)
                rect.setZValue(65)
                self._beam_head_items.append(rect)
            else:
                # Triangle pointing into beam
                import math
                angle_rad = math.atan2(ty - py, tx - px)
                
                p_tri = [QPointF(0, 0), QPointF(marker_size, -marker_size/2.5), QPointF(marker_size, marker_size/2.5)]
                q_poly = QPolygonF(p_tri)
                
                trans = QTransform().translate(px, py).rotateRadians(angle_rad)
                rotated_poly = trans.map(q_poly)
                
                tri_item = self._scene.addPolygon(rotated_poly, h_pen, h_brush)
                tri_item.setZValue(65)
                self._beam_head_items.append(tri_item)


        # Apply selection
        self._on_selection_changed(self._state.selected_entity)

    def _on_selection_changed(self, selection: dict | None):
        """Update polygon styling visually when selection state changes."""
        active_idx = -1
        active_id = None
        sel_type = None

        if selection:
            sel_type = selection.get("type")
            if sel_type == "polygon":
                active_idx = selection.get("index")
            elif sel_type in ["embedded_beam", "point_load", "line_load", "water_level"]:
                active_id = selection.get("id")

        for i, item in enumerate(self._polygon_items):
            # Guard against index mismatch during rapid updates or deletions
            if i >= len(self._state.polygons):
                continue
            
            poly_data = self._state.polygons[i]
            is_staging = self._state.active_tab == "STAGING"
            cur_ph = self._state.current_phase if is_staging else None
            
            # --- 1. Determine Base Color ---
            mat_id = poly_data.get("materialId")
            if is_staging and cur_ph:
                mat_overrides = cur_ph.get("current_material", {})
                if str(i) in mat_overrides:
                    mat_id = mat_overrides[str(i)]

            # Default fallback color
            base_color = QColor("#4CAF50")
            if mat_id:
                for mat in self._state.materials:
                    if mat.get("id") == mat_id:
                        base_color = QColor(mat.get("color", "#4CAF50"))
                        break

            # --- 2. Determine Selection Style ---
            if i == active_idx:
                # Active selection: Thick dark border
                base_color.setAlpha(255)
                active_pen = QPen(base_color.darker(150), 3.5)
                active_pen.setCosmetic(True)
                active_pen.setJoinStyle(Qt.RoundJoin)
                item.setPen(active_pen)
                item.setZValue(20)
            else:
                # Default style
                is_active = True
                if is_staging and cur_ph:
                    is_active = i in cur_ph.get("active_polygon_indices", [])
                
                if not is_active:
                    border_color = QColor("#e4e4e7")
                    item.setZValue(5)
                else:
                    border_color = base_color.darker(120)
                    item.setZValue(10)
                
                default_pen = QPen(border_color, 2)
                default_pen.setCosmetic(True)
                default_pen.setJoinStyle(Qt.RoundJoin)
                
                # Apply alpha based on staging status
                base_color.setAlpha(180 if is_active else 30)
                item.setPen(default_pen)

        # --- Update Beam selection ---
        bm_lookup = {m.get("id"): m for m in self._state.beam_materials}
        for item in self._beam_items:
            bid = item.data(Qt.UserRole)
            is_sel = (sel_type == "embedded_beam" and bid == active_id)
            
            is_staging = self._state.active_tab == "STAGING"
            current_phase = self._state.current_phase if is_staging else None
            is_active = True
            if is_staging and current_phase:
                is_active = bid in current_phase.get("active_beam_ids", [])

            # Find data
            beam_data = next((b for b in self._state.embedded_beams if b.get("id") == bid), None)
            mid = beam_data.get("materialId") if beam_data else None
            
            mat_color = QColor("#2563eb")
            if mid and mid in bm_lookup:
                mat_color = QColor(bm_lookup[mid].get("color", "#2563eb"))

            if is_sel:
                pen = QPen(mat_color.darker(150), 5)
                item.setZValue(65)
            else:
                c = QColor(mat_color) if is_active else QColor("#e4e4e7")
                if not is_active: c.setAlpha(100)
                pen = QPen(c, 3 if is_active else 1)
                item.setZValue(60)
            
            pen.setCosmetic(True)
            item.setPen(pen)

            # --- 3. Interaction State ---
            if self._state.active_tab == "MESH":
                item.setAcceptHoverEvents(False)
                item.setAcceptedMouseButtons(Qt.NoButton)
            else:
                item.setAcceptedMouseButtons(Qt.LeftButton | Qt.RightButton)

        self.viewport().update()
        self._scene.update()

        # Trigger redraw of loads and water levels to apply selection thickness
        self._on_point_loads_changed(self._state.point_loads)
        self._on_line_loads_changed(self._state.line_loads)
        self._on_water_levels_changed(self._state.water_levels)

    def _on_current_phase_changed(self, index: int):
        """React to phase switches in Staging tab."""
        # Refresh all geometry items to show current phase visibility/colors
        self._on_polygons_changed(self._state.polygons)
        self._on_embedded_beams_changed(self._state.embedded_beams)
        self._on_point_loads_changed(self._state.point_loads)
        self._on_line_loads_changed(self._state.line_loads)
        self._on_water_levels_changed(self._state.water_levels)
        
        # Throttled mesh redraw (very expensive)
        if self._state.mesh_response:
             self._mesh_redraw_timer.start()

    def _throttled_mesh_redraw(self):
        """Actually perform the mesh redraw after the throttle interval."""
        if self._state.mesh_response:
            self.draw_mesh(self._state.mesh_response)
            show_mesh = self._state.active_tab in ["MESH", "RESULT"]
            for item in self._mesh_items:
                item.setVisible(show_mesh)
        
        # Always update persistent tracked points if in MESH/RESULT tab
        if self._state.active_tab in ["MESH", "RESULT"] and self._state.tool_mode != "PICK_POINT":
            self._render_tracked_points()
        else:
            self._clear_tracked_markers()

    def _on_mesh_response_changed(self, mesh_data: dict | None):
        """Re-render mesh when the backend returns new data."""
        if self._state.tool_mode == "PICK_POINT":
            self._show_pickable_points()
            
        if mesh_data:
            self.draw_mesh(mesh_data)
            # Immediatley apply tab-based visibility
            show_mesh = self._state.active_tab in ["MESH", "RESULT"]
            for item in self._mesh_items:
                item.setVisible(show_mesh)
        else:
            self.clear_mesh()

    def _show_pickable_points(self):
        """Render all nodes and Gauss Points as clickable markers (Picking Mode)."""
        # Strict isolation: Only allow picking in MESH tab
        if self._state.active_tab != "MESH":
            self._clear_pickable_points()
            return
            
        self._clear_pickable_points()
        self._clear_tracked_markers() # Hide persistent markers while picking to avoid overlap
        
        mesh = self._state.mesh_response
        if not mesh: return
        
        nodes = mesh.get("nodes", [])
        elements = mesh.get("elements", [])
        
        # Compact style for picking
        pen = QPen(QColor("#94a3b8"), 1) # slate-400
        pen.setCosmetic(True)
        brush_node = QBrush(QColor("#f1f5f9")) # slate-100
        brush_gp   = QBrush(QColor("#ecfdf5")) # emerald-50
        
        tracked = { (p["type"], p["index"], p.get("gp_index")): p.get("label", "?") for p in self._state.tracked_points }
        
        # Font for labels
        label_font = QFont("Inter", 8, QFont.Bold)

        transform = QTransform()
        transform.scale(0.015,-0.015)

        # 1. Draw Nodes
        r = 0.1 # Compact
        for i, n in enumerate(nodes):
            x, y = n[0], n[1]
            ellipse = self._scene.addEllipse(x-r, y-r, r*2, r*2, pen, brush_node)
            ellipse.setZValue(200)
            ellipse.setData(Qt.UserRole, i)
            ellipse.setData(Qt.UserRole + 1, "node")
            
            label = tracked.get(("node", i, None))
            if label:
                # Highlighted
                sel_pen = QPen(QColor("#ef4444"), 1, Qt.SolidLine)
                sel_pen.setCosmetic(True)
                ellipse.setBrush(QBrush(QColor("#f87171")))
                ellipse.setPen(sel_pen)
                
                # Add Text Label
                txt = self._scene.addSimpleText(label, label_font)
                txt.setBrush(QBrush(QColor("#b91c1c"))) # red-700
                txt.setPos(x + r*1.5, y + r*3)
                # Text in scene units needs extreme downscaling if items are small
                # Or set it to ignore transformations for readability?
                # For now, let's use a very small scale to match geotechnical dimensions (m)
                txt.setTransform(transform) 
                txt.setZValue(210)
                self._pickable_items.append(txt)

            self._pickable_items.append(ellipse)
            self._node_markers[i] = ellipse

        # 2. Draw Gauss Points
        gp_r = 0.06 # Compact
        for i, el in enumerate(elements):
            if len(el) < 3: continue
            p1, p2, p3 = nodes[el[0]], nodes[el[1]], nodes[el[2]]
            gps = [(1/6, 1/6, 2/3), (1/6, 2/3, 1/6), (2/3, 1/6, 1/6)]
            
            for gp_idx, (l1, l2, l3) in enumerate(gps):
                gx = l1*p1[0] + l2*p2[0] + l3*p3[0]
                gy = l1*p1[1] + l2*p2[1] + l3*p3[1]
                
                ellipse = self._scene.addEllipse(gx-gp_r, gy-gp_r, gp_r*2, gp_r*2, pen, brush_gp)
                ellipse.setZValue(200)
                ellipse.setData(Qt.UserRole, i)
                ellipse.setData(Qt.UserRole + 1, "gp")
                ellipse.setData(Qt.UserRole + 2, gp_idx)
                
                label = tracked.get(("gp", i, gp_idx))
                if label:
                    sel_pen = QPen(QColor("#b45309"), 1, Qt.SolidLine)
                    sel_pen.setCosmetic(True)
                    ellipse.setBrush(QBrush(QColor("#fbbf24")))
                    ellipse.setPen(sel_pen)
                    
                    # Add Text Label
                    txt = self._scene.addSimpleText(label, label_font)
                    txt.setBrush(QBrush(QColor("#92400e"))) # amber-800
                    txt.setPos(gx + gp_r*1.5, gy + gp_r*3)
                    txt.setTransform(transform)
                    txt.setZValue(210)
                    self._pickable_items.append(txt)

                self._pickable_items.append(ellipse)
                self._gp_markers[f"{i}:{gp_idx}"] = ellipse

    def _clear_pickable_points(self):
        for item in self._pickable_items:
            self._scene.removeItem(item)
        self._pickable_items.clear()
        self._node_markers.clear()
        self._gp_markers.clear()

    # ==================================================================
    # Navigation / Zoom
    # ==================================================================

    def zoom_in(self):
        self.scale(1.2, 1.2)

    def zoom_out(self):
        self.scale(1.0 / 1.2, 1.0 / 1.2)

    def zoom_fit(self):
        items_rect = self._scene.itemsBoundingRect()
        if not items_rect.isNull():
            self.fitInView(items_rect, Qt.KeepAspectRatio)

    # ==================================================================
    # Mesh Rendering
    # ==================================================================

    def draw_mesh(self, mesh_data: dict):
        """
        Render the FEM mesh as a wireframe overlay on the canvas.

        Parameters
        ----------
        mesh_data : dict
            The MeshResponse from the backend, containing:
            - "nodes":    list of [x, y] coordinate pairs
            - "elements": list of [n1, n2, n3, n4, n5, n6] (T6 triangles)
                          where n1-n3 are corner nodes, n4-n6 are midside nodes.

        We only draw edges between the 3 corner nodes (n1, n2, n3) since
        the midside nodes are for quadratic interpolation, not geometry.
        """
        # Clear any existing mesh items first
        self.clear_mesh()

        nodes = mesh_data.get("nodes", [])
        elements = mesh_data.get("elements", [])

        if not nodes or not elements:
            return

        # Pen for mesh edges — cosmetic (constant pixel width regardless of zoom)
        mesh_pen = QPen(COLOR_MESH_EDGE, 0)
        mesh_pen.setCosmetic(True)

        # Build a single QPainterPath for ALL triangles — much more efficient
        # than creating individual line items for each edge.
        batch_path = QPainterPath()

        # Build element-to-polygon map for filtering
        element_materials = mesh_data.get("element_materials", [])
        el_to_poly = {}
        for em in element_materials:
            el_to_poly[em["element_id"] - 1] = em.get("polygon_id")

        current_phase = self._state.current_phase
        active_indices = set(current_phase.get("active_polygon_indices", [])) if current_phase else set()
        is_mesh_tab = self._state.active_tab == "MESH"

        for idx, elem in enumerate(elements):
            # Filtering: In STAGING/RESULT tabs, only show elements belonging to active polygons
            if not is_mesh_tab:
                poly_id = el_to_poly.get(idx)
                if poly_id is not None and poly_id not in active_indices:
                    continue

            # T6 element: [n1, n2, n3, n4, n5, n6]
            if len(elem) < 3:
                continue

            # Get corner node indices (0-based)
            i0, i1, i2 = elem[0], elem[1], elem[2]
            if i0 >= len(nodes) or i1 >= len(nodes) or i2 >= len(nodes):
                continue

            # Node coordinates
            x0, y0 = nodes[i0][0], nodes[i0][1]
            x1, y1 = nodes[i1][0], nodes[i1][1]
            x2, y2 = nodes[i2][0], nodes[i2][1]

            # Draw triangle edges
            batch_path.moveTo(x0, y0)
            batch_path.lineTo(x1, y1)
            batch_path.lineTo(x2, y2)
            batch_path.lineTo(x0, y0)

        # Add the complete path as a single QGraphicsPathItem
        if not batch_path.isEmpty():
            path_item = self._scene.addPath(batch_path, mesh_pen)
            path_item.setZValue(50)  # Above polygons (10), below drawing items (99+)
            
            # Visibility: only if we are currently in the MESH tab
            path_item.setVisible(self._state.active_tab == "MESH")
            
            self._mesh_items.append(path_item)

    def clear_mesh(self):
        """Remove all mesh wireframe items from the scene."""
        for item in self._mesh_items:
            self._scene.removeItem(item)
        self._mesh_items.clear()

    # ==================================================================
    # Temp item management
    # ==================================================================

    def _handle_point_pick(self, item: QGraphicsEllipseItem):
        """Toggle selection of a node or GP."""
        etype = item.data(Qt.UserRole + 1)
        idx = item.data(Qt.UserRole)
        gp_idx = item.data(Qt.UserRole + 2)
        
        current_tracked = self._state.tracked_points
        
        # Check if already tracked
        existing_idx = -1
        for i, p in enumerate(current_tracked):
            if p["type"] == etype and p["index"] == idx and p.get("gp_index") == gp_idx:
                existing_idx = i
                break
        
        if existing_idx >= 0:
            # Deselect
            p = current_tracked.pop(existing_idx)
            self._state.set_tracked_points(current_tracked)
            self._state.log(f"Deselected {etype.upper()} index {idx}" + (f" GP {gp_idx}" if gp_idx is not None else ""))
            
            # Reset color
            item.setBrush(QBrush(QColor("#f1f5f9") if etype == "node" else QColor("#ecfdf5")))
            item.setPen(QPen(QColor("#94a3b8"), 0))
        else:
            # Select
            if etype == "node":
                label = f"{idx}"
            else:
                label = f"{idx}/{gp_idx}"
            
            new_pt = {
                "id": f"{etype}_{idx}" + (f"_{gp_idx}" if gp_idx is not None else ""),
                "type": etype,
                "index": idx,
                "gp_index": gp_idx,
                "label": label,
                "x": item.rect().center().x(),
                "y": item.rect().center().y()
            }
            current_tracked.append(new_pt)
            self._state.set_tracked_points(current_tracked)
            self._state.log(f"Selected {etype.upper()} index {idx}" + (f" GP {gp_idx}" if gp_idx is not None else "") + f" as Point {label}")
            
            # Highlights color
            item.setBrush(QBrush(QColor("#f87171") if etype == "node" else QColor("#fbbf24")))
            item.setPen(QPen(QColor("#991b1b") if etype == "node" else QColor("#92400e"), 1, Qt.SolidLine))

    def _on_tracked_points_changed(self, points: list):
        """Handle external changes to tracked points (sync visual state)."""
        if self._state.tool_mode == "PICK_POINT":
            self._show_pickable_points()
        else:
            self._render_tracked_points()

    def _render_tracked_points(self):
        """Persistent rendering of tracked points (Compact View)."""
        self._clear_tracked_markers()
        
        # Only show tracked points in MESH tab (Strict Isolation)
        if self._state.active_tab != "MESH":
            return
            
        points = self._state.tracked_points
        if not points: return
        
        for p in points:
            etype = p["type"]
            px, py = p["x"], p["y"]
            label = p["label"]
            
            # Use distinct but compact markers
            color = QColor("#ef4444") if etype == "node" else QColor("#f59e0b") # red-500 or amber-500
            pen = QPen(color.darker(150), 1)
            pen.setCosmetic(True)
            brush = QBrush(color)
            
            r = 0.1 if etype == "node" else 0.07
            dot = self._scene.addEllipse(px-r, py-r, r*2, r*2, pen, brush)
            dot.setZValue(210) # Above mesh and unselected points
            self._tracked_marker_items.append(dot)
            
            # Persistent Text Label
            transform = QTransform()
            transform.scale(0.015,-0.015)
            lbl_font = QFont("Inter", 8, QFont.Bold)
            txt = self._scene.addSimpleText(label, lbl_font)
            txt.setBrush(QBrush(color.darker(150)))
            txt.setPos(px + r*1.5, py + r*3)
            txt.setTransform(transform)
            txt.setZValue(215)
            self._tracked_marker_items.append(txt)
            
            # Optional: Add small label text
            # from PySide6.QtWidgets import QGraphicsTextItem
            # txt = self._scene.addText(label)
            # txt.setPos(px + r, py - r)
            # txt.setScale(0.01) # Very small since we are in scene units
            # self._tracked_marker_items.append(txt)

    def _clear_tracked_markers(self):
        """Remove persistent tracked point markers."""
        for item in self._tracked_marker_items:
            try: self._scene.removeItem(item)
            except: pass
        self._tracked_marker_items.clear()

    def _clear_temp_items(self):
        """Remove all temporary drawing items from the scene."""
        for item in self._temp_vertex_items:
            self._scene.removeItem(item)
        self._temp_vertex_items.clear()

        for item in self._temp_line_items:
            self._scene.removeItem(item)
        self._temp_line_items.clear()


    # ==================================================================
    # Mouse Events
    # ==================================================================

    def mousePressEvent(self, event: QMouseEvent):
        """
        Dispatch mouse press based on the current tool mode.
        - Middle button always starts panning.
        - Left button behavior depends on tool_mode.
        """
        # ---- MIDDLE BUTTON: Pan ----
        if event.button() == Qt.MiddleButton:
            self._is_panning = True
            self._pan_start = event.position()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
            return

        # Map to scene
        viewport_pos = event.pos()
        raw_scene_pos = self.mapToScene(viewport_pos)
        
        # Calculate snapped position for drawing tools (grid snap)
        scene_pos = QPointF(raw_scene_pos)
        settings = self._state.settings
        if settings.get("snap_to_grid", False):
            spacing = settings.get("grid_spacing", 1.0)
            if spacing <= 0: spacing = 1.0
            scene_pos.setX(round(scene_pos.x() / spacing) * spacing)
            scene_pos.setY(round(scene_pos.y() / spacing) * spacing)

        active_tab = self._state.active_tab

        # ---- PICK_POINT Mode Handling ----
        if event.button() == Qt.LeftButton and self._state.tool_mode == "PICK_POINT":
            # REVOLUTIONARY FIX: Distance-based 'Ground Truth' detection.
            # We ignore graphics-engine hit testing and use pure coordinate math.
            found_item = None
            threshold = 0.5  # Max search distance in scene units (geotechnical units)
            
            # Check for the closest pickable item in the scene
            best_dist = threshold**2
            
            # We search within a small area to find candidate items
            search_rect = QRectF(raw_scene_pos.x() - threshold, raw_scene_pos.y() - threshold, threshold*2, threshold*2)
            candidates = self._scene.items(search_rect)
            
            for item in candidates:
                etype = item.data(Qt.UserRole + 1)
                if etype in ["node", "gp"]:
                    # Get the visual center of the marker
                    # Ellipses are created at (x-r, y-r, 2r, 2r), so their scenePos is usually the center
                    # if they were added via setPos, but here they are children of scene with rects.
                    rect = item.boundingRect()
                    center = item.scenePos() + rect.center()
                    
                    dx = center.x() - raw_scene_pos.x()
                    dy = center.y() - raw_scene_pos.y()
                    dist_sq = dx*dx + dy*dy
                    
                    if dist_sq < best_dist:
                        best_dist = dist_sq
                        found_item = item
            
            if found_item:
                self._handle_point_pick(found_item)
                event.accept()
                return
            else:
                event.accept() 
                return

        # ---- LEFT BUTTON: Tools & Selection ----
        if event.button() == Qt.LeftButton:
            mode = self._state.tool_mode
            
            # Selection logic: allowed in INPUT (SELECT tool) or STAGING tab
            if (active_tab == "INPUT" and mode == "SELECT") or active_tab == "STAGING":
                # Primary: itemAt
                found_item = self.itemAt(viewport_pos)
                if found_item and found_item.data(Qt.UserRole + 1) in ["point_load", "line_load", "water_level"]:
                    self._state.set_selected_entity({"type": found_item.data(Qt.UserRole + 1), "id": found_item.data(Qt.UserRole)})
                    event.accept()
                    return
                
                # Secondary: Forgiving Search
                search_rect = QRectF(raw_scene_pos.x() - 0.25, raw_scene_pos.y() - 0.25, 0.5, 0.5)
                for item in self._scene.items(search_rect):
                    etype = item.data(Qt.UserRole + 1)
                    eid = item.data(Qt.UserRole)
                    if etype in ["point_load", "line_load", "water_level"]:
                        self._state.set_selected_entity({"type": etype, "id": eid})
                        event.accept()
                        return
                
                # PASS 2: MATHEMATICAL PRECISION for Polygons
                # We check if the raw scene coordinate is strictly inside the polygon geometry.
                scene_pos_val = raw_scene_pos
                
                # Iterate in reverse to select the polygon 'on top' if overlapping
                polygons = self._state.polygons
                for i in range(len(polygons) - 1, -1, -1):
                    poly_data = polygons[i]
                    vertices = poly_data.get("vertices", [])
                    if len(vertices) < 3: continue
                    
                    # Create a geometric polygon for containment check
                    qpoly = QPolygonF()
                    for v in vertices:
                        qpoly.append(QPointF(v["x"], v["y"]))
                    
                    if qpoly.containsPoint(scene_pos, Qt.OddEvenFill):
                        self._state.set_selected_entity({"type": "polygon", "index": i})
                        event.accept()
                        return

                # PASS 3: Beam Row Selection (Line Hit Test)
                beams = self._state.embedded_beams
                beam_mat_lookup = {m.get("id"): m for m in self._state.beam_materials}
                
                import math
                def dist_to_seg(p, x1, y1, x2, y2):
                    L = math.hypot(x2-x1, y2-y1)
                    if L < 1e-9: return math.hypot(p.x()-x1, p.y()-y1)
                    t = ((p.x()-x1)*(x2-x1) + (p.y()-y1)*(y2-y1)) / (L*L)
                    t = max(0, min(1, t))
                    return math.hypot(p.x() - (x1 + t*(x2-x1)), p.y() - (y1 + t*(y2-y1)))

                for b in beams:
                    if dist_to_seg(scene_pos, b["x1"], b["y1"], b["x2"], b["y2"]) < 0.2:
                        self._state.set_selected_entity({"type": "embedded_beam", "id": b["id"]})
                        event.accept()
                        return

                # If we clicked empty space
                self._state.set_selected_entity(None)
                event.accept() 
                return

            # Drawing logic: ONLY in INPUT tab
            if active_tab == "INPUT":
                if mode in ["DRAW_POLYGON", "DRAW_RECTANGLE"]:
                    self._handle_draw_polygon_click(scene_pos)
                    event.accept()
                    return

                elif mode == "ADD_POINT_LOAD":
                    self._handle_add_point_load(scene_pos)
                    event.accept()
                    return
                
                elif mode == "ADD_LINE_LOAD":
                    self._handle_add_line_load(scene_pos)
                    event.accept()
                    return
                
                elif mode == "DRAW_WATER_LEVEL":
                    self._handle_draw_water_level_click(scene_pos)
                    event.accept()
                    return
                
                elif mode == "DRAW_EMBEDDED_BEAM":
                    self._handle_draw_beam_click(scene_pos)
                    event.accept()
                    return

        # ---- RIGHT BUTTON: Context Menu ----
        elif event.button() == Qt.RightButton:
            # Consistent two-pass mathematical selection on right click
            click_pos = event.position().toPoint()
            found = False
            
            # PASS 1: Area search for small items
            for item in self.items(click_pos.x() - 5, click_pos.y() - 5, 10, 10):
                etype = item.data(Qt.UserRole + 1)
                eid = item.data(Qt.UserRole)
                if etype in ["point_load", "line_load", "water_level"]:
                    self._state.set_selected_entity({"type": etype, "id": eid})
                    found = True
                    break
            
            # PASS 2: Mathematical hit test for polygons
            if not found:
                scene_pos = self.mapToScene(click_pos)
                polygons = self._state.polygons
                for i in range(len(polygons) - 1, -1, -1):
                    poly_data = polygons[i]
                    vertices = poly_data.get("vertices", [])
                    if len(vertices) < 3: continue
                    
                    qpoly = QPolygonF()
                    for v in vertices:
                        qpoly.append(QPointF(v["x"], v["y"]))
                    
                    if qpoly.containsPoint(scene_pos, Qt.OddEvenFill):
                        self._state.set_selected_entity({"type": "polygon", "index": i})
                        found = True
                        break

            # PASS 3: Beam Hit Test (Context Menu)
            if not found:
                beams = self._state.embedded_beams
                def dist_to_seg(p, x1, y1, x2, y2):
                    import math
                    L = math.hypot(x2-x1, y2-y1)
                    if L < 1e-9: return math.hypot(p.x()-x1, p.y()-y1)
                    t = ((p.x()-x1)*(x2-x1) + (p.y()-y1)*(y2-y1)) / (L*L)
                    t = max(0, min(1, t))
                    return math.hypot(p.x() - (x1 + t*(x2-x1)), p.y() - (y1 + t*(y2-y1)))

                scene_pos = self.mapToScene(click_pos)
                for b in beams:
                    if dist_to_seg(scene_pos, b["x1"], b["y1"], b["x2"], b["y2"]) < 0.2:
                        self._state.set_selected_entity({"type": "embedded_beam", "id": b["id"]})
                        found = True
                        break
            
            if not found:
                self._state.set_selected_entity(None)
            
            # Note: We still call super() for right-click so context menus work
            super().mousePressEvent(event)
            return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        """Handle pan dragging when middle mouse is held, and track coords."""
        scene_pos = self.mapToScene(event.position().toPoint())
        
        # Apply snapping to coordinates strictly for tooltip overlay
        settings = self._state.settings
        if settings.get("snap_to_grid", False):
            spacing = settings.get("grid_spacing", 1.0)
            if spacing <= 0: spacing = 1.0
            scene_pos.setX(round(scene_pos.x() / spacing) * spacing)
            scene_pos.setY(round(scene_pos.y() / spacing) * spacing)

        self._current_mouse_scene_pos = scene_pos
        self.viewport().update()

        if self._is_panning:
            delta = event.position() - self._pan_start
            self._pan_start = event.position()
            # Translate the view (scroll bars are hidden, so we adjust transform)
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - int(delta.x())
            )
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - int(delta.y())
            )
            event.accept()
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        """End panning on middle button release."""
        if event.button() == Qt.MiddleButton and self._is_panning:
            self._is_panning = False
            # Restore cursor to match current tool mode
            self._on_tool_mode_changed(self._state.tool_mode)
            event.accept()
            return

        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        """
        Double-click finalizes the current polygon in DRAW_POLYGON mode.
        """
        if event.button() == Qt.LeftButton:
            mode = self._state.tool_mode

            if mode == "DRAW_POLYGON":
                self._finalize_polygon()
                event.accept()
                return

        super().mouseDoubleClickEvent(event)

    def wheelEvent(self, event: QWheelEvent):
        """
        Zoom in/out centered on the mouse cursor.
        Uses angle delta (most mice emit 120 units per notch).
        """
        angle = event.angleDelta().y()
        if angle > 0:
            factor = ZOOM_FACTOR
        elif angle < 0:
            factor = 1.0 / ZOOM_FACTOR
        else:
            return

        self.scale(factor, factor)

    def keyPressEvent(self, event):
        """Handle Delete key, and Enter for polygons/water levels."""
        key = event.key()
        if key == Qt.Key_Delete:
            if self._state.active_tab in ["STAGING", "RESULT", "MESH"]:
                return  # Deletion disabled
                
            sel = self._state.selected_entity
            if not sel: return

            if sel.get("type") == "polygon":
                self._state.remove_polygon(sel.get("index"))
            elif sel.get("type") == "point_load":
                self._state.remove_point_load(sel.get("id"))
            elif sel.get("type") == "line_load":
                self._state.remove_line_load(sel.get("id"))
            elif sel.get("type") == "water_level":
                self._state.remove_water_level(sel.get("id"))
            elif sel.get("type") == "embedded_beam":
                self._state.remove_embedded_beam(sel.get("id"))
            
            self._state.set_selected_entity(None)
            event.accept()
            return

        elif key in [Qt.Key_Return, Qt.Key_Enter]:
            mode = self._state.tool_mode
            if mode == "DRAW_POLYGON":
                self._finalize_polygon()
            elif mode == "DRAW_WATER_LEVEL":
                self._finalize_water_level()
            elif mode == "DRAW_EMBEDDED_BEAM":
                # Esc/Cancel instead of and automatic finalize for beams which are 2-point only
                pass
            event.accept()
            return

        elif key == Qt.Key_Escape:
            if self._state.tool_mode in ["DRAW_POLYGON", "DRAW_RECTANGLE", "ADD_LINE_LOAD", "DRAW_WATER_LEVEL", "DRAW_EMBEDDED_BEAM"]:
                self._state.clear_drawing_points()
                event.accept()
                return

        super().keyPressEvent(event)

    # ==================================================================
    # Tool Handlers (Specific)
    # ==================================================================

    def _handle_add_point_load(self, pos: QPointF):
        import uuid
        load = {
            "id": str(uuid.uuid4())[:8],
            "x": pos.x(),
            "y": pos.y(),
            "fx": 0.0,
            "fy": -10.0 # Default 10kN down
        }
        self._state.add_point_load(load)

    def _handle_add_line_load(self, pos: QPointF):
        # Line load needs two points
        pts = self._state.drawing_points
        if not pts:
            self._state.add_drawing_point({"x": pos.x(), "y": pos.y()})
        else:
            import uuid
            p1 = pts[0]
            load = {
                "id": str(uuid.uuid4())[:8],
                "x1": p1["x"], "y1": p1["y"],
                "x2": pos.x(), "y2": pos.y(),
                "fx": 0.0, "fy": -10.0
            }
            self._state.clear_drawing_points()
            self._state.add_line_load(load)

    def _handle_draw_water_level_click(self, pos: QPointF):
        self._state.add_drawing_point({"x": pos.x(), "y": pos.y()})

    def _finalize_water_level(self):
        pts = self._state.drawing_points
        if len(pts) < 2:
            self._state.clear_drawing_points()
            return

        import uuid
        wl = {
            "id": str(uuid.uuid4())[:8],
            "name": f"Water Level {len(self._state.water_levels) + 1}",
            "points": list(pts)
        }
        self._state.clear_drawing_points()
        self._state.add_water_level(wl)

    def _handle_draw_beam_click(self, pos: QPointF):
        pts = self._state.drawing_points
        if not pts:
            self._state.add_drawing_point({"x": pos.x(), "y": pos.y()})
        else:
            p1 = pts[0]
            import uuid
            # Default material (first beam material)
            bm = self._state.beam_materials
            mid = bm[0].get("id") if bm else ""
            
            beam = {
                "id": str(uuid.uuid4())[:8],
                "x1": p1["x"], "y1": p1["y"],
                "x2": pos.x(), "y2": pos.y(),
                "materialId": mid,
                "head_point_index": 0,
                "head_connection_type": "FIXED"
            }
            self._state.clear_drawing_points()
            self._state.add_embedded_beam(beam)
            self._state.set_tool_mode("SELECT")

    # ==================================================================
    # Rendering Handlers
    # ==================================================================

    def _on_point_loads_changed(self, loads):
        # Clear old items
        for item in getattr(self, "_point_load_items", []):
            try: self._scene.removeItem(item)
            except: pass
        self._point_load_items = []

        pen_color = QColor("#ef4444")
        brush = QBrush(pen_color)
        
        sel = self._state.selected_entity
        sel_id = sel.get("id") if (sel and sel.get("type") == "point_load") else None

        # STAGING Logic
        is_staging = self._state.active_tab == "STAGING"
        current_phase = self._state.current_phase if is_staging else None

        import math
        for l in loads:
            px, py = l["x"], l["y"]
            fx, fy = l.get("fx", 0), -l.get("fy", 0) 
            lid = l.get("id")
            
            # Determine Color based on active state in staging
            is_active = True
            if is_staging and current_phase:
                active_ids = current_phase.get("active_load_ids", [])
                is_active = lid in active_ids
            
            draw_color = pen_color if is_active else QColor("#d4d4d8") # zinc-300
            if not is_active:
                draw_color.setAlpha(100)
            arrow_brush = QBrush(draw_color)

            # Use thicker pen if selected
            width = 2.5 if lid == sel_id else 0
            pen = QPen(draw_color, width)
            pen.setCosmetic(True)

            mag = math.sqrt(fx*fx + fy*fy)
            if mag < 1e-5: continue

            # Direction on screen: +y up in geo -> +y down in screen
            ux = fx / mag
            uy = -fy / mag # screen-space unit vector (ALWAYS -fy because screen y is inverted)
            
            arrow_len = 1.0
            tx = px - ux * arrow_len
            ty = py - uy * arrow_len
            
            # Arrow Body
            line = self._scene.addLine(tx, ty, px, py, pen)
            line.setZValue(150)
            line.setData(Qt.UserRole, lid)
            line.setData(Qt.UserRole + 1, "point_load")
            
            # Arrow head
            perp_x, perp_y = -uy, ux
            hw, hl = 0.2, 0.3
            head_pts = [
                QPointF(px, py),
                QPointF(px - ux * hl + perp_x * hw, py - uy * hl + perp_y * hw),
                QPointF(px - ux * hl - perp_x * hw, py - uy * hl - perp_y * hw)
            ]
            head_item = self._scene.addPolygon(QPolygonF(head_pts), pen, arrow_brush)
            head_item.setZValue(150)
            head_item.setData(Qt.UserRole, lid)
            head_item.setData(Qt.UserRole + 1, "point_load")
            
            self._point_load_items.extend([line, head_item])

    def _on_line_loads_changed(self, loads):
        for item in getattr(self, "_line_load_items", []):
            try: self._scene.removeItem(item)
            except: pass
        self._line_load_items = []

        pen_color = QColor("#f97316")
        brush = QBrush(pen_color)
        
        sel = self._state.selected_entity
        sel_id = sel.get("id") if (sel and sel.get("type") == "line_load") else None

        # STAGING Logic
        is_staging = self._state.active_tab == "STAGING"
        current_phase = self._state.current_phase if is_staging else None

        import math
        for l in loads:
            x1, y1 = l["x1"], l["y1"]
            x2, y2 = l["x2"], l["y2"]
            fx, fy = l.get("fx", 0), -l.get("fy", 0)
            lid = l.get("id")
            
            # Determine Color
            is_active = True
            if is_staging and current_phase:
                active_ids = current_phase.get("active_load_ids", [])
                is_active = lid in active_ids
            
            draw_color = pen_color if is_active else QColor("#d4d4d8")
            if not is_active:
                draw_color.setAlpha(100)
            arrow_brush = QBrush(draw_color)

            width = 2.5 if lid == sel_id else 0
            pen = QPen(draw_color, width)
            pen.setCosmetic(True)

            mag = math.sqrt(fx*fx + fy*fy)
            if mag < 1e-5:
                main_line = self._scene.addLine(x1, y1, x2, y2, pen)
                main_line.setZValue(140)
                main_line.setData(Qt.UserRole, lid)
                main_line.setData(Qt.UserRole + 1, "line_load")
                self._line_load_items.append(main_line)
                continue

            ux, uy = fx / mag, -fy / mag
            
            main_line = self._scene.addLine(x1, y1, x2, y2, pen)
            main_line.setZValue(140)
            main_line.setData(Qt.UserRole, lid)
            main_line.setData(Qt.UserRole + 1, "line_load")
            self._line_load_items.append(main_line)
            
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
                tick.setData(Qt.UserRole, lid)
                tick.setData(Qt.UserRole + 1, "line_load")
                
                head_pts = [
                    QPointF(px, py),
                    QPointF(px - ux * hl + perp_x * hw, py - uy * hl + perp_y * hw),
                    QPointF(px - ux * hl - perp_x * hw, py - uy * hl - perp_y * hw)
                ]
                head_item = self._scene.addPolygon(QPolygonF(head_pts), pen, arrow_brush)
                head_item.setZValue(140)
                head_item.setData(Qt.UserRole, lid)
                head_item.setData(Qt.UserRole + 1, "line_load")
                
                self._line_load_items.extend([tick, head_item])

    def _on_water_levels_changed(self, levels):
        for item in getattr(self, "_water_level_items", []):
            try: self._scene.removeItem(item)
            except: pass
        self._water_level_items = []

        pen_color = QColor("#3b82f6")
        sel = self._state.selected_entity
        sel_id = sel.get("id") if (sel and sel.get("type") == "water_level") else None

        # STAGING Logic
        is_staging = self._state.active_tab == "STAGING"
        current_phase = self._state.current_phase if is_staging else None

        for wl in levels:
            pts = wl.get("points", [])
            wlid = wl.get("id")
            
            # Determine color
            is_active = True
            if is_staging and current_phase:
                active_id = current_phase.get("active_water_level_id")
                is_active = wlid == active_id
            
            draw_color = pen_color if is_active else QColor("#d4d4d8")

            # Thick pen if selected
            width = 3.0 if wlid == sel_id else (0.5 if is_active else 0)
            pen = QPen(draw_color, width)
            pen.setStyle(Qt.DashLine)
            pen.setCosmetic(True)

            for i in range(len(pts) - 1):
                p1, p2 = pts[i], pts[i+1]
                line = self._scene.addLine(p1["x"], p1["y"], p2["x"], p2["y"], pen)
                line.setZValue(130)
                line.setData(Qt.UserRole, wlid)
                line.setData(Qt.UserRole + 1, "water_level")
                self._water_level_items.append(line)
                
                # Triangle at center of each segment
                mid_x = (p1["x"] + p2["x"]) / 2.0
                mid_y = (p1["y"] + p2["y"]) / 2.0
                tri = QPolygonF([
                    QPointF(mid_x - 0.3, mid_y+0.3),
                    QPointF(mid_x + 0.3, mid_y+0.3),
                    QPointF(mid_x, mid_y)
                ])
                # Semi-transparent brush
                tri_brush = QBrush(QColor(draw_color.red(), draw_color.green(), draw_color.blue(), 180)) # opacity ~0.7
                tri_item = self._scene.addPolygon(tri, QPen(Qt.NoPen), tri_brush)
                tri_item.setZValue(130)
                tri_item.setData(Qt.UserRole, wlid)
                tri_item.setData(Qt.UserRole + 1, "water_level")
                self._water_level_items.append(tri_item)

        # Ensure we respect the current tab visibility
        show_water = self._state.active_tab != "MESH"
        for item in self._water_level_items:
            item.setVisible(show_water)


    def contextMenuEvent(self, event):
        """
        Right-click context:
        - In DRAW_POLYGON mode: finalize the polygon
        - Otherwise: show context menu for polygons
        """
        mode = self._state.tool_mode

        if mode == "DRAW_POLYGON":
            self._finalize_polygon()
            event.accept()
            return
        elif mode == "DRAW_RECTANGLE":
            self._state.clear_drawing_points()
            event.accept()
            return
            
        if self._state.active_tab in ["STAGING", "RESULT", "MESH"]:
            # Context menu deletions are disabled in these modes
            return

        # Let the standard Selection grab the item underneath
        super().contextMenuEvent(event)

    # ==================================================================
    # Tool-specific handlers
    # ==================================================================

    def _handle_draw_polygon_click(self, scene_pos: QPointF):
        """
        Handle clicks while in DRAW_POLYGON or DRAW_RECTANGLE mode.
        """
        points = self._state.drawing_points
        mode = self._state.tool_mode

        if mode == "DRAW_RECTANGLE":
            if points: # Second click
                first_pt = points[0]
                pt1 = {"x": round(first_pt["x"], 4), "y": round(first_pt["y"], 4)}
                pt3 = {"x": round(scene_pos.x(), 4), "y": round(scene_pos.y(), 4)}
                pt2 = {"x": pt3["x"], "y": pt1["y"]}
                pt4 = {"x": pt1["x"], "y": pt3["y"]}
                
                # Replace points array with full 4 points
                self._state.add_drawing_point(pt2)
                self._state.add_drawing_point(pt3)
                self._state.add_drawing_point(pt4)
                
                self._finalize_polygon()
            else: # First click
                point = {"x": round(scene_pos.x(), 4), "y": round(scene_pos.y(), 4)}
                self._state.add_drawing_point(point)
            return
            
        # Standard polygon logic
        if points:
            first_pt = points[0]
            import math
            dist = math.hypot(scene_pos.x() - first_pt["x"], scene_pos.y() - first_pt["y"])
            # Snap radius equivalent to 0.5 units or so
            if len(points) >= 3 and dist < 0.5:
                self._finalize_polygon()
                return

        point = {"x": round(scene_pos.x(), 4), "y": round(scene_pos.y(), 4)}
        self._state.add_drawing_point(point)

    def _finalize_polygon(self):
        """
        Commit the temporary drawing points as a new polygon in
        ProjectState, then clear the drawing buffer.

        Requires at least 3 points to form a valid polygon.
        """
        points = self._state.drawing_points
        if len(points) < 3:
            # Not enough points — just clear and ignore
            self._state.clear_drawing_points()
            return

        # Determine default material id (first material or 'default')
        materials = self._state.materials
        default_mat_id = materials[0].get("id", "default") if materials else "default"

        # Create polygon dict matching the React PolygonData shape
        polygon = {
            "vertices": list(points),  # copy
            "materialId": default_mat_id,
        }

        # Commit to state (this emits polygons_changed → redraws)
        self._state.add_polygon(polygon)

        # Clear drawing buffer (this emits drawing_points_changed → removes temp items)
        self._state.clear_drawing_points()

        # Switch back to SELECT mode after finalizing
        self._state.set_tool_mode("SELECT")

    def _handle_add_point_load(self, scene_pos: QPointF):
        """
        ADD_POINT_LOAD mode: Place a point load at the clicked position.
        """
        load = {
            "id": f"load_{int(time.time() * 1000)}",
            "x": round(scene_pos.x(), 4),
            "y": round(scene_pos.y(), 4),
            "fx": 0.0,
            "fy": -100.0,  # Default downward force
        }
        self._state.add_point_load(load)

        # Switch back to SELECT after placing
        self._state.set_tool_mode("SELECT")

    # ==================================================================
    # Drag-and-Drop (Material assignment onto polygons)
    # ==================================================================

    def dragEnterEvent(self, event: QDragEnterEvent):
        """Accept drag if it carries a material ID."""
        from ui.explorer import MIME_MATERIAL_ID
        if event.mimeData().hasFormat(MIME_MATERIAL_ID):
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event: QDragMoveEvent):
        """Keep accepting while dragging over the canvas."""
        from ui.explorer import MIME_MATERIAL_ID
        if event.mimeData().hasFormat(MIME_MATERIAL_ID):
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event: QDropEvent):
        """
        Handle material drop onto a polygon.
        Hit-tests all polygon items to find which one the cursor is over,
        then assigns the dropped material ID to that polygon.
        """
        from ui.explorer import MIME_MATERIAL_ID
        if not event.mimeData().hasFormat(MIME_MATERIAL_ID):
            super().dropEvent(event)
            return

        # Extract material ID from MIME data
        material_id = bytes(
            event.mimeData().data(MIME_MATERIAL_ID)
        ).decode("utf-8")

        # Map drop position to scene coordinates
        scene_pos = self.mapToScene(event.position().toPoint())

        # Hit-test: check which polygon contains this point
        polygons = self._state.polygons
        for i, poly_data in enumerate(polygons):
            vertices = poly_data.get("vertices", [])
            if len(vertices) < 3:
                continue

            # Build a QPolygonF from vertices for containment check
            qpoly = QPolygonF()
            for v in vertices:
                qpoly.append(QPointF(v["x"], v["y"]))

            if qpoly.containsPoint(scene_pos, Qt.OddEvenFill):
                # Found the polygon — assign the material
                is_staging = self._state.active_tab == "STAGING"
                if is_staging:
                    self._state.update_phase_material(self._state.current_phase_index, i, material_id)
                else:
                    self._state.update_polygon(i, {"materialId": material_id})
                
                event.acceptProposedAction()
                return

        # Hit-test: check for Beams
        beams = self._state.embedded_beams
        def dist_to_seg(p, x1, y1, x2, y2):
            import math
            L = math.hypot(x2-x1, y2-y1)
            if L < 1e-9: return math.hypot(p.x()-x1, p.y()-y1)
            t = ((p.x()-x1)*(x2-x1) + (p.y()-y1)*(y2-y1)) / (L*L)
            t = max(0, min(1, t))
            return math.hypot(p.x() - (x1 + t*(x2-x1)), p.y() - (y1 + t*(y2-y1)))

        for b in beams:
            if dist_to_seg(scene_pos, b["x1"], b["y1"], b["x2"], b["y2"]) < 0.2:
                # Found the beam
                self._state.update_embedded_beam_material(b["id"], material_id)
                event.acceptProposedAction()
                return

        # Drop didn't land on any polygon — ignore
        event.ignore()
