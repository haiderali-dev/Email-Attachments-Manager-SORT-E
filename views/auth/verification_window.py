import mysql.connector
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, 
    QLineEdit, QPushButton, QMessageBox, QLabel, QGroupBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication
from config.database import DB_CONFIG
from styles.modern_style import ModernStyle
from PyQt5.QtCore import QSize
from controllers.auth_controller import AuthController

class VerificationWindow(QWidget):
    def __init__(self, stack, email: str):
        super().__init__()
        self.stack = stack
        self.email = email
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Email Dashboard - Email Verification")
        
        # Get screen size for responsive design
        screen = QApplication.desktop().screenGeometry()
        window_size = ModernStyle.get_responsive_size(QSize(500, 600), screen.size())
        self.resize(window_size)
        
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(40, 40, 40, 40)

        # Header
        header = QLabel("📧 Email Verification")
        header.setAlignment(Qt.AlignCenter)
        header.setStyleSheet("font-size: 24pt; font-weight: bold; color: #0078d4; margin-bottom: 20px;")
        layout.addWidget(header)

        # Instructions
        instructions = QLabel(f"""
        We've sent a verification code to:
        <strong>{self.email}</strong>
        
        Please check your inbox and enter the 6-digit verification code below.
        """)
        instructions.setAlignment(Qt.AlignCenter)
        instructions.setStyleSheet("color: #666666; font-size: 11pt; margin: 20px; line-height: 1.5;")
        instructions.setWordWrap(True)
        layout.addWidget(instructions)

        # Verification form
        form_group = QGroupBox("Verification Code")
        form_layout = QFormLayout()
        form_layout.setSpacing(15)

        self.verification_code = QLineEdit()
        self.verification_code.setPlaceholderText("Enter 6-digit code")
        self.verification_code.setMaxLength(6)
        self.verification_code.setStyleSheet("""
            QLineEdit {
                font-size: 18pt;
                text-align: center;
                letter-spacing: 4px;
                padding: 15px;
                border: 2px solid #ddd;
                border-radius: 8px;
                background-color: #f8f9fa;
            }
            QLineEdit:focus {
                border-color: #0078d4;
                background-color: white;
            }
        """)

        form_layout.addRow("Verification Code:", self.verification_code)
        form_group.setLayout(form_layout)
        layout.addWidget(form_group)

        # Buttons
        btn_layout = QHBoxLayout()
        
        btn_verify = QPushButton("✅ Verify Email")
        btn_verify.clicked.connect(self.handle_verification)
        btn_verify.setProperty("class", "success")
        
        btn_resend = QPushButton("🔄 Resend Code")
        btn_resend.clicked.connect(self.handle_resend)
        btn_resend.setProperty("class", "secondary")
        
        btn_back = QPushButton("⬅️ Back to Login")
        btn_back.clicked.connect(lambda: self.stack.setCurrentIndex(0))

        btn_layout.addWidget(btn_verify)
        btn_layout.addWidget(btn_resend)
        btn_layout.addWidget(btn_back)
        
        layout.addLayout(btn_layout)
        layout.addStretch()
        
        self.setLayout(layout)

    def handle_verification(self):
        code = self.verification_code.text().strip()
        
        if not code:
            QMessageBox.warning(self, "Missing Code", "Please enter the verification code.")
            return
            
        if len(code) != 6 or not code.isdigit():
            QMessageBox.warning(self, "Invalid Code", "Please enter a valid 6-digit verification code.")
            return

        # Verify the code
        success, message = AuthController.verify_user_email(self.email, code)
        
        if success:
            QMessageBox.information(self, "Success", message)
            self.stack.setCurrentIndex(0)  # Go back to login
        else:
            QMessageBox.warning(self, "Verification Failed", message)

    def handle_resend(self):
        # Resend verification code
        success, message = AuthController.send_verification_email(self.email)
        
        if success:
            QMessageBox.information(self, "Code Resent", message)
        else:
            QMessageBox.critical(self, "Error", message) 