import sys
import os

# Add current dir to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication
from ui.run_dialog import SolveRunDialog

def test_dialog():
    app = QApplication(sys.argv)
    phases = [
        {"id": "p1", "name": "Phase 1"},
        {"id": "p2", "name": "Phase 2"}
    ]
    try:
        dialog = SolveRunDialog(phases)
        print("Dialog created successfully")
        # Just show for a second
        dialog.show()
        return True
    except Exception as e:
        print(f"FAILED to create dialog: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_dialog()
