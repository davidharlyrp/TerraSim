# ui/material_dialog.py
# ===========================================================================
# MaterialDialog — QDialog for creating / editing geotechnical & structural materials
# ===========================================================================
# Features a two-tab interface to switch between Soil/Rock and Structural Beams.
# ===========================================================================

from __future__ import annotations
import time
import math
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QFormLayout,
    QLabel, QLineEdit, QDoubleSpinBox, QComboBox, QPushButton,
    QColorDialog, QGroupBox, QScrollArea, QWidget, QFrame,
    QSizePolicy, QListView, QTabWidget
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor


# Material model / drainage enums (matching backend models.py)
MATERIAL_MODELS = [
    ("linear_elastic",  "Linear Elastic"),
    ("mohr_coulomb",    "Mohr-Coulomb"),
    ("hoek_brown",      "Hoek-Brown (Rock)"),
]

DRAINAGE_TYPES = [
    ("drained",       "Drained"),
    ("undrained_a",   "Undrained A"),
    ("undrained_b",   "Undrained B"),
    ("undrained_c",   "Undrained C"),
    ("non_porous",    "Non Porous"),
]

# Default templates
DEFAULT_MATERIAL = {
    "id": "",
    "name": "New Material",
    "color": "#4CAF50",
    "material_model": "linear_elastic",
    "drainage_type": "non_porous",
    "youngsModulus": 30000.0,
    "effyoungsModulus": 30000.0,
    "poissonsRatio": 0.3,
    "unitWeightUnsaturated": 18.0,
    "unitWeightSaturated": 20.0,
    "cohesion": 0.0,
    "frictionAngle": 30.0,
    "undrainedShearStrength": 0.0,
    "dilationAngle": 0.0,
    "k0_x": None,
    "sigma_ci": 0.0,
    "gsi": 50.0,
    "mi": 10.0,
    "disturbFactor": 0.0,
    "m_b": None,
    "s": None,
    "a": None,
}

DEFAULT_BEAM_MATERIAL = {
    "id": "",
    "name": "New Beam Material",
    "color": "#2563EB",
    "youngsModulus": 200000000.0, # kN/m2
    "crossSectionArea": 0.01,    # m2
    "momentOfInertia": 0.0001,   # m4
    "unitWeight": 0.1,           # kN/m/m
    "spacing": 1.0,              # m
    "skinFrictionMax": 100.0,    # kN/m
    "tipResistanceMax": 500.0,   # kN
    "section_shape": "user_defined",
    "diameter": 0.5,
    "width": 0.4,
    "is_beam": True
}


def _create_spinbox(
    value=0.0, minimum=0.0, maximum=1e12,
    decimals=2, step=1.0, suffix: str = ""
) -> QDoubleSpinBox:
    """Helper to create a configured QDoubleSpinBox without step buttons."""
    sb = QDoubleSpinBox()
    sb.setRange(minimum, maximum)
    sb.setDecimals(decimals)
    sb.setSingleStep(step)
    if suffix:
        sb.setSuffix(f" {suffix}")
    sb.setButtonSymbols(QDoubleSpinBox.NoButtons)
    sb.setValue(value)
    sb.setFixedWidth(140)
    return sb


class MaterialDialog(QDialog):
    """
    Modal dialog for creating or editing materials (Soil or Beam).
    """

    material_saved = Signal(dict)

    def __init__(self, material: dict | None = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Material Properties")
        self.setMinimumSize(480, 550)
        self.resize(500, 650)
        self.setModal(True)

        # Detect material type
        self._is_editing = material is not None
        self._is_beam_mode = False
        
        if material:
            self._is_beam_mode = material.get("is_beam", False) or "crossSectionArea" in material

        # Working copy
        if self._is_beam_mode:
            self._data = dict(DEFAULT_BEAM_MATERIAL)
        else:
            self._data = dict(DEFAULT_MATERIAL)
            
        if material:
            self._data.update(material)

        # Generate ID if creating new
        if not self._data.get("id"):
            prefix = "bem" if self._is_beam_mode else "mat"
            self._data["id"] = f"{prefix}_{int(time.time() * 1000)}"

        self._build_ui()
        self._sync_ui_from_data()
        self._update_field_visibility()
        self._on_beam_shape_changed() # Always call to sync EBR visibility
        
        # If editing, lock the tab to prevent mode switching
        if self._is_editing:
            self._tabs.setTabEnabled(1 if not self._is_beam_mode else 0, False)
            self._tabs.setCurrentIndex(1 if self._is_beam_mode else 0)

    def _build_row(self, label_text: str, widget: QWidget, unit_text: str = "") -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        lbl = QLabel(label_text)
        lbl.setMinimumWidth(140)
        lbl.setMaximumWidth(140)
        lbl.setStyleSheet("font-size: 11px; color: #475569;")
        layout.addWidget(lbl)

        layout.addWidget(widget)

        unit_lbl = QLabel(unit_text if unit_text else "")
        unit_lbl.setMinimumWidth(60)
        unit_lbl.setStyleSheet("font-size: 10px; color: #94a3b8;")
        layout.addWidget(unit_lbl)

        layout.addStretch()
        return row

    def _force_light_dropdown(self, cmb: QComboBox):
        view = QListView()
        cmb.setView(view)
        cmb.setStyleSheet(
            "QComboBox { combobox-popup: 0; }"
            "QComboBox QAbstractItemView { background: #ffffff; color: #000000; border: 1px solid #ccc; }"
            "QComboBox QAbstractItemView::item { min-height: 24px; }"
            "QComboBox QAbstractItemView::item:selected { background: #e0e0e0; color: #000000; }"
        )

    def _build_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Top Row: Name and Color (Integrated)
        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(16, 8, 16, 4)
        top_layout.setSpacing(6)

        self._txt_name = QLineEdit()
        self._txt_name.setPlaceholderText("Material Name")
        self._txt_name.setFixedWidth(200)
        self._txt_name.setStyleSheet("""
            QLineEdit {
                border: 1px solid #e2e8f0;
                border-radius: 3px;
                padding: 2px 8px;
                font-size: 11px;
                background-color: #ffffff;
            }
            QLineEdit:focus { border: 1px solid #3b82f6; }
        """)
        top_layout.addWidget(self._txt_name)

        self._btn_color = QPushButton()
        self._btn_color.setFixedSize(18, 18)
        self._btn_color.setCursor(Qt.PointingHandCursor)
        self._btn_color.setStyleSheet("border-radius: 2px; border: 1px solid #cbd5e1;")
        self._btn_color.clicked.connect(self._pick_color)
        top_layout.addWidget(self._btn_color)
        
        self._lbl_color_hex = QLabel("#000000")
        self._lbl_color_hex.setStyleSheet("font-size: 10px; color: #94a3b8; font-family: 'Consolas', monospace;")
        top_layout.addWidget(self._lbl_color_hex)
        top_layout.addStretch()

        root_layout.addLayout(top_layout)

        # TABS
        self._tabs = QTabWidget()
        self._tabs.setStyleSheet("""
            QTabWidget::pane { border-top: 1px solid #f1f5f9; }
            QTabBar::tab {
                padding: 5px 14px;
                background: #f8fafc;
                border: 1px solid #f1f5f9;
                border-bottom: none;
                border-top-left-radius: 3px;
                border-top-right-radius: 3px;
                margin-right: 2px;
                font-size: 11px;
                color: #64748b;
            }
            QTabBar::tab:selected {
                background: white;
                border-bottom: 2px solid #3b82f6;
                color: #1e293b;
                font-weight: 600;
            }
        """)

        # Tab 1: Soil & Rock
        self._soil_scroll = QScrollArea()
        self._soil_scroll.setWidgetResizable(True)
        self._soil_scroll.setFrameShape(QFrame.NoFrame)
        soil_content = QWidget()
        self._soil_layout = QVBoxLayout(soil_content)
        self._soil_layout.setContentsMargins(16, 16, 16, 16)
        self._soil_layout.setSpacing(12)
        self._build_soil_fields()
        self._soil_scroll.setWidget(soil_content)
        self._tabs.addTab(self._soil_scroll, "Soil & Rock")

        # Tab 2: Embedded Beam
        self._beam_scroll = QScrollArea()
        self._beam_scroll.setWidgetResizable(True)
        self._beam_scroll.setFrameShape(QFrame.NoFrame)
        beam_content = QWidget()
        self._beam_layout = QVBoxLayout(beam_content)
        self._beam_layout.setContentsMargins(16, 16, 16, 16)
        self._beam_layout.setSpacing(12)
        self._build_beam_fields()
        self._beam_scroll.setWidget(beam_content)
        self._tabs.addTab(self._beam_scroll, "Embedded Beam")

        root_layout.addWidget(self._tabs)

        # Footer
        btn_container = QWidget()
        btn_container.setStyleSheet("background-color: #ffffff; border-top: 1px solid #d0d0d0;")
        btn_layout = QHBoxLayout(btn_container)
        btn_layout.setContentsMargins(16, 12, 16, 12)
        btn_layout.addStretch()
        
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)

        btn_save = QPushButton("Save Material")
        btn_save.setDefault(True)
        btn_save.clicked.connect(self._on_save)
        btn_save.setStyleSheet("background-color: #2563eb; color: white; border: none; font-weight: bold; padding: 6px 16px; border-radius: 4px;")
        btn_layout.addWidget(btn_save)

        root_layout.addWidget(btn_container)

    def _build_soil_fields(self):
        # Model & Drainage Group
        grp_model = QGroupBox("Analysis Model")
        model_layout = QVBoxLayout(grp_model)
        model_layout.setContentsMargins(12, 12, 12, 12)
        model_layout.setSpacing(8)

        self._cmb_model = QComboBox()
        self._cmb_model.setFixedWidth(140)
        self._force_light_dropdown(self._cmb_model)
        for val, label in MATERIAL_MODELS:
            self._cmb_model.addItem(label, val)
        self._cmb_model.currentIndexChanged.connect(self._on_model_changed)
        model_layout.addWidget(self._build_row("Constitutive Model", self._cmb_model))

        self._cmb_drainage = QComboBox()
        self._cmb_drainage.setFixedWidth(140)
        self._force_light_dropdown(self._cmb_drainage)
        self._cmb_drainage.currentIndexChanged.connect(self._on_drainage_changed)
        model_layout.addWidget(self._build_row("Drainage Behavior", self._cmb_drainage))
        self._soil_layout.addWidget(grp_model)

        # Physico-mechanical Group
        grp_stiff = QGroupBox("Stiffness & Weight")
        stiff_layout = QVBoxLayout(grp_stiff)
        stiff_layout.setContentsMargins(12, 12, 12, 12)
        stiff_layout.setSpacing(8)
        
        self._row_E = QWidget()
        self._row_E_layout = QVBoxLayout(self._row_E)
        self._row_E_layout.setContentsMargins(0, 0, 0, 0)
        self._spn_E = _create_spinbox(30000)
        self._row_E_layout.addWidget(self._build_row("Young's Modulus, E", self._spn_E, "kN/m²"))
        stiff_layout.addWidget(self._row_E)

        self._row_Eeff = QWidget()
        self._row_Eeff_layout = QVBoxLayout(self._row_Eeff)
        self._row_Eeff_layout.setContentsMargins(0, 0, 0, 0)
        self._spn_Eeff = _create_spinbox(30000)
        self._row_Eeff_layout.addWidget(self._build_row("Young's Modulus, E'", self._spn_Eeff, "kN/m²"))
        stiff_layout.addWidget(self._row_Eeff)

        self._spn_nu = _create_spinbox(0.3, 0, 0.499, 3)
        stiff_layout.addWidget(self._build_row("Poisson's Ratio, ν", self._spn_nu))

        self._spn_gamma = _create_spinbox(18.0)
        self._row_gamma = self._build_row("Unit Weight, γ", self._spn_gamma, "kN/m³")
        stiff_layout.addWidget(self._row_gamma)

        self._spn_gamma_sat = _create_spinbox(20.0)
        self._row_gamma_sat = self._build_row("Unit Weight Sat., γsat", self._spn_gamma_sat, "kN/m³")
        stiff_layout.addWidget(self._row_gamma_sat)
        self._soil_layout.addWidget(grp_stiff)

        # Strength Groups
        self._grp_mc_drained = QGroupBox("MC Drained Strength")
        mc_dl = QVBoxLayout(self._grp_mc_drained)
        mc_dl.setContentsMargins(12, 12, 12, 12)
        mc_dl.setSpacing(8)
        self._spn_c = _create_spinbox(0)
        mc_dl.addWidget(self._build_row("Cohesion, c'", self._spn_c, "kN/m²"))
        self._spn_phi = _create_spinbox(30, maximum=90)
        mc_dl.addWidget(self._build_row("Friction Angle, φ'", self._spn_phi, "°"))
        self._spn_psi = _create_spinbox(0, maximum=90)
        mc_dl.addWidget(self._build_row("Dilation Angle, ψ", self._spn_psi, "°"))
        self._spn_k0 = _create_spinbox(0.5, maximum=10, decimals=3)
        mc_dl.addWidget(self._build_row("Lateral Coeff., K₀", self._spn_k0))
        self._soil_layout.addWidget(self._grp_mc_drained)

        self._grp_mc_undrained = QGroupBox("MC Undrained Strength")
        mc_ul = QVBoxLayout(self._grp_mc_undrained)
        mc_ul.setContentsMargins(12, 12, 12, 12)
        mc_ul.setSpacing(8)
        self._spn_su = _create_spinbox(0)
        mc_ul.addWidget(self._build_row("Strength, Su", self._spn_su, "kN/m²"))
        self._spn_k0_u = _create_spinbox(0.5, maximum=10, decimals=3)
        mc_ul.addWidget(self._build_row("Lateral Coeff., K₀x", self._spn_k0_u))
        self._soil_layout.addWidget(self._grp_mc_undrained)

        self._grp_hb = QGroupBox("Hoek-Brown Rock")
        hb_layout = QVBoxLayout(self._grp_hb)
        hb_layout.setContentsMargins(12, 12, 12, 12)
        hb_layout.setSpacing(8)
        self._spn_sigma_ci = _create_spinbox(0)
        hb_layout.addWidget(self._build_row("UCS Rock, σci", self._spn_sigma_ci, "kN/m²"))
        self._spn_gsi = _create_spinbox(50, 0, 100, 0)
        self._spn_gsi.valueChanged.connect(self._recalc_hoek_brown)
        hb_layout.addWidget(self._build_row("GSI Index", self._spn_gsi))
        self._spn_mi = _create_spinbox(10, 1, 50, 0)
        self._spn_mi.valueChanged.connect(self._recalc_hoek_brown)
        hb_layout.addWidget(self._build_row("Intact Param., mi", self._spn_mi))
        self._spn_D = _create_spinbox(0, 0, 1, 2)
        self._spn_D.valueChanged.connect(self._recalc_hoek_brown)
        hb_layout.addWidget(self._build_row("Disturbance, D", self._spn_D))
        
        self._hb_results = QLabel("Derived: m_b=... s=... a=...")
        self._hb_results.setStyleSheet("color: #64748b; font-size: 11px;")
        hb_layout.addWidget(self._hb_results)
        self._soil_layout.addWidget(self._grp_hb)

        self._soil_layout.addStretch()

    def _build_beam_fields(self):
        grp_beam = QGroupBox("Embedded Beam Row Properties")
        beam_layout = QVBoxLayout(grp_beam)
        beam_layout.setContentsMargins(12, 12, 12, 12)
        beam_layout.setSpacing(8)

        # 1. Shape Selection
        self._cmb_section_shape = QComboBox()
        self._cmb_section_shape.setFixedWidth(140)
        self._force_light_dropdown(self._cmb_section_shape)
        self._cmb_section_shape.addItem("User Defined", "user_defined")
        self._cmb_section_shape.addItem("Circular", "circle")
        self._cmb_section_shape.addItem("Square", "square")
        self._cmb_section_shape.currentIndexChanged.connect(self._on_beam_shape_changed)
        beam_layout.addWidget(self._build_row("Section Shape", self._cmb_section_shape))

        # 2. Dimensions (Conditional)
        self._sb_beam_diameter = _create_spinbox(0.5, decimals=3, step=0.01)
        self._sb_beam_diameter.valueChanged.connect(self._recalc_beam_geometric_props)
        self._row_diameter = self._build_row("Diameter", self._sb_beam_diameter, "m")
        self._row_diameter.setVisible(False)
        beam_layout.addWidget(self._row_diameter)

        self._sb_beam_width = _create_spinbox(0.4, decimals=3, step=0.01)
        self._sb_beam_width.valueChanged.connect(self._recalc_beam_geometric_props)
        self._row_width = self._build_row("Width", self._sb_beam_width, "m")
        self._row_width.setVisible(False)
        beam_layout.addWidget(self._row_width)

        # 3. Calculated Properties
        self._spn_beam_E = _create_spinbox(2e8)
        beam_layout.addWidget(self._build_row("Young's Modulus, E", self._spn_beam_E, "kN/m²"))

        self._spn_beam_A = _create_spinbox(0.01, decimals=4)
        beam_layout.addWidget(self._build_row("Cross Section Area, A", self._spn_beam_A, "m²"))

        self._spn_beam_I = _create_spinbox(0.0001, decimals=6)
        beam_layout.addWidget(self._build_row("Moment of Inertia, I", self._spn_beam_I, "m⁴"))

        self._spn_beam_w = _create_spinbox(0.1, decimals=3)
        beam_layout.addWidget(self._build_row("Unit Weight, w", self._spn_beam_w, "kN/m/m"))

        self._spn_beam_spacing = _create_spinbox(1.0)
        beam_layout.addWidget(self._build_row("Beam Spacing, L", self._spn_beam_spacing, "m"))

        self._beam_layout.addWidget(grp_beam)

        grp_inter = QGroupBox("Skin Friction & Interaction")
        inter_layout = QVBoxLayout(grp_inter)
        inter_layout.setContentsMargins(12, 12, 12, 12)
        inter_layout.setSpacing(8)

        self._spn_beam_tmax = _create_spinbox(100.0)
        inter_layout.addWidget(self._build_row("Skin Friction, Tmax", self._spn_beam_tmax, "kN/m"))

        self._spn_beam_fmax = _create_spinbox(500.0)
        inter_layout.addWidget(self._build_row("Tip Resistance, Fmax", self._spn_beam_fmax, "kN"))

        self._beam_layout.addWidget(grp_inter)
        self._beam_layout.addStretch()

    # ==================================================================
    # Logic
    # ==================================================================

    def _sync_ui_from_data(self):
        d = self._data
        self._txt_name.setText(d.get("name", ""))
        self._update_color_button(d.get("color", "#4CAF50"))

        if self._is_beam_mode:
            self._spn_beam_E.setValue(d.get("youngsModulus", 2e8))
            self._spn_beam_A.setValue(d.get("crossSectionArea", 0.01))
            self._spn_beam_I.setValue(d.get("momentOfInertia", 0.0001))
            self._spn_beam_w.setValue(d.get("unitWeight", 0.1))
            self._spn_beam_spacing.setValue(d.get("spacing", 1.0))
            self._spn_beam_tmax.setValue(d.get("skinFrictionMax", 100.0))
            self._spn_beam_fmax.setValue(d.get("tipResistanceMax", 500.0))
            
            # New shape fields
            shape = d.get("section_shape", "user_defined")
            idx = self._cmb_section_shape.findData(shape)
            self._cmb_section_shape.setCurrentIndex(idx if idx >= 0 else 0)
            self._sb_beam_diameter.setValue(d.get("diameter", 0.5))
            self._sb_beam_width.setValue(d.get("width", 0.4))
        else:
            # Soil fields
            model = d.get("material_model", "linear_elastic")
            for i in range(self._cmb_model.count()):
                if self._cmb_model.itemData(i) == model:
                    self._cmb_model.setCurrentIndex(i)
                    break
            self._update_drainage_options()
            drainage = d.get("drainage_type", "non_porous")
            for i in range(self._cmb_drainage.count()):
                if self._cmb_drainage.itemData(i) == drainage:
                    self._cmb_drainage.setCurrentIndex(i)
                    break

            self._spn_E.setValue(d.get("youngsModulus", 30000))
            self._spn_Eeff.setValue(d.get("effyoungsModulus", 30000))
            self._spn_nu.setValue(d.get("poissonsRatio", 0.3))
            self._spn_gamma.setValue(d.get("unitWeightUnsaturated", 18.0))
            self._spn_gamma_sat.setValue(d.get("unitWeightSaturated", 20.0))
            self._spn_c.setValue(d.get("cohesion", 0))
            self._spn_phi.setValue(d.get("frictionAngle", 30))
            self._spn_psi.setValue(d.get("dilationAngle", 0))
            self._spn_k0.setValue(d.get("k0_x", 0.5) or 0.5)
            self._spn_su.setValue(d.get("undrainedShearStrength", 0))
            self._spn_k0_u.setValue(d.get("k0_x", 0.5) or 0.5)
            self._spn_sigma_ci.setValue(d.get("sigma_ci", 0))
            self._spn_gsi.setValue(d.get("gsi", 50))
            self._spn_mi.setValue(d.get("mi", 10))
            self._spn_D.setValue(d.get("disturbFactor", 0))
            self._recalc_hoek_brown()

    def _sync_data_from_ui(self):
        d = self._data
        d["name"] = self._txt_name.text().strip() or "Unnamed"
        
        if self._tabs.currentIndex() == 1:
            # BEAM MODE
            d["is_beam"] = True
            d["youngsModulus"] = self._spn_beam_E.value()
            d["crossSectionArea"] = self._spn_beam_A.value()
            d["momentOfInertia"] = self._spn_beam_I.value()
            d["unitWeight"] = self._spn_beam_w.value()
            d["spacing"] = self._spn_beam_spacing.value()
            d["skinFrictionMax"] = self._spn_beam_tmax.value()
            d["tipResistanceMax"] = self._spn_beam_fmax.value()
            d["section_shape"] = self._cmb_section_shape.currentData()
            d["diameter"] = self._sb_beam_diameter.value()
            d["width"] = self._sb_beam_width.value()
        else:
            # SOIL MODE
            d["is_beam"] = False
            d["material_model"] = self._cmb_model.currentData()
            d["drainage_type"] = self._cmb_drainage.currentData()
            if d["material_model"] == "linear_elastic" or d["drainage_type"] == "undrained_c":
                d["youngsModulus"] = self._spn_E.value()
            else:
                d["effyoungsModulus"] = self._spn_Eeff.value()
            d["poissonsRatio"] = self._spn_nu.value()
            d["unitWeightUnsaturated"] = self._spn_gamma.value()
            d["unitWeightSaturated"] = self._spn_gamma_sat.value()
            if d["material_model"] == "mohr_coulomb":
                if d["drainage_type"] in ("drained", "undrained_a"):
                    d["cohesion"] = self._spn_c.value()
                    d["frictionAngle"] = self._spn_phi.value()
                    d["dilationAngle"] = self._spn_psi.value()
                    d["k0_x"] = self._spn_k0.value()
                else:
                    d["undrainedShearStrength"] = self._spn_su.value()
                    d["k0_x"] = self._spn_k0_u.value()
            elif d["material_model"] == "hoek_brown":
                d["sigma_ci"] = self._spn_sigma_ci.value()
                d["gsi"] = self._spn_gsi.value()
                d["mi"] = self._spn_mi.value()
                d["disturbFactor"] = self._spn_D.value()

    def _on_beam_shape_changed(self):
        shape = self._cmb_section_shape.currentData()
        self._row_diameter.setVisible(shape == "circle")
        self._row_width.setVisible(shape == "square")
        
        is_user = (shape == "user_defined")
        self._spn_beam_A.setReadOnly(not is_user)
        self._spn_beam_I.setReadOnly(not is_user)
        
        # Style hint for read-only
        ro_style = "QDoubleSpinBox { background-color: #f8fafc; color: #64748b; border-color: #f1f5f9; }" if not is_user else "QDoubleSpinBox { background-color: #ffffff; color: #1e293b; border-color: #e2e8f0; }"
        self._spn_beam_A.setStyleSheet(ro_style)
        self._spn_beam_I.setStyleSheet(ro_style)
        
        self._recalc_beam_geometric_props()

    def _recalc_beam_geometric_props(self):
        shape = self._cmb_section_shape.currentData()
        if shape == "user_defined":
            return
            
        if shape == "circle":
            d = self._sb_beam_diameter.value()
            area = math.pi * (d/2)**2
            inertia = (math.pi * (d**4)) / 64.0
        else: # square
            w = self._sb_beam_width.value()
            area = w * w
            inertia = (w**4) / 12.0
            
        self._spn_beam_A.setValue(area)
        self._spn_beam_I.setValue(inertia)

    def _update_field_visibility(self):
        # Only relevant for Soil tab
        model = self._cmb_model.currentData()
        drainage = self._cmb_drainage.currentData()
        is_le = model == "linear_elastic"
        is_mc = model == "mohr_coulomb"
        is_hb = model == "hoek_brown"
        
        self._row_E.setVisible(is_le or drainage == "undrained_c")
        self._row_Eeff.setVisible(not (is_le or drainage == "undrained_c"))
        self._row_gamma_sat.setVisible(drainage != "non_porous")
        
        self._grp_mc_drained.setVisible(is_mc and drainage in ("drained", "undrained_a"))
        self._grp_mc_undrained.setVisible(is_mc and drainage in ("undrained_b", "undrained_c"))
        self._grp_hb.setVisible(is_hb)

    def _on_model_changed(self, _idx):
        self._update_drainage_options()
        self._update_field_visibility()

    def _on_drainage_changed(self, _idx):
        self._update_field_visibility()

    def _update_drainage_options(self):
        model = self._cmb_model.currentData()
        curr = self._cmb_drainage.currentData()
        self._cmb_drainage.blockSignals(True)
        self._cmb_drainage.clear()
        if model != "linear_elastic": self._cmb_drainage.addItem("Drained", "drained")
        if model == "mohr_coulomb":
            self._cmb_drainage.addItem("Undrained A", "undrained_a")
            self._cmb_drainage.addItem("Undrained B", "undrained_b")
            self._cmb_drainage.addItem("Undrained C", "undrained_c")
        if model in ["linear_elastic", "hoek_brown"]: self._cmb_drainage.addItem("Non Porous", "non_porous")
        idx = self._cmb_drainage.findData(curr)
        self._cmb_drainage.setCurrentIndex(idx if idx >= 0 else 0)
        self._cmb_drainage.blockSignals(False)

    def _pick_color(self):
        current = QColor(self._data.get("color", "#4CAF50"))
        color = QColorDialog.getColor(current, self, "Material Color")
        if color.isValid():
            self._data["color"] = color.name()
            self._update_color_button(color.name())

    def _update_color_button(self, hex_color: str):
        self._btn_color.setStyleSheet(f"background-color: {hex_color}; border: 1px solid #000; border-radius: 4px;")
        self._lbl_color_hex.setText(hex_color)

    def _recalc_hoek_brown(self):
        gsi, mi, D = self._spn_gsi.value(), self._spn_mi.value(), self._spn_D.value()
        try:
            mb = mi * math.exp((gsi - 100) / (28 - 14 * D))
            s = math.exp((gsi-100)/(9-3*D))
            a = 0.5 + (1/6)*(math.exp(-gsi/15)-math.exp(-20/3))
            self._hb_results.setText(f"Derived: mb={mb:.3f}  s={s:.4f}  a={a:.3f}")
        except: pass

    def _on_save(self):
        self._sync_data_from_ui()
        self.material_saved.emit(dict(self._data))
        self.accept()
