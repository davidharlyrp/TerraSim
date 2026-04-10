# ui/run_dialog.py
import sys
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QProgressBar, QScrollArea, QFrame, QPlainTextEdit,
    QPushButton, QSplitter, QWidget, QFileDialog
)
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QIcon
from core.state import ProjectState

# We use Matplotlib for professional graphing. 
try:
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    HAS_MPL = True
except ImportError:
    HAS_MPL = False

class PhaseProgressCard(QFrame):
    """
    Shows individual phase progress, status, and a mini-graph.
    This card is dynamic and is reused for every phase.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.phase_id = ""
        self.phase_name = "Waiting..."
        self.is_safety = False
        
        self.setFrameShape(QFrame.StyledPanel)
        self.setMinimumHeight(400) 
        self.setStyleSheet("""
            PhaseProgressCard {
                background-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 4px;
            }
            QLabel#PhaseTitle {
                font-weight: 600;
                font-size: 11px;
                color: #1e293b;
            }
            QLabel#StatusLabel {
                font-size: 10px;
                font-weight: 500;
                text-transform: uppercase;
            }
        """)
        
        self.data_x = []
        self.data_y = []
        self._init_ui()

    def _init_ui(self):
        # MAIN LAYOUT
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(12, 8, 12, 8)
        self.main_layout.setSpacing(8)
        
        # 1. TOP SECTION (Header + Progress) - Keep this tight
        top_section = QWidget()
        top_layout = QVBoxLayout(top_section)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(6)
        
        # Header (Title & Status)
        header = QHBoxLayout()
        self.lbl_title = QLabel(self.phase_name)
        self.lbl_title.setObjectName("PhaseTitle")
        header.addWidget(self.lbl_title)
        
        header.addStretch()
        
        self.lbl_status = QLabel("WAITING")
        self.lbl_status.setObjectName("StatusLabel")
        self.lbl_status.setStyleSheet("color: #94a3b8;")
        header.addWidget(self.lbl_status)
        top_layout.addLayout(header)
        
        # Local Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar { background-color: #f1f5f9; border: none; border-radius: 3px; }
            QProgressBar::chunk { background-color: #3b82f6; border-radius: 3px; }
        """)
        top_layout.addWidget(self.progress_bar)
        
        self.main_layout.addWidget(top_section)
        
        # 2. GRAPH SECTION - Should take maximum space
        if HAS_MPL:
            self.figure = Figure(dpi=100)
            self.figure.patch.set_facecolor('#ffffff')
            self.canvas = FigureCanvas(self.figure)
            self.ax = self.figure.add_subplot(111)
            self.ax.tick_params(axis='both', which='major', labelsize=8, colors='#64748b')
            for spine in self.ax.spines.values():
                spine.set_edgecolor('#e2e8f0')
            
            self.line, = self.ax.plot([], [], color='#3b82f6', linewidth=1.0)
            self.ax.set_xlabel("Displacement (m)", fontsize=9, color='#64748b')
            self.ax.set_ylabel("Mstage", fontsize=9, color='#64748b')
            self.figure.tight_layout(pad=1.0)
            self.main_layout.addWidget(self.canvas, 1) # Set stretch to 1
        else:
            placeholder = QLabel("Matplotlib not found.\nGraphs disabled.")
            placeholder.setAlignment(Qt.AlignCenter)
            placeholder.setStyleSheet("color: #94a3b8; font-size: 11px; background: #f8fafc; border-radius: 6px;")
            self.main_layout.addWidget(placeholder, 1)

    def reset(self, phase_id, phase_name, is_safety=False):
        """Reset the card for a new phase."""
        self.phase_id = phase_id
        self.phase_name = phase_name
        self.is_safety = is_safety
        self.lbl_title.setText(phase_name)
        self.lbl_status.setText("INITIATING")
        self.lbl_status.setStyleSheet("color: #3b82f6;")
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet("""
            QProgressBar { background-color: #f1f5f9; border: none; border-radius: 3px; }
            QProgressBar::chunk { background-color: #3b82f6; border-radius: 3px; }
        """)
        self.data_x = []
        self.data_y = []
        if HAS_MPL:
            self.line.set_data([], [])
            # Update Y Label
            y_label = "Msf" if is_safety else "Mstage"
            self.ax.set_ylabel(y_label, fontsize=9, color='#64748b')
            self.ax.relim()
            self.ax.autoscale_view()
            self.canvas.draw()
        
    def update_progress(self, m_stage, max_disp):
        """Update local progress bar and graph data."""
        self.lbl_status.setText(f"RUNNING ({m_stage:.2f})")
        self.lbl_status.setStyleSheet("color: #3b82f6;")
        self.progress_bar.setValue(int(m_stage * 100))
        
        if HAS_MPL:
            self.data_x.append(max_disp)
            self.data_y.append(m_stage)
            self.line.set_data(self.data_x, self.data_y)
            self.ax.relim()
            self.ax.autoscale_view()
            self.canvas.draw()

    def set_finished(self, success):
        if success:
            self.lbl_status.setText("SUCCESS")
            self.lbl_status.setStyleSheet("color: #10b981;")
            self.progress_bar.setValue(100)
            self.progress_bar.setStyleSheet("""
                QProgressBar { background-color: #f1f5f9; border: none; border-radius: 3px; }
                QProgressBar::chunk { background-color: #10b981; border-radius: 3px; }
            """)
        else:
            self.lbl_status.setText("FAILED")
            self.lbl_status.setStyleSheet("color: #ef4444;")
            self.progress_bar.setStyleSheet("""
                QProgressBar { background-color: #f1f5f9; border: none; border-radius: 3px; }
                QProgressBar::chunk { background-color: #ef4444; border-radius: 3px; }
            """)

class SolveRunDialog(QDialog):
    stop_clicked = Signal()

    def __init__(self, phases, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Calculation")
        self.resize(800, 500)
        
        # UI Policy
        self.setWindowFlags(self.windowFlags() | Qt.WindowMinimizeButtonHint | Qt.WindowMaximizeButtonHint)
        
        self.phases = phases
        self.completed_count = 0
        self.is_finished = False
        
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)
        
        # 1. Overall Progress Header (Compact)
        header_container = QFrame()
        header_container.setStyleSheet("background: #f8fafc; border-radius: 4px; border: 1px solid #e2e8f0;")
        header_container.setFixedHeight(48) 
        header_layout = QVBoxLayout(header_container)
        header_layout.setContentsMargins(12, 6, 12, 6)
        header_layout.setSpacing(4)
        
        self.lbl_overall = QLabel(f"Overall Progress: 0 of {len(self.phases)} Phases Complete")
        self.lbl_overall.setStyleSheet("font-weight: 700; font-size: 11px; color: #1e293b; border: none;")
        header_layout.addWidget(self.lbl_overall)
        
        self.overall_progress = QProgressBar()
        self.overall_progress.setFixedHeight(6)
        self.overall_progress.setRange(0, len(self.phases))
        self.overall_progress.setValue(0)
        self.overall_progress.setTextVisible(False)
        self.overall_progress.setStyleSheet("""
            QProgressBar { background-color: #e2e8f0; border: none; border-radius: 3px; }
            QProgressBar::chunk { background-color: #3b82f6; border-radius: 3px; }
        """)
        header_layout.addWidget(self.overall_progress)
        main_layout.addWidget(header_container)
        
        # 2. Main Content Splitter
        main_splitter = QSplitter(Qt.Horizontal)
        
        # Left Panel: Single Dynamic Phase Card
        self.active_card = PhaseProgressCard()
        main_splitter.addWidget(self.active_card)
        
        # Right Panel: System Logs
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        self.log_output = QPlainTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setStyleSheet("""
            QPlainTextEdit {
                background-color: #0f172a;
                color: #94a3b8;
                font-family: 'DM Mono', 'Consolas', monospace;
                font-size: 11px;
                line-height: 1.4;
                border: none;
                border-radius: 8px;
                padding: 10px;
            }
            QScrollBar:vertical {
                border: none;
                background: #0f172a;
                width: 8px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #334155;
                min-height: 20px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical:hover {
                background: #475569;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """)
        right_layout.addWidget(self.log_output)
        
        main_splitter.addWidget(right_panel)
        # Ratio roughly 60/40
        main_splitter.setSizes([650, 450])
        main_layout.addWidget(main_splitter)
        
        # 3. Footer
        footer = QHBoxLayout()
        
        # STOP BUTTON
        self.btn_stop = QPushButton("Stop Analysis")
        self.btn_stop.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #ef4444;
                border: 1px solid #ef4444;
                border-radius: 4px;
                padding: 6px 14px;
                font-weight: 600;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #fef2f2;
            }
            QPushButton:disabled {
                color: #cbd5e1;
                border-color: #e2e8f0;
            }
        """)
        self.btn_stop.clicked.connect(self._on_stop_clicked)
        footer.addWidget(self.btn_stop)

        footer.addStretch()

        # SAVE LOG BUTTON
        self.btn_save_log = QPushButton("Save Log (.txt)")
        self.btn_save_log.setEnabled(False) # Enable once calculation finishes
        self.btn_save_log.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #64748b;
                border: 1px solid #e2e8f0;
                border-radius: 4px;
                padding: 6px 14px;
                font-weight: 500;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #f8fafc;
            }
            QPushButton:enabled {
                color: #334155;
            }
        """)
        self.btn_save_log.clicked.connect(self._on_save_log_clicked)
        footer.addWidget(self.btn_save_log)

        footer.addSpacing(8)
        
        self.btn_close = QPushButton("Close")
        self.btn_close.setEnabled(False) 
        self.btn_close.setStyleSheet("""
            QPushButton {
                background-color: #f1f5f9;
                color: #94a3b8;
                border: none;
                border-radius: 4px;
                padding: 6px 16px;
                font-weight: 600;
                font-size: 11px;
            }
            QPushButton:enabled {
                background-color: #3b82f6;
                color: white;
            }
            QPushButton:hover:enabled {
                background-color: #2563eb;
            }
        """)
        self.btn_close.clicked.connect(self.accept)
        footer.addWidget(self.btn_close)
        main_layout.addLayout(footer)

    def _on_stop_clicked(self):
        self.btn_stop.setEnabled(False)
        self.btn_stop.setText("Stopping...")
        self.stop_clicked.emit()

    def _on_save_log_clicked(self):
        """Save the log output to a .txt file."""
        log_text = self.log_output.toPlainText()
        if not log_text:
            return
            
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Calculation Log", "Simulation_Log.txt", "Text Files (*.txt)"
        )
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(log_text)
                ProjectState.instance().log(f"Log saved to: {file_path}")
            except Exception as e:
                ProjectState.instance().log(f"Error saving log: {str(e)}")

    @Slot(str)
    def append_log(self, message):
        self.log_output.appendPlainText(message)
        self.log_output.verticalScrollBar().setValue(self.log_output.verticalScrollBar().maximum())
        
        # Bridge to main console ONLY for completion/summary messages
        if "finished in" in message or "Total Time:" in message:
            ProjectState.instance().log(message)

    @Slot(str, str, bool)
    def on_phase_started(self, phase_id, phase_name, is_safety):
        """Signal from worker that a new phase is starting."""
        self.active_card.reset(phase_id, phase_name, is_safety)
        self.append_log(f"\n>>> Starting Phase: {phase_name}")

    @Slot(str, dict)
    def update_phase_point(self, phase_id, point):
        # We only care about the currently active card
        if phase_id == self.active_card.phase_id:
            self.active_card.update_progress(
                point.get("m_stage", 0), 
                point.get("max_disp", 0)
            )

    @Slot(str, bool, dict)
    def on_phase_completed(self, phase_id, success, results):
        if phase_id == self.active_card.phase_id:
            self.active_card.set_finished(success)
        
        # Update overall counter
        self.completed_count += 1
        self.overall_progress.setValue(self.completed_count)
        self.lbl_overall.setText(f"Overall Progress: {self.completed_count} of {len(self.phases)} Phases Complete")
        
        if not success:
            self.append_log(f"\n[ERROR] Phase '{self.active_card.phase_name}' failed.")

    @Slot(dict)
    def on_total_finished(self, summary):
        self.is_finished = True
        self.btn_stop.setEnabled(False)
        self.btn_stop.hide()
        self.append_log("\n" + "="*40)
        self.append_log("   ANALYSIS TASK COMPLETED")
        self.append_log("="*40)
        self.btn_close.setEnabled(True)
        self.btn_save_log.setEnabled(True)
