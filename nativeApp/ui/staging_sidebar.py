import PySide6
import time
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, 
    QPushButton, QScrollArea, QMenu, QMessageBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon, QPixmap
from core.state import ProjectState
from ui.phase_dialog import PhaseDialog

class PhaseItemWidget(QWidget):
    """
    Custom widget representing a single phase in the hierarchy.
    Draws indentation lines and connectors manually.
    """
    clicked = Signal(int)
    double_clicked = Signal(int)
    delete_requested = Signal(int)
    edit_requested = Signal(int)

    def __init__(self, phase, index, levels, is_current=False, read_only=False, parent=None):
        super().__init__(parent)
        self.phase = phase
        self.index = index
        self.levels = levels
        self.is_current = is_current
        self.read_only = read_only
        self.setFixedHeight(28)
        self._init_ui()

    def _init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Indentation Guides
        depth = len(self.levels) - 1
        for i in range(depth):
            guide = QWidget()
            guide.setFixedWidth(20)
            if self.levels[i]:
                line = QFrame(guide)
                line.setFrameShape(QFrame.VLine)
                line.setFrameShadow(QFrame.Plain)
                line.setStyleSheet("color: #e4e4e7;")
                line.setGeometry(9, 0, 1, 28)
            main_layout.addWidget(guide)

        # 2. Connector (├─ or └─)
        if depth >= 0:
            connector_container = QWidget()
            connector_container.setFixedWidth(20)
            
            # If the last level is True, it means there's a sibling below.
            # If False, it's the last child of a branch.
            is_branch_end = not self.levels[depth]
            
            v_top = QFrame(connector_container)
            v_top.setFrameShape(QFrame.VLine)
            v_top.setFrameShadow(QFrame.Plain)
            v_top.setStyleSheet("color: #e4e4e7;")
            v_top.setGeometry(9, 0, 1, 14)
            
            if not is_branch_end:
                v_bottom = QFrame(connector_container)
                v_bottom.setFrameShape(QFrame.VLine)
                v_bottom.setFrameShadow(QFrame.Plain)
                v_bottom.setStyleSheet("color: #e4e4e7;")
                v_bottom.setGeometry(9, 14, 1, 14)
            
            h_line = QFrame(connector_container)
            h_line.setFrameShape(QFrame.HLine)
            h_line.setFrameShadow(QFrame.Plain)
            h_line.setStyleSheet("color: #e4e4e7;")
            h_line.setGeometry(10, 13, 10, 1)
            
            main_layout.addWidget(connector_container)

        # 3. Content Area
        self.content_frame = QFrame()
        self.content_frame.setObjectName("ContentFrame")
        self.content_layout = QHBoxLayout(self.content_frame)
        self.content_layout.setContentsMargins(8, 0, 8, 0)
        self.content_layout.setSpacing(6)
        
        # Icon
        ptype = self.phase.get("phase_type", "PLASTIC")
        icon_lbl = QLabel()
        icon_lbl.setFixedSize(14, 14)
        icon_lbl.setScaledContents(True)
        
        # Determine path relative to this file
        import os
        base_path = os.path.dirname(os.path.dirname(__file__))
        
        if ptype == "SAFETY_ANALYSIS":
            path = os.path.join(base_path, "assets", "icons", "safety.svg")
            icon_lbl.setPixmap(QPixmap(path)) 
            icon_lbl.setStyleSheet("background-color: transparent;")
        else:
            path = os.path.join(base_path, "assets", "icons", "plastic.svg")
            icon_lbl.setPixmap(QPixmap(path))
            icon_lbl.setStyleSheet("background-color: transparent;")
            
        self.content_layout.addWidget(icon_lbl)
        
        name_lbl = QLabel(self.phase.get("name", "Unnamed Phase"))
        name_lbl.setStyleSheet("font-size: 11px; font-weight: 500; background-color: transparent;")
        self.content_layout.addWidget(name_lbl)
        
        # Status Icon (Far Right)
        self.status_icon = QLabel()
        self.status_icon.setFixedSize(14, 14)
        self.status_icon.setScaledContents(True)
        self.status_icon.setStyleSheet("background: transparent;")
        self.content_layout.addWidget(self.status_icon)
        
        self.content_layout.addStretch()
        
        bg_color = "#f1f5f9" if self.is_current else "transparent"
        border = "1px solid #3b82f6" if self.is_current else "none"
        self.content_frame.setStyleSheet(f"""
            QFrame#ContentFrame {{
                background-color: {bg_color};
                border-radius: 4px;
                border: {border};
            }}
            QFrame#ContentFrame:hover {{
                background-color: #f4f4f5;
            }}
        """)
        main_layout.addWidget(self.content_frame)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.index)
        elif event.button() == Qt.RightButton:
            self.clicked.emit(self.index)
            if not self.read_only:
                self._show_context_menu(event.globalPos())

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton and not self.read_only:
            self.double_clicked.emit(self.index)

    def set_status(self, status):
        """Set the success/fail icon on the far right."""
        import os
        base_path = os.path.dirname(os.path.dirname(__file__))
        
        if status == "SUCCESS":
            path = os.path.join(base_path, "assets", "icons", "finished.svg")
            self.status_icon.setPixmap(QPixmap(path))
        elif status == "FAILED":
            path = os.path.join(base_path, "assets", "icons", "fail.svg")
            self.status_icon.setPixmap(QPixmap(path))
        elif status == "RUNNING":
            # Optional: loader or just clear
            self.status_icon.clear()
        else:
            self.status_icon.clear()

    def _show_context_menu(self, pos):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background-color: #ffffff; border: 1px solid #e4e4e7; border-radius: 6px; padding: 4px; }
            QMenu::item { padding: 4px 20px; border-radius: 4px; font-size: 11px; }
            QMenu::item:selected { background-color: #f4f4f5; color: #18181b; }
        """)
        edit_action = menu.addAction("Edit Phase")
        edit_action.triggered.connect(lambda: self.edit_requested.emit(self.index))
        if self.index > 0:
            menu.addSeparator()
            delete_action = menu.addAction("Delete Phase")
            delete_action.triggered.connect(lambda: self.delete_requested.emit(self.index))
        menu.exec(pos)

class StagingSidebar(QWidget):
    """
    Staging Sidebar focusing exclusively on the phase hierarchy tree.
    Element activation logic is now integrated into the Explorer panel.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(240)
        self.setObjectName("StagingSidebar")
        
        self.setStyleSheet("""
            QWidget#StagingSidebar {
                border-left: 1px solid #e4e4e7;
                background-color: #ffffff;
            }
            .SectionHeader {
                font-weight: 600;
                font-size: 11px;
                color: #52525b;
                padding: 6px 10px;
                background-color: #fafafa;
                border-bottom: 1px solid #f4f4f5;
                text-align: left;
            }
        """)
        
        self._state = ProjectState.instance()
        self._is_updating = False
        self._read_only = False

        self._init_ui()

        # Connect signals
        self._state.phases_changed.connect(self._sync_all)
        self._state.current_phase_changed.connect(self._sync_all)
        self._state.phase_status_changed.connect(self._on_status_changed)

        self.widgets_by_id = {}
        self._sync_all()

    def set_read_only(self, read_only: bool):
        """Toggle editability of the phase tree."""
        self._read_only = read_only
        if hasattr(self, 'add_btn'):
            self.add_btn.setVisible(not read_only)
        self._sync_all()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Phases Header
        btn_phases = QPushButton("Phases")
        btn_phases.setProperty("class", "SectionHeader")
        layout.addWidget(btn_phases)

        # Add Button (Now at the top)
        self.add_btn = QPushButton("+ Add Analysis Stage")
        self.add_btn.setStyleSheet("""
            QPushButton { 
                border: 1px dashed #e2e8f0; border-radius: 4px; color: #94a3b8; 
                padding: 6px; font-size: 11px; margin: 8px 10px; font-weight: 500;
            }
            QPushButton:hover { background-color: #f8fafc; color: #64748b; border-style: solid; }
        """)
        self.add_btn.clicked.connect(self._on_add_phase)
        layout.addWidget(self.add_btn)

        # Phases List
        self.phase_scroll = QScrollArea()
        self.phase_scroll.setWidgetResizable(True)
        self.phase_scroll.setFrameShape(QFrame.NoFrame)
        self.phase_content = QWidget()
        self.phase_list_layout = QVBoxLayout(self.phase_content)
        self.phase_list_layout.setContentsMargins(8, 0, 8, 8) # Reduced top margin
        self.phase_list_layout.setSpacing(2)
        self.phase_scroll.setWidget(self.phase_content)
        layout.addWidget(self.phase_scroll, 1) # Set stretch to 1

    def _clear_layout(self):
        """Safely clear the phase list layout."""
        while self.phase_list_layout.count():
            item = self.phase_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.spacerItem():
                pass # Spacers are handled by layout removal

    def _sync_all(self):
        if self._is_updating: return
        self._is_updating = True

        try:
            self._clear_layout()
            self.widgets_by_id = {}

            phases = self._state.phases
            current_idx = self._state.current_phase_index

            # Build list recursively
            self._render_recursive_list(phases, current_idx)

            # Add stretch at the end to keep items at the top
            self.phase_list_layout.addStretch()
        except Exception as e:
            print(f"Error syncing phases: {e}")
        finally:
            self._is_updating = False

    def _render_recursive_list(self, all_phases, current_idx):
        roots = []
        for i, ph in enumerate(all_phases):
            p_id = ph.get("parent_id")
            parent_exists = any(p["id"] == p_id for p in all_phases) if p_id else False
            if not p_id or not parent_exists:
                roots.append((ph, i))

        has_root_siblings = len(roots) > 1
        for i, (root, original_idx) in enumerate(roots):
            is_last = (i == len(roots) - 1)
            # Root depth logic
            levels = [] if not has_root_siblings else [not is_last]
            self._render_item_and_children(root, original_idx, all_phases, current_idx, levels, has_root_siblings)

    def _render_item_and_children(self, phase, idx, all_phases, current_idx, levels, has_siblings):
        item_widget = PhaseItemWidget(phase, idx, levels, is_current=(idx == current_idx), read_only=self._read_only)
        item_widget.clicked.connect(self._state.set_current_phase_index)
        item_widget.double_clicked.connect(self._on_edit_phase)
        item_widget.edit_requested.connect(self._on_edit_phase)
        item_widget.delete_requested.connect(self._on_delete_phase)

        self.widgets_by_id[phase["id"]] = item_widget

        # apply existing status
        initial_status = self._state.get_phase_status(phase["id"])
        item_widget.set_status(initial_status)

        self.phase_list_layout.addWidget(item_widget)

        children = [ (ph, i) for i, ph in enumerate(all_phases) if ph.get("parent_id") == phase["id"] ]

        # User dynamic indentation rule:
        # 1. Indent if the parent has multiple children (branching).
        # 2. OR Indent if the parent itself has siblings (brother).
        has_branching = len(children) > 1
        should_indent_children = has_branching or has_siblings

        for i, (child, original_idx) in enumerate(children):
            c_is_last = (i == len(children) - 1)

            if should_indent_children:
                # Add a new level of indentation
                new_levels = levels + [not c_is_last]
            else:
                # Succession in a solitary path: Keep same alignment
                new_levels = list(levels)

            self._render_item_and_children(child, original_idx, all_phases, current_idx, new_levels, has_branching)

    def _on_edit_phase(self, index):
        from ui.phase_dialog import PhaseDialog
        dlg = PhaseDialog(index, self)
        dlg.exec()

    def _on_delete_phase(self, index):
        if index == 0:
            QMessageBox.information(self, "Action Restricted", "The Initial Phase cannot be deleted.")
            return

        name = self._state.phases[index].get("name", "Phase")
        res = QMessageBox.question(self, "Delete Phase", f"Are you sure you want to delete phase '{name}'?",
                                 QMessageBox.Yes | QMessageBox.No)
        if res == QMessageBox.Yes:
            self._state.remove_phase(index)

    def _on_add_phase(self):
        phases = self._state.phases
        current = self._state.current_phase

        # Determine unique name
        new_name = f"Phase {len(phases)}"
        while any(p.get("name") == new_name for p in phases):
            new_name = f"Phase {len(phases) + 1}"

        new_id = f"phase_{int(time.time() * 1000)}"
        new_phase = {
            "id": new_id,
            "name": new_name,
            "parent_id": current["id"] if current else None,
            "phase_type": "PLASTIC",
            "active_polygon_indices": list(current["active_polygon_indices"]) if current else [],
            "active_load_ids": list(current["active_load_ids"]) if current else [],
            "active_water_level_id": current.get("active_water_level_id") if current else None,
            "active_beam_ids": list(current.get("active_beam_ids", [])) if current else [],
            "reset_displacements": False,
            "current_material": dict(current["current_material"]) if current else {},
            "parent_material": dict(current["current_material"]) if current else {}
        }

        self._state.add_phase(new_phase)
        self._state.set_current_phase_index(len(self._state.phases) - 1)

    def _on_status_changed(self, phase_id, status):
        if phase_id in self.widgets_by_id:
            self.widgets_by_id[phase_id].set_status(status)
