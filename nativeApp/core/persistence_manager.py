import json
import os
from PySide6.QtWidgets import QFileDialog, QMessageBox, QWidget
from core.state import ProjectState

class PersistenceManager:
    """
    Handles file I/O logic for the TerraSim (.tsmx) project format.
    Communicates directly with ProjectState to serialize/deserialize data.
    """
    EXTENSION = "tsmx"
    FILTER = f"TerraSim Project (*.{EXTENSION})"

    def __init__(self, parent_widget: QWidget):
        self._parent = parent_widget
        self._state = ProjectState.instance()

    def handle_new(self):
        """Reset the project after confirmation."""
        if self._confirm_discard():
            self._state.reset()
            self._state.set_current_file_path(None)

    def handle_open(self):
        """Open a .tsmx file."""
        if not self._confirm_discard():
            return

        file_path, _ = QFileDialog.getOpenFileName(
            self._parent, "Open Project", "", self.FILTER
        )
        if not file_path:
            return

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            self._state.load_project(data)
            self._state.set_current_file_path(file_path)
            self._state.log(f"Project loaded from: {os.path.basename(file_path)}")
        except Exception as e:
            QMessageBox.critical(self._parent, "Error", f"Failed to load project: {e}")

    def handle_save(self) -> bool:
        """Save the current project. Prompts for path if first time."""
        path = self._state.current_file_path
        if not path:
            return self.handle_save_as()
        return self._save_to_path(path)

    def handle_save_as(self) -> bool:
        """Prompt for a new file path and save."""
        file_path, _ = QFileDialog.getSaveFileName(
            self._parent, "Save Project As", "", self.FILTER
        )
        if not file_path:
            return False
            
        if not file_path.endswith(f".{self.EXTENSION}"):
            file_path += f".{self.EXTENSION}"
            
        if self._save_to_path(file_path):
            self._state.set_current_file_path(file_path)
            return True
        return False

    def _save_to_path(self, path: str) -> bool:
        """Internal worker to write state to disk."""
        try:
            data = self._state.serialize_project()
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            
            self._state.log(f"Project saved to: {os.path.basename(path)}")
            return True
        except Exception as e:
            QMessageBox.critical(self._parent, "Error", f"Failed to save project: {e}")
            return False

    def _confirm_discard(self) -> bool:
        """Return True if it's safe to discard current changes."""
        # Simple confirmation for now. 
        # Future: implement a 'dirty' flag in ProjectState.
        reply = QMessageBox.question(
            self._parent, "Confirm",
            "Are you sure you want to discard current changes?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        return reply == QMessageBox.Yes
