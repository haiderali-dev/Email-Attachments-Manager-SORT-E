import datetime
import bcrypt
import mysql.connector
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, 
    QLineEdit, QPushButton, QMessageBox, QLabel, QGroupBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication
from config.database import DB_CONFIG
from config.settings import PASSWORD_REGEX
from styles.modern_style import ModernStyle
from PyQt5.QtCore import QSize

class ResetWindow(QWidget):
    def __init__(self, stack):
        super().__init__()
        self.stack = stack
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Email Dashboard - Reset Password")
        
        # Get screen size for responsive design
        screen = QApplication.desktop().screenGeometry()
        window_size = ModernStyle.get_responsive_size(QSize(500, 600), screen.size())
        self.resize(window_size)
        
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(40, 40, 40, 40)

        # Header
        header = QLabel("🔄 Reset Password")
        header.setAlignment(Qt.AlignCenter)
        header.setStyleSheet("font-size: 24pt; font-weight: bold; color: #0078d4; margin-bottom: 20px;")
        layout.addWidget(header)

        # Form
        form_group = QGroupBox("Enter Reset Information")
        form_layout = QFormLayout()
        form_layout.setSpacing(15)

        self.email = QLineEdit()
        self.email.setPlaceholderText("Enter your email address")
        self.token = QLineEdit()
        self.token.setPlaceholderText("Enter 4-digit PIN from email")
        self.pw = QLineEdit()
        self.pw.setEchoMode(QLineEdit.Password)
        self.pw.setPlaceholderText("Enter new password")
        self.pw2 = QLineEdit()
        self.pw2.setEchoMode(QLineEdit.Password)
        self.pw2.setPlaceholderText("Confirm new password")

        form_layout.addRow("Email:", self.email)
        form_layout.addRow("Reset PIN:", self.token)
        form_layout.addRow("New Password:", self.pw)
        form_layout.addRow("Confirm Password:", self.pw2)

        form_group.setLayout(form_layout)
        layout.addWidget(form_group)

        # Buttons
        btn_layout = QHBoxLayout()
        
        btn_reset = QPushButton("✅ Reset Password")
        btn_reset.clicked.connect(self.handle_reset)
        btn_reset.setProperty("class", "success")
        
        btn_back = QPushButton("⬅️ Back to Login")
        btn_back.clicked.connect(lambda: self.stack.setCurrentIndex(0))

        btn_layout.addWidget(btn_reset)
        btn_layout.addWidget(btn_back)
        
        layout.addLayout(btn_layout)
        layout.addStretch()
        
        self.setLayout(layout)

    def handle_reset(self):
        e = self.email.text().strip()
        t = self.token.text().strip()
        p = self.pw.text()
        p2 = self.pw2.text()
        
        if not all([e, t, p, p2]):
            QMessageBox.warning(self, "Missing Information", "Please fill in all fields.")
            return
            
        if p != p2:
            QMessageBox.warning(self, "Password Mismatch", "Passwords do not match.")
            return
            
        if not PASSWORD_REGEX.match(p):
            QMessageBox.warning(self, "Invalid Password", "Password must meet the security requirements.")
            return

        conn = mysql.connector.connect(**DB_CONFIG)
        cur = conn.cursor(dictionary=True)
        
        try:
            cur.execute(
                "SELECT id, reset_token_expiry FROM dashboard_users WHERE email=%s AND reset_token=%s",
                (e, t)
            )
            row = cur.fetchone()
            
            if not row or row['reset_token_expiry'] < datetime.datetime.now():
                QMessageBox.warning(self, "Invalid PIN", "Invalid or expired PIN.")
                return

            pwd_hash = bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()
            cur.execute(
                "UPDATE dashboard_users SET password_hash=%s, reset_token=NULL, reset_token_expiry=NULL WHERE id=%s",
                (pwd_hash, row['id'])
            )
            conn.commit()
            
            QMessageBox.information(self, "Success", "Password reset successfully! Please log in with your new password.")
            self.stack.setCurrentIndex(0)
        finally:
            cur.close()
            conn.close()