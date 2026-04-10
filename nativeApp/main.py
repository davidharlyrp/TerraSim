# main.py
import sys
import os
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from ui.main_window import MainWindow

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

def load_stylesheet(app):
    """Membaca file style.qss dan menerapkannya secara global"""
    qss_path = resource_path(os.path.join("assets", "style.qss"))
    if os.path.exists(qss_path):
        with open(qss_path, "r") as f:
            app.setStyleSheet(f.read())
    else:
        print(f"Warning: style.qss not found at {qss_path}")

if __name__ == "__main__":
    # Force purely light mode at the OS integration level
    os.environ["QT_COLOR_MODE"] = "light"

    app = QApplication(sys.argv)
    
    # Use Fusion style to bypass native Windows overrides
    app.setStyle("Fusion")
    
    # Overwrite the persistent dark palette from Windows 11 completely
    app.styleHints().setColorScheme(Qt.ColorScheme.Light)
    
    from PySide6.QtGui import QIcon
    icon_path = resource_path(os.path.join("assets", "Logo.png"))
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    
    # Terapkan tema
    load_stylesheet(app)
    
    # Jalankan Window Utama
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())