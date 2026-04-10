import sys
try:
    from PySide6.QtWidgets import QApplication, QMainWindow
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    print("Imports successful")
    
    app = QApplication(sys.argv)
    fig = Figure()
    canvas = FigureCanvas(fig)
    print("Canvas created successful")
    
except Exception as e:
    print(f"FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
