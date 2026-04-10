# ui/activation_dialog.py
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QMessageBox, QFrame
)
from PySide6.QtCore import Qt, QSettings
from core.licensing import verify_serial, unpack_license_data

class ActivationDialog(QDialog):
    """
    A minimalist, sharp-edged activation dialog for TerraSim.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("TerraSim Activation")
        self.setFixedSize(380, 200)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        
        # Persistence settings
        self.settings = QSettings("DaharEngineer", "TerraSim")
        
        self._init_ui()
        self._apply_styles()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Instruction label
        title_label = QLabel("ENTER PRODUCT LICENSE")
        title_label.setStyleSheet("font-weight: semibold; letter-spacing: 1px; color: #a1a1aa;")
        layout.addWidget(title_label)

        # Serial input field
        self.serial_input = QLineEdit()
        self.serial_input.setPlaceholderText("TS-XXXXX-YYYYY")
        self.serial_input.setFixedHeight(36)
        layout.addWidget(self.serial_input)

        # Instruction info
        info_label = QLabel("Please enter the 13-digit serial number provided with your copy.")
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #71717a; font-size: 11px;")
        layout.addWidget(info_label)

        # Action buttons layout
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        # Exit button (Secondary)
        self.btn_exit = QPushButton("Quit")
        self.btn_exit.setFixedHeight(40)
        self.btn_exit.setCursor(Qt.PointingHandCursor)
        self.btn_exit.setObjectName("btn_secondary")
        self.btn_exit.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_exit)

        # Activation button (Primary)
        self.btn_activate = QPushButton("Activate")
        self.btn_activate.setFixedHeight(40)
        self.btn_activate.setCursor(Qt.PointingHandCursor)
        self.btn_activate.clicked.connect(self._on_activate_clicked)
        btn_layout.addWidget(self.btn_activate)

        layout.addLayout(btn_layout)

    def _apply_styles(self):
        """
        Minimalist 'Dahar Engineer' Style: Light Gray/White palette, Sharp Borders.
        """
        self.setStyleSheet("""
            QDialog {
                background-color: #ffffff;
            }
            QLabel {
                color: #18181b;
                background-color: transparent;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QLineEdit {
                background-color: #ffffff;
                border: 1px solid #d4d4d8;
                border-radius: 0px;
                color: #18181b;
                padding-left: 10px;
                font-family: 'Consolas', monospace;
            }
            QLineEdit:focus {
                border: 1px solid #18181b;
            }
            QPushButton#btn_secondary {
                background-color: #f4f4f5;
                border: 1px solid #e4e4e7;
                color: #18181b;
            }
            QPushButton#btn_secondary:hover {
                background-color: #e4e4e7;
                border: 1px solid #d4d4d8;
            }
            QPushButton {
                background-color: #18181b;
                border: none;
                border-radius: 0px;
                color: #ffffff;
                font-weight: bold;
                letter-spacing: 0.5px;
            }
            QPushButton:hover {
                background-color: #27272a;
            }
            QPushButton:pressed {
                background-color: #3f3f46;
            }
            QMessageBox {
                background-color: #ffffff;
            }
            QMessageBox QLabel {
                color: #18181b;
                background-color: transparent;
            }
            QMessageBox QPushButton {
                background-color: #18181b;
                color: #ffffff;
                width: 80px;
                height: 30px;
                border-radius: 0px;
            }
        """)

    def _on_activate_clicked(self):
        serial = self.serial_input.text().strip().upper()
        
        if verify_serial(serial):
            # Save to QSettings permanently (Only the key)
            self.settings.setValue("license_key", serial)
            self.settings.setValue("is_activated", True)
            
            # Extract for the success message only
            _, data_part, _ = serial.split("-")
            info = unpack_license_data(data_part)
            
            QMessageBox.information(
                self, "Success", 
                f"TerraSim has been successfully activated for:\n{info.get('name')}\n\nEnjoy!"
            )
            self.accept()
        else:
            QMessageBox.warning(
                self, "Invalid License", 
                "The serial number provided is invalid. Please try again."
            )
