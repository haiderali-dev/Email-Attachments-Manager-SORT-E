import bcrypt
import mysql.connector
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, 
    QLineEdit, QPushButton, QMessageBox, QCheckBox, QLabel, QGroupBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication
from config.database import DB_CONFIG
from config.settings import PASSWORD_REGEX
from styles.modern_style import ModernStyle
from PyQt5.QtCore import QSize, pyqtSignal
from controllers.auth_controller import AuthController

class RegisterWindow(QWidget):
    # Signal emitted when verification is needed
    verification_needed = pyqtSignal(str)
    
    def __init__(self, stack):
        super().__init__()
        self.stack = stack
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Email Dashboard - Register")
        
        # Get screen size for responsive design
        screen = QApplication.desktop().screenGeometry()
        window_size = ModernStyle.get_responsive_size(QSize(500, 700), screen.size())
        self.resize(window_size)
        
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(40, 40, 40, 40)

        # Header
        header = QLabel("Create Dashboard Account")
        header.setAlignment(Qt.AlignCenter)
        header.setStyleSheet("font-size: 24pt; font-weight: bold; color: #0078d4; margin-bottom: 20px;")
        layout.addWidget(header)

        # Registration form
        form_group = QGroupBox("Account Information")
        form_layout = QFormLayout()
        form_layout.setSpacing(15)

        self.username = QLineEdit()
        self.username.setPlaceholderText("Choose a username")
        self.email = QLineEdit()
        self.email.setPlaceholderText("Enter your email address")
        self.pw = QLineEdit()
        self.pw.setEchoMode(QLineEdit.Password)
        self.pw.setPlaceholderText("Create a password")
        self.pw2 = QLineEdit()
        self.pw2.setEchoMode(QLineEdit.Password)
        self.pw2.setPlaceholderText("Confirm your password")
        
        show_cb = QCheckBox("Show passwords")
        show_cb.stateChanged.connect(lambda s: [
            self.pw.setEchoMode(QLineEdit.Normal if s else QLineEdit.Password),
            self.pw2.setEchoMode(QLineEdit.Normal if s else QLineEdit.Password)
        ])

        form_layout.addRow("Username:", self.username)
        form_layout.addRow("Email:", self.email)
        form_layout.addRow("Password:", self.pw)
        form_layout.addRow("Confirm Password:", self.pw2)
        form_layout.addRow("", show_cb)

        # Password requirements
        requirements = QLabel("""
        Password Requirements:
        • At least 8 characters long
        • Include uppercase and lowercase letters
        • Include at least one number
        • Include at least one special character
        """)
        requirements.setStyleSheet("color: #666666; font-size: 9pt; margin: 10px;")
        form_layout.addRow("", requirements)

        form_group.setLayout(form_layout)
        layout.addWidget(form_group)

        # Buttons
        btn_layout = QHBoxLayout()
        
        btn_create = QPushButton("✅ Create Account")
        btn_create.clicked.connect(self.handle_register)
        btn_create.setProperty("class", "success")
        
        btn_back = QPushButton("⬅️ Back to Login")
        btn_back.clicked.connect(lambda: self.stack.setCurrentIndex(0))

        btn_layout.addWidget(btn_create)
        btn_layout.addWidget(btn_back)
        
        layout.addLayout(btn_layout)
        layout.addStretch()
        
        self.setLayout(layout)

    def handle_register(self):
        u = self.username.text().strip()
        e = self.email.text().strip()
        p = self.pw.text()
        p2 = self.pw2.text()
        
        if not all([u, e, p, p2]):
            QMessageBox.warning(self, "Missing Information", "Please fill in all fields.")
            return
            
        if p != p2:
            QMessageBox.warning(self, "Password Mismatch", "Passwords do not match.")
            return
            
        if not PASSWORD_REGEX.match(p):
            QMessageBox.warning(
                self, "Invalid Password",
                "Password must be at least 8 characters long and include:\n" +
                "• Uppercase and lowercase letters\n" +
                "• At least one number\n" +
                "• At least one special character"
            )
            return

        # Use AuthController to register user
        success, message, user = AuthController.register_user(u, e, p)
        
        if success:
            # Send verification email
            email_success, email_message = AuthController.send_verification_email(e)
            
            if email_success:
                QMessageBox.information(self, "Registration Successful", 
                    f"{message}\n{email_message}")
                # Emit signal to show verification window
                self.verification_needed.emit(e)
            else:
                QMessageBox.warning(self, "Registration Issue", 
                    f"{message}\nHowever, there was an issue sending the verification email: {email_message}")
        else:
            QMessageBox.warning(self, "Registration Failed", message)