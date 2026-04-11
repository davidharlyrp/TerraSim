# main.py
import sys
import os

# ===========================================================================
# DLL SEARCH PATH FIX (FOR FROZEN BUILDS)
# Required for Python 3.8+ on Windows to find bundled DLLs (MKL/Pardiso)
# ===========================================================================
if getattr(sys, 'frozen', False):
    # Triple-Layer DLL Loader Fix
    bundle_dir = sys._MEIPASS
    if os.path.basename(bundle_dir) == "_internal":
        internal_dir = bundle_dir
    else:
        internal_dir = os.path.join(bundle_dir, '_internal')
    
    # 1. Standard search path
    os.add_dll_directory(bundle_dir)
    if os.path.exists(internal_dir) and internal_dir != bundle_dir:
        os.add_dll_directory(internal_dir)
    
    # 2. Legacy PATH update
    os.environ['PATH'] = bundle_dir + os.pathsep + internal_dir + os.pathsep + os.environ.get('PATH', '')
    
    # 3. AMD Math Hack
    os.environ['MKL_DEBUG_CPU_TYPE'] = '5'
    
    # 4. DIRECT PARDISO FIX
    mkl_lib_path = os.path.join(internal_dir, 'mkl_rt.2.dll')
    if os.path.exists(mkl_lib_path):
        os.environ['PYPARDISO_MKL_RT'] = mkl_lib_path

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from core.licensing import verify_serial
from ui.activation_dialog import ActivationDialog

def check_license():
    """Returns True if the application is correctly activated."""
    from PySide6.QtCore import QSettings
    settings = QSettings("DaharEngineer", "TerraSim")
    
    # Rapid check for status
    is_activated = settings.value("is_activated", False, type=bool)
    if not is_activated:
        return False
        
    # Security re-validation of the stored key
    key = settings.value("license_key", "", type=str)
    return verify_serial(key)

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
    
    # --- LICENSE CHECK ---
    # First, check if the license is already valid in QSettings
    if not check_license():
        # Hide splash or just show dialog
        dlg = ActivationDialog()
        # If user closes dialog without activation, exit app
        if dlg.exec() != ActivationDialog.Accepted:
            sys.exit(0)
    # --- END LICENSE CHECK ---

    # Get initial file from command line (e.g. from double-clicking a .tsmx)
    initial_file = None
    if len(sys.argv) > 1:
        candidate = sys.argv[1]
        if os.path.exists(candidate) and candidate.lower().endswith(".tsmx"):
            initial_file = candidate

    # Jalankan Window Utama
    window = MainWindow(initial_file=initial_file)
    window.show()
    
    sys.exit(app.exec())