# ui/output_panel.py
# ===========================================================================
# OutputPanel — Result selection and visualization controls
# ===========================================================================

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QComboBox, QSlider, QFrame, QPushButton
)
from PySide6.QtCore import Qt
from core.state import ProjectState, OutputType

class OutputPanel(QWidget):
    """
    Sidebar panel that allows users to choose which simulation result
    to visualize (Displacement, Stress, etc.) and scale deformations.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("OutputPanel")
        self._state = ProjectState.instance()

        self.setStyleSheet("""
            QWidget#OutputPanel {
                background-color: #ffffff;
                border-right: 1px solid #e4e4e7;
                border-bottom: 1px solid #e4e4e7;
            }
            .PanelHeader {
                font-weight: 600;
                font-size: 11px;
                color: #52525b;
                padding: 6px 10px;
                background-color: #fafafa;
                border-bottom: 1px solid #f4f4f5;
                text-align: left;
            }
            QLabel {
                font-size: 11px;
                color: #71717a;
            }
            QComboBox {
                font-size: 11px;
                padding: 4px;
                border: 1px solid #e4e4e7;
                border-radius: 4px;
                background: white;
            }
        """)
        
        self._init_ui()
        
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 1. Header
        header = QPushButton("Output View")
        header.setProperty("class", "PanelHeader")
        layout.addWidget(header)

        # 2. Controls Area
        controls_container = QWidget()
        controls_layout = QVBoxLayout(controls_container)
        controls_layout.setContentsMargins(10, 10, 10, 10)
        controls_layout.setSpacing(12)

        # Result Type Selection
        type_label = QLabel("Result Type")
        controls_layout.addWidget(type_label)

        self.type_combo = QComboBox()
        self.type_combo.addItem("Deformed Mesh", OutputType.DEFORMED_MESH)
        self.type_combo.addItem("Total Displacement", OutputType.DEFORMED_CONTOUR)
        self.type_combo.addItem("UX Displacement", OutputType.DEFORMED_CONTOUR_UX)
        self.type_combo.addItem("UY Displacement", OutputType.DEFORMED_CONTOUR_UY)
        self.type_combo.insertSeparator(4)
        self.type_combo.addItem("Stress Sigma 1", OutputType.SIGMA_1)
        self.type_combo.addItem("Stress Sigma 3", OutputType.SIGMA_3)
        self.type_combo.addItem("Effective Sigma 1", OutputType.SIGMA_1_EFF)
        self.type_combo.addItem("Effective Sigma 3", OutputType.SIGMA_3_EFF)
        self.type_combo.insertSeparator(9)
        self.type_combo.addItem("PWP Total", OutputType.PWP_TOTAL)
        self.type_combo.addItem("PWP Steady", OutputType.PWP_STEADY)
        self.type_combo.addItem("PWP Excess", OutputType.PWP_EXCESS)
        self.type_combo.insertSeparator(13)
        self.type_combo.addItem("Yield Status", OutputType.YIELD_STATUS)
        
        self.type_combo.currentIndexChanged.connect(self._on_type_changed)
        controls_layout.addWidget(self.type_combo)

        # Deformation Scale Container for conditional hiding
        self.scale_container = QWidget()
        scale_root_layout = QVBoxLayout(self.scale_container)
        scale_root_layout.setContentsMargins(0, 0, 0, 0)
        scale_root_layout.setSpacing(8)

        scale_label_layout = QHBoxLayout()
        scale_label_layout.addWidget(QLabel("Deformation Scale"))
        self.scale_val_lbl = QLabel("1.0x")
        self.scale_val_lbl.setStyleSheet("font-weight: 600; color: #3b82f6;")
        scale_label_layout.addStretch()
        scale_label_layout.addWidget(self.scale_val_lbl)
        scale_root_layout.addLayout(scale_label_layout)

        self.scale_slider = QSlider(Qt.Horizontal)
        self.scale_slider.setRange(0, 100) # 0 to 100x
        self.scale_slider.setValue(1)
        self.scale_slider.setTickInterval(10)
        self.scale_slider.setTickPosition(QSlider.TicksBelow)
        self.scale_slider.valueChanged.connect(self._on_scale_changed)
        scale_root_layout.addWidget(self.scale_slider)
        
        controls_layout.addWidget(self.scale_container)

        layout.addWidget(controls_container)
        layout.addStretch()

    def _on_type_changed(self, index):
        out_type = self.type_combo.currentData()
        if out_type:
            self._state.set_output_type(out_type)
            # Hide scale controls if not in Deformed Mesh mode
            self.scale_container.setVisible(out_type == OutputType.DEFORMED_MESH)

    def _on_scale_changed(self, value):
        # We allow 0.0 to 100.0 scale, mapped linearly for now
        scale = float(value)
        self.scale_val_lbl.setText(f"{scale:.1f}x")
        self._state.set_deformation_scale(scale)
