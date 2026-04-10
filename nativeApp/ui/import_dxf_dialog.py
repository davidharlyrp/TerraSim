from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QComboBox, QCheckBox, QPushButton, QFrame, 
    QGraphicsView, QGraphicsScene, QGraphicsPolygonItem,
    QListView
)
from PySide6.QtCore import Qt, QSize, QPointF
from PySide6.QtGui import QColor, QPen, QBrush, QPolygonF, QPainter
from core.dxf_parser import extract_polygons_from_dxf, get_dxf_units

class DXFImportDialog(QDialog):
    """
    A wizard-style dialog to configure DXF import settings
    and preview the geometry before committing to state.
    """
    def __init__(self, dxf_path: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Import DXF Geometry")
        self.setMinimumSize(480, 520)
        self._dxf_path = dxf_path
        self._final_polygons = []
        self._delete_existing = False
        
        # Unit mappings: label -> scale factor (to meters)
        self._unit_factors = {
            "m (Meters)": 1.0,
            "cm (Centimeters)": 0.01,
            "mm (Millimeters)": 0.001,
            "in (Inches)": 0.0254,
            "ft (Feet)": 0.3048
        }
        
        self.setStyleSheet("""
            QDialog { background-color: #ffffff; }
            .SectionHeader { font-weight: 600; font-size: 11px; color: #71717a; margin-top: 10px; }
            QGraphicsView { border: 1px solid #e4e4e7; border-radius: 4px; background-color: #fafafa; }
            QPushButton#ImportBtn { background-color: #18181b; color: white; border-radius: 6px; padding: 6px 16px; font-weight: 600; }
            QPushButton#CancelBtn { background-color: #f4f4f5; color: #18181b; border-radius: 6px; padding: 6px 16px; }
            QComboBox { padding: 4px; border: 1px solid #e4e4e7; border-radius: 4px; }
        """)

        self._init_ui()
        self._detect_initial_units()
        self._update_preview()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        # 1. Units Section
        lbl_unit = QLabel("Source File units")
        lbl_unit.setProperty("class", "SectionHeader")
        layout.addWidget(lbl_unit)
        
        self.unit_cmb = QComboBox()
        self.unit_cmb.setView(QListView())
        self.unit_cmb.addItems(list(self._unit_factors.keys()))
        self.unit_cmb.currentIndexChanged.connect(self._update_preview)
        layout.addWidget(self.unit_cmb)

        # 2. Options Section
        lbl_opt = QLabel("Options")
        lbl_opt.setProperty("class", "SectionHeader")
        layout.addWidget(lbl_opt)
        
        self.delete_cb = QCheckBox("Delete all current polygons")
        self.delete_cb.setChecked(False)
        layout.addWidget(self.delete_cb)

        # 3. Preview Section
        lbl_prev = QLabel("Geometry Preview")
        lbl_prev.setProperty("class", "SectionHeader")
        layout.addWidget(lbl_prev)
        
        self.scene = QGraphicsScene()
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.Antialiasing)
        layout.addWidget(self.view, 1) # Stretch

        # 4. Buttons Section
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("CancelBtn")
        self.cancel_btn.clicked.connect(self.reject)
        
        self.import_btn = QPushButton("Import Geometry")
        self.import_btn.setObjectName("ImportBtn")
        self.import_btn.clicked.connect(self._on_confirm_import)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.import_btn)
        layout.addLayout(btn_layout)

    def _detect_initial_units(self):
        """Auto-detect units from DXF header."""
        detected = get_dxf_units(self._dxf_path)
        # Attempt to map 'mm' -> 'mm (Millimeters)', etc.
        for i in range(self.unit_cmb.count()):
            text = self.unit_cmb.itemText(i)
            if text.startswith(detected):
                self.unit_cmb.setCurrentIndex(i)
                break

    def _update_preview(self):
        """Extract polygons with current scale and draw them."""
        self.scene.clear()
        
        unit_text = self.unit_cmb.currentText()
        scale = self._unit_factors.get(unit_text, 1.0)
        
        self._final_polygons = extract_polygons_from_dxf(self._dxf_path, scale)
        
        if not self._final_polygons:
            self.scene.addText("No closed polylines found in file.")
            return

        pen = QPen(QColor("#18181b"), 1)
        pen.setCosmetic(True) # Line width stays constant when zooming
        brush = QBrush(QColor(161, 161, 170, 80)) # zinc-400 with alpha

        for poly in self._final_polygons:
            qpoly = QPolygonF()
            for v in poly:
                qpoly.append(QPointF(v["x"], -v["y"])) # Negate Y for geo coords -> view coords
            
            item = QGraphicsPolygonItem(qpoly)
            item.setPen(pen)
            item.setBrush(brush)
            self.scene.addItem(item)
            
        # Manually calculate combined rect for better zooming
        self.view.setSceneRect(self.scene.itemsBoundingRect())
        self.view.fitInView(self.scene.itemsBoundingRect(), Qt.KeepAspectRatio)

    def _on_confirm_import(self):
        self._delete_existing = self.delete_cb.isChecked()
        self.accept()

    def get_import_data(self):
        """Returns (polygons_list, delete_existing_bool)"""
        return self._final_polygons, self._delete_existing
