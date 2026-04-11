# ui/track_data_dialog.py
# ===========================================================================
# TrackDataDialog — Visualization of point tracking data curves
# ===========================================================================

import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas, NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QComboBox, 
    QLabel, QPushButton, QFrame, QWidget, QScrollArea,
    QCheckBox, QFileDialog
)
from PySide6.QtCore import Qt
import math
import numpy as np
from core.state import ProjectState

class TrackDataDialog(QDialog):
    """
    A professional, compact dialog for plotting tracked point data.
    Users can pick the tracked point and define custom X/Y axes.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Track Data Curves")
        self.setMinimumSize(1200, 800)
        self.setAttribute(Qt.WA_DeleteOnClose)
        
        self._state = ProjectState.instance()
        self._data_cache, self._phase_info = self._prepare_data()
        self._phase_checks = {} # Mapping phase_id -> QCheckBox
        
        self.setStyleSheet("""
            QDialog {
                background-color: #ffffff;
            }
            .Sidebar {
                background-color: #f8fafc;
                border-right: 1px solid #e2e8f0;
                min-width: 200px;
                max-width: 200px;
            }
            QLabel {
                font-size: 11px;
                color: #64748b;
                font-weight: 500;
                background-color: transparent;
            }
            QComboBox {
                background: white;
                border: 1px solid #cbd5e1;
                border-radius: 4px;
                padding: 4px;
                font-size: 11px;
            }
            QPushButton#CloseButton, QPushButton#ExportButton {
                background-color: #f1f5f9;
                border: 1px solid #cbd5e1;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 11px;
                font-weight: 600;
                color: #475569;
            }
            QPushButton#CloseButton:hover, QPushButton#ExportButton:hover {
                background-color: #e2e8f0;
            }
            QPushButton#ExportButton {
                border-color: #94a3b8;
                color: #334155;
            }
            QScrollArea {
                border: none;
                background: transparent;
            }
            QCheckBox {
                font-size: 11px;
                color: #475569;
            }
        """)
        
        self._init_ui()
        self._populate_controls()
        
        # Interaction State
        self._is_panning = False
        self._pan_start = None
        self._hover_ann = None
        
        # Connect Matplotlib events for direct interaction
        self.canvas.mpl_connect("scroll_event", self._on_scroll)
        self.canvas.mpl_connect("button_press_event", self._on_press)
        self.canvas.mpl_connect("button_release_event", self._on_release)
        self.canvas.mpl_connect("motion_notify_event", self._on_motion)
        
        self._on_selection_changed()

    def _prepare_data(self):
        """Flatten and group track data from all phases with calculated fields."""
        results = self._state.solver_results
        phases_list = self._state.phases
        
        # 1. Map phase durations and parent relationships
        durations = {} # phase_id -> total_steps
        parent_map = {} # phase_id -> parent_id
        phase_dict = {} # phase_id -> phase_obj
        
        for p in phases_list:
            pid = p.get("id")
            phase_dict[pid] = p
            parent_map[pid] = p.get("parent_id")
            
            # Get duration from results
            if pid in results and "track_data" in results[pid]:
                td = results[pid]["track_data"]
                if td:
                    sample_pid = list(td.keys())[0]
                    durations[pid] = len(td[sample_pid])
                else:
                    durations[pid] = 0
            else:
                durations[pid] = 0

        # 2. Calculate branch-aware global offsets
        # offset[pid] = sum of durations of all ancestors
        offsets = {}
        def get_offset(pid):
            if pid in offsets: return offsets[pid]
            parent_id = parent_map.get(pid)
            if not parent_id or parent_id not in phase_dict:
                offsets[pid] = 0
                return 0
            # Offset is the offset of the parent + the duration of the parent
            off = get_offset(parent_id) + durations.get(parent_id, 0)
            offsets[pid] = off
            return off

        for p in phases_list:
            get_offset(p.get("id"))

        # 3. Process data with offsets
        combined = {}
        phase_info = [] # List of (id, name)
        
        for phase in phases_list:
            pid_phase = phase.get("id")
            if pid_phase not in results:
                continue
                
            phase_res = results[pid_phase]
            track_data = phase_res.get("track_data", {})
            if not track_data:
                continue
            
            phase_info.append((pid_phase, phase.get("name", "Unnamed Phase")))
            offset = offsets.get(pid_phase, 0)
            
            for pid, steps in track_data.items():
                if pid not in combined:
                    combined[pid] = {}
                
                phase_steps = []
                for i, s in enumerate(steps):
                    entry = s.copy()
                    
                    # 1. Calculated Steps
                    entry["step_local"] = i + 1
                    entry["step_global"] = offset + i + 1
                    
                    # 2. Local vs Global Displacement
                    lux = entry.get("ux", 0)
                    luy = entry.get("uy", 0)
                    gux = entry.get("total_ux", 0)
                    guy = entry.get("total_uy", 0)
                    
                    entry["ux_local"] = lux
                    entry["uy_local"] = luy
                    entry["displacement_local_total"] = math.sqrt(lux**2 + luy**2)
                    
                    entry["ux_global"] = gux
                    entry["uy_global"] = guy
                    entry["displacement_global_total"] = math.sqrt(gux**2 + guy**2)
                    
                    entry["displacement_total"] = entry["displacement_global_total"]
                    
                    # 3. Principal Stresses for GP
                    if "sig_xx" in entry and "sig_yy" in entry:
                        sx = entry["sig_xx"]
                        sy = entry["sig_yy"]
                        txy = entry.get("sig_xy", 0)
                        
                        center = (sx + sy) / 2.0
                        radius = math.sqrt(((sx - sy) / 2.0)**2 + txy**2)
                        entry["sigma_1"] = center + radius
                        entry["sigma_3"] = center - radius
                        entry["q_von_mises"] = abs(sx - sy)
                    
                    phase_steps.append(entry)
                
                combined[pid][pid_phase] = phase_steps
                
        return combined, phase_info

    def _init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # --- Sidebar Controls ---
        sidebar = QWidget()
        sidebar.setProperty("class", "Sidebar")
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(12, 20, 12, 20)
        side_layout.setSpacing(15)
        
        side_layout.addWidget(QLabel("Tracked Point"))
        self.point_combo = QComboBox()
        self.point_combo.currentIndexChanged.connect(self._on_selection_changed)
        side_layout.addWidget(self.point_combo)
        
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background-color: #e2e8f0; border: none; height: 1px; background-color: transparent;")
        side_layout.addWidget(line)
        
        side_layout.addWidget(QLabel("X Axis"))
        self.x_axis_combo = QComboBox()
        self.x_axis_combo.currentIndexChanged.connect(self._on_selection_changed)
        side_layout.addWidget(self.x_axis_combo)
        
        side_layout.addWidget(QLabel("Y Axis"))
        self.y_axis_combo = QComboBox()
        self.y_axis_combo.currentIndexChanged.connect(self._on_selection_changed)
        side_layout.addWidget(self.y_axis_combo)
        
        line2 = QFrame()
        line2.setFrameShape(QFrame.HLine)
        line2.setStyleSheet("background-color: #e2e8f0; border: none; height: 1px; background-color: transparent;")
        side_layout.addWidget(line2)
        
        side_layout.addWidget(QLabel("Layout"))
        self.chk_invert_x = QCheckBox("Invert X Direction")
        self.chk_invert_x.toggled.connect(self._on_selection_changed)
        side_layout.addWidget(self.chk_invert_x)
        
        self.chk_invert_y = QCheckBox("Invert Y Direction")
        self.chk_invert_y.toggled.connect(self._on_selection_changed)
        side_layout.addWidget(self.chk_invert_y)

        line3 = QFrame()
        line3.setFrameShape(QFrame.HLine)
        line3.setStyleSheet("background-color: #e2e8f0; border: none; height: 1px; background-color: transparent;")
        side_layout.addWidget(line3)

        side_layout.addWidget(QLabel("Phases"))
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        self.phase_list_layout = QVBoxLayout(scroll_content)
        self.phase_list_layout.setContentsMargins(0, 0, 0, 0)
        self.phase_list_layout.setSpacing(5)
        
        scroll.setWidget(scroll_content)
        side_layout.addWidget(scroll, 1) # Give it stretch
        
        side_layout.addStretch()
        
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        
        self.btn_export = QPushButton("Export to CSV")
        self.btn_export.setObjectName("ExportButton")
        self.btn_export.clicked.connect(self._on_export_csv)
        btn_row.addWidget(self.btn_export, 1)
        
        self.btn_close = QPushButton("Close")
        self.btn_close.setObjectName("CloseButton")
        self.btn_close.clicked.connect(self.accept)
        btn_row.addWidget(self.btn_close)
        
        side_layout.addLayout(btn_row)
        
        main_layout.addWidget(sidebar)
        
        # --- Plot Area ---
        plot_container = QWidget()
        plot_layout = QVBoxLayout(plot_container)
        plot_layout.setContentsMargins(20, 20, 20, 20)
        
        self.figure = Figure(figsize=(5, 4), dpi=100, facecolor='#ffffff')
        self.canvas = FigureCanvas(self.figure)
        
        plot_layout.addWidget(self.canvas)
        
        main_layout.addWidget(plot_container)

    def _populate_controls(self):
        # Populate Points
        # Match ID to Label from state.tracked_points
        label_map = {p["id"]: p["label"] for p in self._state.tracked_points}
        data_pids = sorted(self._data_cache.keys())
        for pid in data_pids:
            label = label_map.get(pid, pid)
            self.point_combo.addItem(f"Point {label} ({pid})", pid)
            
        # Populate Axes (based on first available data point)
        if data_pids:
            first_pid = data_pids[0]
            if self._data_cache[first_pid]:
                # Identify point type (Node vs GP) to filter fields
                point_type = "node"
                for p in self._state.tracked_points:
                    if p["id"] == first_pid:
                        point_type = p.get("type", "node")
                        break
                
                # Filter categories
                general = ["step_global", "step_local", "m_stage"]
                node_only = [
                    "ux_local", "uy_local", "displacement_local_total",
                    "ux_global", "uy_global", "displacement_global_total"
                ]
                gp_only = [
                    "sig_xx", "sig_yy", "sig_xy", "sig_zz", "sigma_1", "sigma_3", 
                    "pwp_total", "pwp_excess", "pwp_steady",
                    "eps_xx", "eps_yy", "eps_xy"
                ]
                
                # Field to Label map with Units
                units = {
                    "ux_local": "(m)", "uy_local": "(m)", "displacement_local_total": "(m)",
                    "ux_global": "(m)", "uy_global": "(m)", "displacement_global_total": "(m)",
                    "sig_xx": "(kPa)", "sig_yy": "(kPa)", "sig_xy": "(kPa)", "sig_zz": "(kPa)",
                    "sigma_1": "(kPa)", "sigma_3": "(kPa)",
                    "pwp_total": "(kPa)", "pwp_excess": "(kPa)", "pwp_steady": "(kPa)",
                    "m_stage": "(-)"
                }
                
                # Get common keys from first phase of first point
                first_phase_id = list(self._data_cache[first_pid].keys())[0]
                all_keys = self._data_cache[first_pid][first_phase_id][0].keys()
                
                fields = []
                for k in general:
                    if k in all_keys: fields.append(k)
                for k in node_only:
                    if k in all_keys: fields.append(k)
                if point_type == "gp":
                    for k in gp_only:
                        if k in all_keys: fields.append(k)
                
                for f in fields:
                    label = f.replace("_", " ").title()
                    # Prettify common geotechnical terms
                    if "ux_local" in f: label = "Local Displacement Ux"
                    elif "uy_local" in f: label = "Local Displacement Uy"
                    elif "displacement_local_total" in f: label = "Local Total Displacement"
                    elif "ux_global" in f: label = "Global Displacement Ux"
                    elif "uy_global" in f: label = "Global Displacement Uy"
                    elif "displacement_global_total" in f: label = "Global Total Displacement"
                    elif f == "m_stage": label = "Multiplier (Mstage)"
                    elif f == "sigma_1": label = "Sigma 1 (Major)"
                    elif f == "sigma_3": label = "Sigma 3 (Minor)"
                    elif f == "pwp_total": label = "Total PWP"
                    elif f == "pwp_excess": label = "Excess PWP"
                    elif f == "pwp_steady": label = "Steady PWP"
                    
                    # Append unit
                    u = units.get(f, "")
                    if u: label += f" {u}"
                    
                    self.x_axis_combo.addItem(label, f)
                    self.y_axis_combo.addItem(label, f)
                
                # Defaults
                def_x = self.x_axis_combo.findData("step_global")
                if def_x >= 0: self.x_axis_combo.setCurrentIndex(def_x)
                
                y_target = "displacement_global_total" if point_type == "node" else "sigma_1"
                def_y = self.y_axis_combo.findData(y_target)
                if def_y < 0: def_y = self.y_axis_combo.findData("ux_global") 
                if def_y < 0: def_y = self.y_axis_combo.findData("ux") # Legacy fallback
                if def_y >= 0: self.y_axis_combo.setCurrentIndex(def_y)

        # Populate Phases
        for pid_phase, name in self._phase_info:
            chk = QCheckBox(name)
            chk.setChecked(True)
            chk.toggled.connect(self._on_selection_changed)
            self.phase_list_layout.addWidget(chk)
            self._phase_checks[pid_phase] = chk
        self.phase_list_layout.addStretch()

    def _on_selection_changed(self):
        pid = self.point_combo.currentData()
        x_field = self.x_axis_combo.currentData()
        y_field = self.y_axis_combo.currentData()
        
        if not pid or not x_field or not y_field:
            return
            
        point_phases = self._data_cache.get(pid, {})
        
        self.figure.clear()
        self._hover_ann = None
        ax = self.figure.add_subplot(111)
        
        # Color palette for phases
        colors = ['#3b82f6', '#ef4444', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899', '#06b6d4', '#71717a']
        
        # To handle continuity, search parent info
        phases_list = self._state.phases
        parent_map = {p.get("id"): p.get("parent_id") for p in phases_list}
        
        self._plot_curves = [] # Store lines for hover snap
        plotted_anything = False
        
        for i, (phase_id, phase_name) in enumerate(self._phase_info):
            if phase_id not in point_phases:
                continue
            
            # Check visibility
            if phase_id not in self._phase_checks:
                continue
            if not self._phase_checks[phase_id].isChecked():
                continue
                
            data = point_phases[phase_id]
            x_vals = [d.get(x_field, 0) for d in data]
            y_vals = [d.get(y_field, 0) for d in data]
            
            # CURVE CONTINUITY: 
            # If this phase has a parent and the parent is visible, prepend parent's last point
            parent_id = parent_map.get(phase_id)
            if parent_id and parent_id in self._phase_checks and self._phase_checks[parent_id].isChecked():
                parent_data = point_phases.get(parent_id, [])
                if parent_data:
                    last_pt = parent_data[-1]
                    x_vals.insert(0, last_pt.get(x_field, 0))
                    y_vals.insert(0, last_pt.get(y_field, 0))
            
            color = colors[i % len(colors)]
            line, = ax.plot(x_vals, y_vals, color=color, linewidth=1.5, marker='o', 
                           markersize=3, markerfacecolor='white', label=phase_name)
            self._plot_curves.append((line, phase_name, data))
            plotted_anything = True
            
        # Invert Directions
        if self.chk_invert_x.isChecked():
            ax.invert_xaxis()
        if self.chk_invert_y.isChecked():
            ax.invert_yaxis()
            
        ax.set_xlabel(self.x_axis_combo.currentText(), fontsize=9, color='#64748b', fontweight='bold')
        ax.set_ylabel(self.y_axis_combo.currentText(), fontsize=9, color='#64748b', fontweight='bold')
        
        if plotted_anything:
            ax.legend(fontsize=8, frameon=False, loc='best')
            
        ax.grid(True, linestyle='--', alpha=0.3)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color('#e2e8f0')
        ax.spines['bottom'].set_color('#e2e8f0')
        ax.tick_params(colors='#64748b', labelsize=8)
        
        self.figure.tight_layout()
        self.canvas.draw()

    def _on_scroll(self, event):
        """Handle zoom in/out with mouse wheel."""
        if not event.inaxes: return
        
        base_scale = 1.3
        scale_factor = 1.0 / base_scale if event.button == 'up' else base_scale
        
        ax = event.inaxes
        cur_xlim = ax.get_xlim()
        cur_ylim = ax.get_ylim()
        
        x_data = event.xdata
        y_data = event.ydata
        
        new_width = (cur_xlim[1] - cur_xlim[0]) * scale_factor
        new_height = (cur_ylim[1] - cur_ylim[0]) * scale_factor
        
        rel_x = (cur_xlim[1] - x_data) / (cur_xlim[1] - cur_xlim[0])
        rel_y = (cur_ylim[1] - y_data) / (cur_ylim[1] - cur_ylim[0])
        
        ax.set_xlim([x_data - new_width * (1-rel_x), x_data + new_width * rel_x])
        ax.set_ylim([y_data - new_height * (1-rel_y), y_data + new_height * rel_y])
        self.canvas.draw_idle()

    def _on_press(self, event):
        """Start panning on left-click."""
        if event.button == 1 and event.inaxes: # 1 = Left Click
            self._is_panning = True
            self._pan_start = (event.xdata, event.ydata)

    def _on_release(self, event):
        """Stop panning."""
        self._is_panning = False
        self._pan_start = None

    def _on_motion(self, event):
        """Handle both panning and hover tooltips."""
        if not event.inaxes:
            if self._hover_ann:
                self._hover_ann.set_visible(False)
                self.canvas.draw_idle()
            return

        # 1. Handle Panning
        if self._is_panning and self._pan_start:
            ax = event.inaxes
            dx = event.xdata - self._pan_start[0]
            dy = event.ydata - self._pan_start[1]
            
            # The trick for panning: subtract dx/dy from the current limits
            ax.set_xlim(ax.get_xlim() - dx)
            ax.set_ylim(ax.get_ylim() - dy)
            self.canvas.draw_idle()
            return

        # 2. Handle Hover Tooltip (Data Snapping)
        if not hasattr(self, "_plot_curves") or not self._plot_curves:
            return

        ax = event.inaxes
        closest_pt = None
        min_dist = float("inf")
        info_text = ""
        phase_col = ""

        for line, phase_name, raw_data in self._plot_curves:
            xdata = line.get_xdata()
            ydata = line.get_ydata()
            
            dists = np.sqrt((xdata - event.xdata)**2 + (ydata - event.ydata)**2)
            idx = np.argmin(dists)
            
            if dists[idx] < min_dist:
                min_dist = dists[idx]
                closest_pt = (xdata[idx], ydata[idx])
                phase_col = line.get_color()
                
                val_x = xdata[idx]
                val_y = ydata[idx]
                info_text = f"{phase_name}\nX: {val_x:.4g}\nY: {val_y:.4g}"

        xlim = ax.get_xlim()
        ylim = ax.get_ylim()
        thresh = 0.05 * max(abs(xlim[1]-xlim[0]), abs(ylim[1]-ylim[0]))

        if closest_pt and min_dist < thresh:
            if not self._hover_ann:
                self._hover_ann = ax.annotate(
                    "", xy=(0,0), xytext=(10,10),
                    textcoords="offset points",
                    bbox=dict(boxstyle="round", fc="white", ec=phase_col, alpha=0.9),
                    fontsize=8
                )
            
            self._hover_ann.set_text(info_text)
            self._hover_ann.xy = closest_pt
            self._hover_ann.get_bbox_patch().set_edgecolor(phase_col)
            self._hover_ann.set_visible(True)
            self.canvas.draw_idle()
        else:
            if self._hover_ann:
                self._hover_ann.set_visible(False)
                self.canvas.draw_idle()

    def _on_export_csv(self):
        """Export visible curves data to CSV format."""
        if not hasattr(self, "_plot_curves") or not self._plot_curves:
            return
            
        # Get point details for filename suggestion
        pid = self.point_combo.currentData()
        ptext = self.point_combo.currentText().split("(")[0].strip()
        
        # Save Dialog
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Track Data", 
            f"track_data_{pid}.csv", 
            "CSV Files (*.csv)"
        )
        if not path:
            return
            
        import csv
        x_field = self.x_axis_combo.currentData()
        y_field = self.y_axis_combo.currentData()
        x_label = self.x_axis_combo.currentText()
        y_label = self.y_axis_combo.currentText()
        
        try:
            with open(path, 'w', newline='') as f:
                writer = csv.writer(f)
                # Header: Phase, Step Local, X Field, Y Field
                writer.writerow(["Phase Name", "Step (Local)", f"X: {x_label}", f"Y: {y_label}"])
                
                # Data Rows
                for line, phase_name, raw_data in self._plot_curves:
                    for entry in raw_data:
                        writer.writerow([
                            phase_name,
                            entry.get("step_local", 0),
                            entry.get(x_field, 0.0),
                            entry.get(y_field, 0.0)
                        ])
            
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.information(self, "Export Successful", f"Data exported successfully to:\n{path}")
            
        except Exception as e:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Export Failed", f"Could not export data:\n{str(e)}")
