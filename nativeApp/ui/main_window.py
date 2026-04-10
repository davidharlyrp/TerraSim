# ui/main_window.py
# ===========================================================================
# MainWindow — Primary Application Shell
# ===========================================================================
# Layout:
#   ┌─────────────────────────────────────────────────┐
#   │                  TOOLBAR (top)                   │
#   ├──────────┬──────────────────────────────────────┤
#   │ EXPLORER │                                      │
#   │  (left)  │           CANVAS (center)            │
#   │ polygons │                                      │
#   │ materials│                                      │
#   ├──────────┴──────────────────────────────────────┤
#   │                 CONSOLE LOG (bottom)            │
#   └─────────────────────────────────────────────────┘
# ===========================================================================

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QPlainTextEdit, QSplitter, QLabel,
    QButtonGroup, QFrame, QSizePolicy, QToolBar,
    QFileDialog
)
from PySide6.QtCore import (Qt, QSize)
from PySide6.QtGui import QIcon
import os

from api.workers import MeshWorker, SolveWorker
from core.state import ProjectState
from ui.canvas import TerraSimCanvas
from ui.preferences_dialog import PreferencesDialog
from ui.settings_dialog import SettingsDialog
from ui.explorer import BrowserExplorer
from ui.material_dialog import MaterialDialog
from ui.wizard_tabs import WizardTabs
from ui.properties_sidebar import PropertiesSidebar
from ui.console import TerraSimConsole
from ui.mesh_bar import MeshBar
from ui.staging_bar import StagingBar
from ui.run_dialog import SolveRunDialog
from ui.staging_sidebar import StagingSidebar
from ui.result_canvas import ResultCanvas
from ui.output_panel import OutputPanel
from core.samples import SAMPLE_FOUNDATION, SAMPLE_RETAINING_WALL


class MainWindow(QMainWindow):
    """
    Top-level window for the TerraSim native desktop application.
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("TerraSim 0.5.1 Beta - Geotechnical Finite Element Analysis")
        self.resize(1200, 800)

        # Project state (singleton)
        self.state = ProjectState.instance()

        # Active background workers (prevent garbage collection)
        self._mesh_worker: MeshWorker | None = None
        self._solve_worker: SolveWorker | None = None
        self._solve_dialog: SolveRunDialog | None = None
        
        # Persistence handling
        from core.persistence_manager import PersistenceManager
        self._persistence = PersistenceManager(self)

        # Build the UI
        self._init_ui()

        # Connect state signals to console logging
        self.state.tool_mode_changed.connect(self._on_tool_mode_changed)
        self.state.polygons_changed.connect(self._on_polygons_changed)
        self.state.point_loads_changed.connect(self._on_point_loads_changed)
        self.state.materials_changed.connect(self._on_materials_changed)
        self.state.active_tab_changed.connect(self._on_tab_changed)
        self.state.project_name_changed.connect(self._update_window_title)
        self.state.state_changed.connect(self._update_window_title)
        self.state.solver_response_changed.connect(self._update_tab_safety)

        # Connect explorer signals
        self.explorer.edit_material_requested.connect(self._on_edit_material)
        self.explorer.delete_material_requested.connect(self._on_delete_material)
        self.explorer.edit_beam_material_requested.connect(self._on_edit_beam_material)
        self.explorer.delete_beam_material_requested.connect(self._on_delete_beam_material)
        self.explorer.delete_polygon_requested.connect(self._on_delete_polygon)
        self.explorer.delete_beam_requested.connect(self._on_delete_beam)

        # Initial Tab Safety Check
        self._update_tab_safety()

    # ==================================================================
    # UI Construction
    # ==================================================================

    def _init_ui(self):
        """Build the main layout: toolbar (top) + explorer|canvas + console."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- 1. WIZARD TABS (Top) ---
        self.wizard_tabs = WizardTabs()
        main_layout.addWidget(self.wizard_tabs)

        # Separator (Batas Gap yang Tegas)
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background-color: #d4d4d8; border: none;")
        main_layout.addWidget(sep)

        # --- Vertical splitter: workspace (top) | console (bottom) ---
        v_splitter = QSplitter(Qt.Vertical)

        # --- Horizontal splitter: explorer (left) | canvas (right) ---
        h_splitter = QSplitter(Qt.Horizontal)

        # --- 2. LEFT SIDEBAR (Explorer + OutputView) ---
        self.left_splitter = QSplitter(Qt.Vertical)
        self.left_splitter.setHandleWidth(1)
        self.left_splitter.setStyleSheet("QSplitter::handle { background-color: #e4e4e7; }")

        self.output_panel = OutputPanel()
        self.output_panel.setVisible(False)
        self.left_splitter.addWidget(self.output_panel)

        self.explorer = BrowserExplorer()
        self.explorer.setMinimumWidth(140)
        self.left_splitter.addWidget(self.explorer)

        h_splitter.addWidget(self.left_splitter)

        # --- 3. CENTER COLUMN (MeshBar + Canvas) ---
        center_container = QWidget()
        center_layout = QVBoxLayout(center_container)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(0)
        
        self.mesh_bar = MeshBar()
        self.mesh_bar.setVisible(False)
        center_layout.addWidget(self.mesh_bar)

        self.staging_bar = StagingBar()
        self.staging_bar.setVisible(False)
        # Button moved to toolbar
        center_layout.addWidget(self.staging_bar)
        
        self.canvas = TerraSimCanvas()
        center_layout.addWidget(self.canvas)

        self.result_canvas = ResultCanvas()
        self.result_canvas.setVisible(False)
        center_layout.addWidget(self.result_canvas)

        # --- 4. FLOATING TOOLBAR ---
        from ui.toolbar import TopToolBar
        self.toolbar_widget = TopToolBar(parent=self.canvas)
        # We don't add it to a layout, it's absolutely positioned in the canvas

        # Connect toolbar signals
        self.toolbar_widget.tool_mode_changed.connect(self._on_tool_button_clicked)
        self.toolbar_widget.add_material_requested.connect(self._on_add_material_clicked)
        self.toolbar_widget.mesh_generation_requested.connect(self._on_generate_mesh_clicked)
        self.toolbar_widget.solve_requested.connect(self._on_run_analysis_clicked)
        
        # --- 5. PROPERTIES & STAGING PANEL (Right) ---
        self.right_splitter = QSplitter(Qt.Vertical)
        self.right_splitter.setHandleWidth(1)
        self.right_splitter.setStyleSheet("QSplitter::handle { background-color: #e4e4e7; }")

        self.staging_sidebar = StagingSidebar()
        self.staging_sidebar.setVisible(False)
        self.right_splitter.addWidget(self.staging_sidebar)

        self.properties = PropertiesSidebar()
        self.right_splitter.addWidget(self.properties)
        
        # --- 6. CONSOLE LOG (Bottom) ---
        self.console = TerraSimConsole(self)
        self.state.log_message.connect(self.console.log)
        self._log("TerraSim Initialized. Waiting for inputs...")

        # Assemble splitters: [Left Splitter | Center | Right Splitter]
        h_splitter.addWidget(center_container)
        h_splitter.addWidget(self.right_splitter)
        
        # Set proportions: Left (200), Canvas (Stretch), Right (240)
        h_splitter.setSizes([200, 800, 240])
        h_splitter.setStretchFactor(0, 0) # Left Sidebar
        h_splitter.setStretchFactor(1, 1) # Canvas
        h_splitter.setStretchFactor(2, 0) # Right Sidebar

        # Set initial vertical proportions WITHIN splitters
        self.left_splitter.setSizes([300, 500])
        self.right_splitter.setSizes([300, 500])

        v_splitter.addWidget(h_splitter)
        v_splitter.addWidget(self.console)
        v_splitter.setSizes([600, 200])

        main_layout.addWidget(v_splitter)

        # Create menus now that all components exist
        self._create_menus()

    def _create_menus(self):
        """Build the top menu bar (File, Edit, View, etc.)."""
        # Create standard menus
        menu_bar = self.menuBar()
        menu_bar.setNativeMenuBar(False) # Ensures cross-platform consistency

        # File Menu
        file_menu = menu_bar.addMenu("File")
        
        action_new = file_menu.addAction("New Project")
        action_new.setShortcut("Ctrl+N")
        action_new.triggered.connect(self._persistence.handle_new)
        
        action_open = file_menu.addAction("Open Project...")
        action_open.setShortcut("Ctrl+O")
        action_open.triggered.connect(self._persistence.handle_open)
        
        file_menu.addSeparator()
        
        action_save = file_menu.addAction("Save Project")
        action_save.setShortcut("Ctrl+S")
        action_save.triggered.connect(self._persistence.handle_save)
        
        action_save_as = file_menu.addAction("Save Project As...")
        action_save_as.setShortcut("Ctrl+Shift+S")
        action_save_as.triggered.connect(self._persistence.handle_save_as)
        
        file_menu.addSeparator()
        
        action_import = file_menu.addAction("Import Geometry...")
        action_import.setShortcut("Ctrl+I")
        action_import.triggered.connect(self._on_import_geometry)
        action_export = file_menu.addAction("Export Geometry...")
        action_export.setShortcut("Ctrl+E")
        action_export.triggered.connect(self._on_export_geometry)
        
        file_menu.addSeparator()
        # Sample Project Submenu
        sample_menu = file_menu.addMenu("Load Sample Project")
        action_sample_found = sample_menu.addAction("Shallow Foundation")
        action_sample_found.triggered.connect(self._load_sample_foundation)
        action_sample_wall = sample_menu.addAction("Retaining Wall")
        action_sample_wall.triggered.connect(self._load_sample_retaining_wall)
        
        file_menu.addSeparator()
        action_exit = file_menu.addAction("Exit")
        action_exit.triggered.connect(self.close)


        # Edit Menu
        edit_menu = menu_bar.addMenu("Edit")
        action_undo = edit_menu.addAction("Undo")
        action_undo.setShortcut("Ctrl+Z")
        action_undo.triggered.connect(lambda: self.state.undo())
        
        action_redo = edit_menu.addAction("Redo")
        action_redo.setShortcut("Ctrl+Shift+Z")
        action_redo.triggered.connect(lambda: self.state.redo())
        edit_menu.addSeparator()
        action_settings = edit_menu.addAction("Preferences")
        action_settings.triggered.connect(self._on_open_preferences)

        # View Menu
        view_menu = menu_bar.addMenu("View")
        action_zoom_in = view_menu.addAction("Zoom In")
        action_zoom_in.setShortcut("Ctrl+=")
        action_zoom_in.triggered.connect(self.canvas.zoom_in)
        action_zoom_out = view_menu.addAction("Zoom Out")
        action_zoom_out.setShortcut("Ctrl+-")
        action_zoom_out.triggered.connect(self.canvas.zoom_out)
        action_zoom_fit = view_menu.addAction("Zoom to Fit")
        action_zoom_fit.setShortcut("Ctrl+0")
        action_zoom_fit.triggered.connect(self.canvas.zoom_fit)
        view_menu.addSeparator()
        action_settings = view_menu.addAction("View Settings")
        action_settings.triggered.connect(self._on_open_settings)
        

        # Windows Menu
        windows_menu = menu_bar.addMenu("Windows")
        action_explorer = windows_menu.addAction("Explorer")
        action_explorer.setCheckable(True)
        action_explorer.setChecked(True)
        action_explorer.toggled.connect(self.explorer.setVisible)
        action_properties = windows_menu.addAction("Properties")
        action_properties.setCheckable(True)
        action_properties.setChecked(True)
        action_properties.toggled.connect(self.properties.setVisible) # Toggle the child itself
        action_console = windows_menu.addAction("Console")
        action_console.setCheckable(True)
        action_console.setChecked(True)
        action_console.toggled.connect(self.console.setVisible)

        # Help Menu
        help_menu = menu_bar.addMenu("Help")
        action_about = help_menu.addAction("About TerraSim")
        action_license = help_menu.addAction("License")
        manual_menu = help_menu.addAction("Manual")
        help_menu.addSeparator()
        action_feedback = help_menu.addAction("Feedback / Report Bug")
        help_menu.addSeparator()
        action_daharengineer = help_menu.addAction("Dahar Engineer")


    def _on_open_preferences(self):
        """Open the simulation parameters dialog."""
        dlg = PreferencesDialog(self)
        dlg.exec()

    def _on_open_settings(self):
        """Open the viewing/UI settings dialog."""
        dlg = SettingsDialog(self)
        dlg.exec()

    # ==================================================================
    # Tool button handlers
    # ==================================================================

    def _update_tab_safety(self, _=None):
        """Enable 'RESULT' tab only if simulation results are available."""
        # Use the underlying dictionary of results
        res = self.state._solver_results
        has_results = res is not None and len(res) > 0
        self.wizard_tabs.set_tab_enabled("RESULT", has_results)

    def _on_tab_changed(self, tab: str):
        """Update UI elements when a wizard tab is selected."""
        # 1. Toggle Task-specific Toolbars & Canvases
        is_result = tab == "RESULT"
        
        self.mesh_bar.setVisible(tab == "MESH")
        self.staging_bar.setVisible(False) # Now moved to sidebar-toolbar logic
        
        # Toggle between drawing canvas and result canvas
        self.canvas.setVisible(not is_result)
        self.result_canvas.setVisible(is_result)
        
        # 2. Toggle Sidebars & Panels
        # Show/Hide Console
        self.console.setVisible(not is_result)
        
        # Show/Hide Properties
        self.properties.setVisible(tab not in ["RESULT", "MESH"])
        
        # Toggle Staging Sidebar visibility & mode
        # It's visible in both STAGING and RESULT
        show_staging = tab in ["STAGING", "RESULT"]
        self.staging_sidebar.setVisible(show_staging)
        self.staging_sidebar.set_read_only(is_result)

        # Toggle Output Panel visibility
        self.output_panel.setVisible(is_result)

        # In Result mode, we hide properties but show results list (staging sidebar)
        # In Mesh mode, we hide both, so hide the whole splitter
        self.right_splitter.setVisible(tab != "MESH")
        
        self._log(f"Switched to wizard tab: {tab}")

    def _on_tool_button_clicked(self, mode: str):
        """Update ProjectState.tool_mode from toolbar button click."""
        self.state.set_tool_mode(mode)

    # ==================================================================
    # Material Management
    # ==================================================================

    def _on_add_material_clicked(self):
        """Open the MaterialDialog to create a new material."""
        dialog = MaterialDialog(parent=self)
        dialog.material_saved.connect(self._on_material_created)
        dialog.exec()

    def _on_material_created(self, material: dict):
        """Handle a newly created material from the dialog."""
        if material.get("is_beam"):
            self.state.add_beam_material(material)
        else:
            self.state.add_material(material)
        self._log(f"Material created: {material.get('name', '?')} ({material.get('id', '')})")

    def _on_edit_material(self, material_id: str):
        """Open the MaterialDialog to edit an existing material."""
        # Find the material in state
        materials = self.state.materials
        target = None
        for m in materials:
            if m.get("id") == material_id:
                target = m
                break

        if not target:
            self._log(f"[WARN] Material not found: {material_id}")
            return

        dialog = MaterialDialog(material=target, parent=self)
        dialog.material_saved.connect(
            lambda mat: self._on_material_edited(material_id, mat)
        )
        dialog.exec()

    def _on_material_edited(self, material_id: str, updated: dict):
        """Handle an edited material from the dialog."""
        if updated.get("is_beam"):
            self.state.update_beam_material(material_id, updated)
        else:
            self.state.update_material(material_id, updated)
        self._log(f"Material updated: {updated.get('name', '?')}")

    def _on_edit_beam_material(self, material_id: str):
        """Open the MaterialDialog to edit an existing beam material."""
        target = next((m for m in self.state.beam_materials if m.get("id") == material_id), None)
        if not target: return
        
        dialog = MaterialDialog(material=target, parent=self)
        dialog.material_saved.connect(
            lambda mat: self._on_material_edited(material_id, mat)
        )
        dialog.exec()

    def _on_delete_beam_material(self, material_id: str):
        self.state.remove_beam_material(material_id)
        self._log(f"Beam material deleted: {material_id}")

    def _on_delete_beam(self, beam_id: str):
        self.state.remove_embedded_beam(beam_id)
        self._log(f"Embedded beam {beam_id} deleted")

    def _on_delete_material(self, material_id: str):
        """Delete a material from state."""
        self.state.remove_material(material_id)
        self._log(f"Material deleted: {material_id}")

    def _on_delete_polygon(self, index: int):
        """Delete a polygon from state."""
        self.state.remove_polygon(index)
        self._log(f"Polygon {index + 1} deleted")

    # ==================================================================
    # State signal handlers (logged to console)
    # ==================================================================

    def _on_tool_mode_changed(self, mode: str):
        self._log(f"Tool mode → {mode}")

    def _on_polygons_changed(self, polygons: list):
        self._log(f"Polygons updated: {len(polygons)} polygon(s)")

    def _on_point_loads_changed(self, loads: list):
        self._log(f"Point loads updated: {len(loads)} load(s)")

    def _on_materials_changed(self, materials: list):
        self._log(f"Materials updated: {len(materials)} material(s)")

    # ==================================================================
    # Console logging
    # ==================================================================

    def _update_window_title(self):
        """Update the title bar with project name and current file path."""
        p_name = self.state.project_name
        path = self.state.current_file_path
        file_str = f" - [{os.path.basename(path)}]" if path else ""
        self.setWindowTitle(f"TerraSim 0.5.1 Beta - {p_name}{file_str}")

    def _log(self, message: str):
        self.console.log(message)

    # ==================================================================
    # Mesh Generation (Async via QThread)
    # ==================================================================

    def _on_generate_mesh_clicked(self):
        """Handler for 'Generate Mesh' button."""
        if self._mesh_worker and self._mesh_worker.isRunning():
            self._log("[WARN] Mesh generation already in progress...")
            return

        if not self.state.polygons:
            self._log("[WARN] No polygons defined. Draw geometry first.")
            return

        if not self.state.materials:
            self._log("[WARN] No materials defined. Add a material first.")
            return

        # Check all polygons have valid materials
        mat_ids = {m.get("id") for m in self.state.materials}
        for i, poly in enumerate(self.state.polygons):
            mid = poly.get("materialId", "")
            if mid not in mat_ids:
                self._log(
                    f"[WARN] Polygon {i + 1} has no valid material assigned. "
                    "Drag a material from Explorer onto the polygon."
                )
                return

        payload = self.state.get_mesh_payload()

        self._log(f"Starting mesh generation ({len(payload['polygons'])} polygon(s), "
                  f"mesh_size={payload['mesh_settings']['mesh_size']})...")

        self.toolbar_widget.set_mesh_loading(True)

        self.state.set_mesh_response(None)

        self._mesh_worker = MeshWorker(
            payload=payload
        )
        self._mesh_worker.progress.connect(self._on_mesh_progress)
        self._mesh_worker.finished.connect(self._on_mesh_finished)
        self._mesh_worker.error.connect(self._on_mesh_error)
        self._mesh_worker.start()

    def _on_mesh_progress(self, message: str):
        self._log(f"[MESH] {message}")

    def _on_mesh_finished(self, mesh_data: dict):
        n_nodes = len(mesh_data.get("nodes", []))
        n_elems = len(mesh_data.get("elements", []))
        self._log(f"[OK] Mesh generated: {n_nodes} nodes, {n_elems} elements")
        self.state.set_mesh_response(mesh_data)
        self.toolbar_widget.set_mesh_loading(False)
        self._mesh_worker = None

    # ---- Sample Project Loading ----

    def _load_sample_foundation(self):
        """Load the foundation sample into the project state."""
        self.state.load_project(SAMPLE_FOUNDATION)
        self._log("Loaded 'Foundation' sample project.")

    def _load_sample_retaining_wall(self):
        """Load the retaining wall sample into the project state."""
        self.state.load_project(SAMPLE_RETAINING_WALL)
        self._log("Loaded 'Retaining Wall' sample project.")

    # ---- Geometry Import ----

    def _on_import_geometry(self):
        """Standard File-selection followed by the DXF Import Wizard."""
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Select DXF File", "", "CAD Files (*.dxf)"
        )
        if not filepath:
            return

        from ui.import_dxf_dialog import DXFImportDialog
        dialog = DXFImportDialog(filepath, self)
        if dialog.exec():
            polygons, delete_existing = dialog.get_import_data()
            if not polygons:
                self._log("[WARN] No valid geometry found in the selected DXF.")
                return

            # Convert point lists to polygon dicts
            new_polygons = []
            for pts in polygons:
                new_polygons.append({
                    "vertices": pts,
                    "materialId": "default"
                })
            
            # Commit to state
            if delete_existing:
                self.state.set_polygons(new_polygons)
            else:
                current = self.state.polygons
                self.state.set_polygons(current + new_polygons)

            self._log(f"[OK] Successfully imported {len(new_polygons)} polygons from DXF.")

    def _on_export_geometry(self):
        """Export current polygons to a DXF file."""
        polygons = self.state.polygons
        if not polygons:
            self._log("[WARN] No polygons found to export.")
            return

        filepath, _ = QFileDialog.getSaveFileName(
            self, "Export DXF File", "", "CAD Files (*.dxf)"
        )
        if not filepath:
            return

        import ezdxf
        try:
            # Create a new DXF document (R2010 is widely compatible)
            doc = ezdxf.new('R2010')
            doc.header['$INSUNITS'] = 6 # 6 = Meters (TerraSim units)
            msp = doc.modelspace()

            # Group polygons by material for layer organization
            for i, poly in enumerate(polygons):
                vertices = poly.get("vertices", [])
                if not vertices:
                    continue

                mat_id = poly.get("materialId", "default")
                
                # Add a closed LWPOLYLINE
                # points = [(x, y), (x, y), ...]
                points = [(v["x"], v["y"]) for v in vertices]
                
                # We use the material ID as the layer name
                msp.add_lwpolyline(points, dxfattribs={
                    'layer': str(mat_id),
                    'closed': True
                })

            # 2. Export Water Levels
            water_levels = self.state.water_levels
            for i, wl in enumerate(water_levels):
                pts = wl.get("points", [])
                if pts:
                    msp.add_lwpolyline([(p["x"], p["y"]) for p in pts], dxfattribs={
                        'layer': 'WATER_LEVEL',
                        'closed': False,
                        'color': 5 # Blue in CAD
                    })

            # 3. Export Line Loads
            line_loads = self.state.line_loads
            for i, ll in enumerate(line_loads):
                pts = ll.get("points", [])
                if pts:
                    msp.add_lwpolyline([(p["x"], p["y"]) for p in pts], dxfattribs={
                        'layer': 'LINE_LOAD',
                        'closed': False,
                        'color': 2 # Yellow in CAD
                    })

            # 4. Export Point Loads
            point_loads = self.state.point_loads
            for i, pl in enumerate(point_loads):
                x = pl.get("x", 0)
                y = pl.get("y", 0)
                msp.add_point((x, y), dxfattribs={
                    'layer': 'POINT_LOAD',
                    'color': 1 # Red in CAD
                })

            doc.saveas(filepath)
            self._log(f"[OK] Successfully exported geometry (polygons, water, loads) to DXF: {filepath}")

        except Exception as e:
            self._log(f"[ERROR] Export failed: {str(e)}")

    def _on_mesh_error(self, error_msg: str):
        self._log(f"[ERROR] Mesh generation failed: {error_msg}")
        if hasattr(self, "toolbar_widget"):
            self.toolbar_widget.set_mesh_loading(False)
        self._mesh_worker = None

    # ==================================================================
    # Solver Execution
    # ==================================================================

    def _on_run_analysis_clicked(self):
        """Handler for 'Run Analysis' button in StagingBar."""
        try:
            if not self.state.mesh_response:
                self._log("[WARN] No mesh found. Please generate the mesh first.")
                return

            payload = self.state.get_solver_payload()
            if not payload or not payload.get("phases"):
                self._log("[ERROR] No phases defined for calculation.")
                return

            # Avoid double-running or ghost signals
            if self._solve_worker and self._solve_worker.isRunning():
                self._log("[WARN] Analysis already in progress.")
                return

            self._log("Preparing Calculation Console...")

            # 1. Initialize result dialog (cleanup previous if any)
            if self._solve_dialog:
                try: self._solve_dialog.close()
                except: pass
            
            self._solve_dialog = SolveRunDialog(payload["phases"], self)
            
            # 2. Setup Worker
            self._solve_worker = SolveWorker(
                payload=payload
            )

            # 3. Connect signals
            def on_started(ph_id, ph_name, is_safety):
                self._solve_dialog.on_phase_started(ph_id, ph_name, is_safety)
                self.state.set_phase_status(ph_id, "RUNNING")

            def on_finished(ph_id, success, results):
                self._solve_dialog.on_phase_completed(ph_id, success, results)
                status = "SUCCESS" if success else "FAILED"
                self.state.set_phase_status(ph_id, status)
                self.state.set_phase_results(ph_id, results)

            self._solve_worker.log_received.connect(self._solve_dialog.append_log)
            self._solve_worker.phase_started.connect(on_started)
            self._solve_worker.step_point_received.connect(self._solve_dialog.update_phase_point)
            self._solve_worker.phase_finished.connect(on_finished)
            self._solve_worker.finished.connect(self._solve_dialog.on_total_finished)
            self._solve_worker.error.connect(lambda msg: self._log(f"[SOLVER ERROR] {msg}"))

            # Stop Request
            self._solve_dialog.stop_clicked.connect(self._solve_worker.cancel)

            # 4. Execute
            self._solve_dialog.show() 
            self._solve_worker.start()
            self._log("Solver engine started successfully.")

        except Exception as e:
            import traceback
            err_msg = f"CRITICAL UI ERROR: {str(e)}"
            self._log(f"[ERROR] {err_msg}")
            traceback.print_exc()