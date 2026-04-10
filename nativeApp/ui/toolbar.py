import os
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QButtonGroup, QFrame,
    QGraphicsDropShadowEffect, QStyleOptionButton, QStyle
)
from PySide6.QtGui import QIcon, QColor, QPainter
from PySide6.QtCore import Qt, QSize, Signal, QPropertyAnimation, Property, QEasingCurve, QRect, QPointF
from core.state import ProjectState


class RotatingButton(QPushButton):
    """
    A QPushButton that can animate the rotation of its icon.
    Used for loading/generating states.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self._rotation_angle = 0.0
        self._is_spinning = False

        # Set up the indefinite rotation animation
        self._animation = QPropertyAnimation(self, b"rotation_angle")
        self._animation.setDuration(1200) # Slightly slower for a premium feel
        self._animation.setStartValue(0.0)
        self._animation.setEndValue(360.0)
        self._animation.setLoopCount(-1) # Infinite
        self._animation.setEasingCurve(QEasingCurve.Linear)

    def get_rotation_angle(self) -> float:
        return self._rotation_angle

    def set_rotation_angle(self, angle: float):
        self._rotation_angle = angle
        self.update()

    rotation_angle = Property(float, get_rotation_angle, set_rotation_angle)

    def set_spinning(self, spinning: bool):
        self._is_spinning = spinning
        if spinning:
            if self._animation.state() != QPropertyAnimation.Running:
                self._animation.start()
        else:
            self._animation.stop()
            self._rotation_angle = 0.0
            self.update()

    def paintEvent(self, event):
        # 1. Draw the button base using style options (keeps stylesheets working)
        # We clear the icon from the option so the standard style doesn't draw it.
        opt = QStyleOptionButton()
        self.initStyleOption(opt)
        opt.icon = QIcon() # Hide default icon from style painting
        
        painter = QPainter(self)
        self.style().drawControl(QStyle.CE_PushButton, opt, painter, self)

        # 2. Draw the icon manually with rotation
        icon = self.icon()
        if not icon.isNull():
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setRenderHint(QPainter.SmoothPixmapTransform)

            icon_size = self.iconSize()
            # Center the icon in the button rect
            rect = QRect(
                (self.width() - icon_size.width()) // 2,
                (self.height() - icon_size.height()) // 2,
                icon_size.width(),
                icon_size.height()
            )
            
            # Rotate around the center of the icon
            center = QPointF(rect.center())
            painter.translate(center)
            painter.rotate(self._rotation_angle)
            painter.translate(-center)

            icon.paint(painter, rect, Qt.AlignCenter)
            painter.end()

class TopToolBar(QWidget):
    """
    Horizontal toolbar strip at the top of the main window.
    Contains drawing tools, action buttons, and material management.
    """
    # Signals for communication with the main window / state
    tool_mode_changed = Signal(str)
    add_material_requested = Signal()
    mesh_generation_requested = Signal()
    solve_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(44)  # Slightly wider for breathing room

        # MUST enable this for QWidget to paint background from stylesheet
        self.setAttribute(Qt.WA_StyledBackground, True)

        # Styling: pure white island, rounded
        self.setStyleSheet("""
            QWidget {
                background-color: #ffffff;
                border: 1px solid #e4e4e7; /* zinc-200 */
                border-radius: 8px;
            }
            QPushButton {
                background: transparent;
                border: none;
                border-radius: 6px;
                color: #52525b; /* zinc-600 */
                padding: 6px;
            }
            QPushButton:hover {
                background-color: #f4f4f5; /* zinc-100 */
                color: #18181b;
            }
            QPushButton:checked {
                background-color: #eff6ff; /* blue-50 */
                color: #2563eb; /* blue-600 */
            }
        """)

        # Add a subtle drop shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 20))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)
        
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(6, 6, 6, 6)
        self._layout.setSpacing(4)

        self._state = ProjectState.instance()
        self._build_tools()

        # Connect to state
        self._state.active_tab_changed.connect(self._sync_active_tab)
        self._sync_active_tab(self._state.active_tab)

    def _build_tools(self):
        # Tool button group (exclusive)
        self._tool_group = QButtonGroup(self)
        self._tool_group.setExclusive(True)

        # Define tools: (label, mode_string, tooltip, icon_filename)
        tool_definitions = [
            ("",       "SELECT",             "Select and move objects", "select.svg"),
            ("",      "DRAW_POLYGON",       "Draw a soil/material region", "polygon.svg"),
            ("",      "DRAW_RECTANGLE",     "Draw a rectangular region", "square.svg"),
            ("",    "ADD_POINT_LOAD",     "Place a point load", "ptload.svg"),
            ("",    "ADD_LINE_LOAD",      "Draw a distributed line load", "lnload.svg"),
            ("",    "DRAW_WATER_LEVEL",   "Draw a water level polyline", "waterlevel.svg"),
            ("",      "DRAW_EMBEDDED_BEAM", "Draw an embedded beam element", "beam.svg"),
        ]

        self._tool_buttons = {}

        for label, mode, tooltip, icon_name in tool_definitions:
            btn = QPushButton()
            btn.setCheckable(True)
            btn.setToolTip(tooltip)
            btn.setFixedHeight(26)
            
            if icon_name:
                icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "icons", icon_name)
                if os.path.exists(icon_path):
                    btn.setIcon(QIcon(icon_path))
                    btn.setIconSize(QSize(18, 18))
            else:
                # If no icon, use very short text or abbreviation
                btn.setText(label[:4])
                font = btn.font()
                font.setPointSize(7)
                btn.setFont(font)

            btn.clicked.connect(lambda checked, m=mode: self.tool_mode_changed.emit(m))
            self._tool_group.addButton(btn)
            self._layout.addWidget(btn)
            self._tool_buttons[mode] = btn

        # Default: SELECT
        self._tool_buttons["SELECT"].setChecked(True)

        # ---- Separator ----
        self.sep = QFrame()
        self.sep.setFrameShape(QFrame.HLine)
        self.sep.setStyleSheet("border: none; background-color: #f4f4f5; min-height: 1px; max-height: 1px;")
        self._layout.addWidget(self.sep)

        # ---- Material Management ----
        self.btn_add_mat = QPushButton()
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "icons", "material.svg")
        if os.path.exists(icon_path):
            self.btn_add_mat.setIcon(QIcon(icon_path))
            self.btn_add_mat.setIconSize(QSize(18, 18))
        self.btn_add_mat.setToolTip("Create a new material (Ctrl+M)")
        self.btn_add_mat.setShortcut("Ctrl+M")
        self.btn_add_mat.setFixedHeight(28)
        self.btn_add_mat.clicked.connect(self.add_material_requested.emit)
        self._layout.addWidget(self.btn_add_mat)

        # ---- Separator ----
        self.sep2 = QFrame()
        self.sep2.setFrameShape(QFrame.HLine)
        self.sep2.setStyleSheet("border: none; background-color: #f4f4f5; min-height: 1px; max-height: 1px;")
        self._layout.addWidget(self.sep2)

        # ---- Actions ----
        self.btn_mesh = RotatingButton()
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "icons", "run.svg")
        if os.path.exists(icon_path):
            self.btn_mesh.setIcon(QIcon(icon_path))
            self.btn_mesh.setIconSize(QSize(18, 18))
        self.btn_mesh.setToolTip("Generate FEM mesh from geometry")
        self.btn_mesh.setFixedHeight(28)
        self.btn_mesh.clicked.connect(self.mesh_generation_requested.emit)
        
        font_sm = self.btn_mesh.font()
        font_sm.setPointSize(8)
        font_sm.setBold(True)
        self.btn_mesh.setFont(font_sm)
        self._layout.addWidget(self.btn_mesh)

        self.btn_solve = RotatingButton()
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "icons", "run.svg")
        if os.path.exists(icon_path):
            self.btn_solve.setIcon(QIcon(icon_path))
            self.btn_solve.setIconSize(QSize(18, 18))
        self.btn_solve.setToolTip("Run FEM analysis")
        self.btn_solve.setFixedHeight(28)
        self.btn_solve.setFont(font_sm)
        self.btn_solve.setStyleSheet("color: #059669;") # green-600
        self.btn_solve.clicked.connect(self.solve_requested.emit)
        self._layout.addWidget(self.btn_solve)

        # No stretch here to allow the widget to shrink to content height

    def _sync_active_tab(self, tab: str):
        # Hide/show tools based on Wizard active tab.
        # Reset visibility
        for mode, btn in self._tool_buttons.items():
            btn.setVisible(tab == "INPUT")
            
        self.sep.setVisible(tab == "INPUT")
        
        # Tools specific overrides
        self.btn_mesh.setVisible(tab == "MESH")
        
        self.btn_solve.setVisible(tab in ["STAGING", "RESULT"])
        
        # Materials available everywhere except MESH
        self.btn_add_mat.setVisible(tab != "MESH")
        self.sep2.setVisible(tab != "MESH")

        # Dynamically resize the widget to fit visible buttons
        self.adjustSize()

    def set_mesh_loading(self, is_loading: bool):
        """Update mesh button icon and state while generating."""
        self.btn_mesh.setEnabled(not is_loading)
        self.btn_mesh.set_spinning(is_loading)
        
        icon_name = "loading.svg" if is_loading else "run.svg"
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "icons", icon_name)
        
        if os.path.exists(icon_path):
            self.btn_mesh.setIcon(QIcon(icon_path))
        
        self.btn_mesh.setText("")
        self.adjustSize()
