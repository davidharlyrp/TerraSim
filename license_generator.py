# license_generator.py
import sys
import os
import hashlib
import base64
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, 
    QLabel, QLineEdit, QPushButton, QTextEdit
)
from PySide6.QtCore import Qt

# ===========================================================================
# GENERATION ENGINE (ISOLATED)
# ===========================================================================

def _generate_signature(data_part: str) -> str:
    """
    Kalkulasi signature (Double SHA-256) dengan salt produksi.
    Hanya ada di sini (Generator). App utama hanya memverifikasi.
    """
    salt = "T3rr4S1m_2oz4" # Ini adalah kombinasi salt dari core
    first_pass = hashlib.sha256(f"{data_part}{salt}".encode()).hexdigest()
    second_pass = hashlib.sha256(first_pass.encode()).hexdigest()
    return second_pass[:6].upper()

def _pack_license_data(id_val: str, name: str, email: str) -> str:
    """
    Mengemas Data User ke Base32.
    """
    raw = f"{id_val.strip()}|{name.strip()}|{email.strip().lower()}".encode('utf-8')
    return base64.b32encode(raw).decode('utf-8').rstrip('=')

# ===========================================================================
# UI COMPONENT
# ===========================================================================

class LicenseGenerator(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TerraSim Licensing System - Generator")
        self.setFixedSize(450, 480)
        self._init_ui()
        self._apply_styles()

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(30,30,30,30)
        layout.setSpacing(12)

        title = QLabel("PRODUCTION LICENSE ISSUER")
        title.setStyleSheet("font-weight: bold; letter-spacing: 2px; color: #a1a1aa; font-size: 14px;")
        layout.addWidget(title)

        # Inputs
        layout.addWidget(QLabel("USER ID / INVOICE ID:"))
        self.id_input = QLineEdit()
        self.id_input.setPlaceholderText("INV-001")
        layout.addWidget(self.id_input)

        layout.addWidget(QLabel("FULL NAME:"))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("David Harly")
        layout.addWidget(self.name_input)

        layout.addWidget(QLabel("EMAIL ADDRESS:"))
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("david@example.com")
        layout.addWidget(self.email_input)

        layout.addSpacing(10)

        self.btn_gen = QPushButton("GENERATE PRODUCTION SERIAL")
        self.btn_gen.setFixedHeight(45)
        self.btn_gen.setCursor(Qt.PointingHandCursor)
        self.btn_gen.clicked.connect(self._on_generate)
        layout.addWidget(self.btn_gen)

        layout.addSpacing(10)

        layout.addWidget(QLabel("RESULTING SERIAL KEY:"))
        self.result_box = QTextEdit()
        self.result_box.setReadOnly(True)
        self.result_box.setFixedHeight(80)
        self.result_box.setStyleSheet("background-color: #09090b; color: #10b981; font-weight: bold;")
        layout.addWidget(self.result_box)

    def _apply_styles(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #ffffff; }
            QLabel { color: #18181b; font-size: 11px; font-weight: bold; }
            QLineEdit { 
                background-color: #ffffff; 
                border: 1px solid #d4d4d8; 
                border-radius: 0px; 
                color: #18181b; 
                padding: 8px;
                font-family: 'Consolas', monospace;
            }
            QLineEdit:focus {
                border: 1px solid #18181b;
            }
            QPushButton { 
                background-color: #18181b; 
                border: none; 
                color: #ffffff; 
                font-weight: bold; 
                border-radius: 0px;
            }
            QPushButton:hover { background-color: #27272a; }
            QTextEdit { 
                background-color: #f8fafc;
                border: 1px solid #d4d4d8; 
                border-radius: 0px; 
                padding: 10px; 
                font-size: 14px; 
                color: #059669; /* Emerald for success info */
                font-weight: bold;
            }
        """)

    def _on_generate(self):
        id_val = self.id_input.text().strip()
        name = self.name_input.text().strip()
        email = self.email_input.text().strip()

        if not name or not email:
            self.result_box.setText("FAILED: Metadata required.")
            return

        # Core logic (INTERNAL to this script)
        data_part = _pack_license_data(id_val, name, email)
        sig = _generate_signature(data_part)
        serial = f"TS-{data_part}-{sig}"

        self.result_box.setText(serial)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = LicenseGenerator()
    window.show()
    sys.exit(app.exec())
