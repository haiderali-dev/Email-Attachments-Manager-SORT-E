import datetime
import random
import smtplib
import ssl
import mysql.connector
from email.message import EmailMessage
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, 
    QLineEdit, QPushButton, QMessageBox, QLabel, QGroupBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication
from config.database import DB_CONFIG
from config.settings import EMAIL_CONFIG
from styles.modern_style import ModernStyle
from PyQt5.QtCore import QSize

class ForgotWindow(QWidget):
    def __init__(self, stack):
        super().__init__()
        self.stack = stack
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Email Dashboard - Forgot Password")
        
        # Get screen size for responsive design
        screen = QApplication.desktop().screenGeometry()
        window_size = ModernStyle.get_responsive_size(QSize(500, 400), screen.size())
        self.resize(window_size)
        
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(40, 40, 40, 40)

        # Header
        header = QLabel("Reset Password")
        header.setAlignment(Qt.AlignCenter)
        header.setStyleSheet("font-size: 24pt; font-weight: bold; color: #0078d4; margin-bottom: 20px;")
        layout.addWidget(header)

        # Form
        form_group = QGroupBox("Password Reset")
        form_layout = QFormLayout()
        form_layout.setSpacing(15)

        self.email = QLineEdit()
        self.email.setPlaceholderText("Enter your registered email")
        form_layout.addRow("Email Address:", self.email)

        info_label = QLabel("Enter your email address and we'll send you a 4-digit PIN to reset your password.")
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #666666; margin: 10px;")
        form_layout.addRow("", info_label)

        form_group.setLayout(form_layout)
        layout.addWidget(form_group)

        # Buttons
        btn_layout = QHBoxLayout()
        
        btn_send = QPushButton("📧 Send Reset PIN")
        btn_send.clicked.connect(self.handle_forgot)
        btn_send.setProperty("class", "warning")
        
        btn_back = QPushButton("⬅️ Back to Login")
        btn_back.clicked.connect(lambda: self.stack.setCurrentIndex(0))

        btn_layout.addWidget(btn_send)
        btn_layout.addWidget(btn_back)
        
        layout.addLayout(btn_layout)
        layout.addStretch()
        
        self.setLayout(layout)

    def handle_forgot(self):
        e = self.email.text().strip()
        
        if not e:
            QMessageBox.warning(self, "Missing Email", "Please enter your email address.")
            return

        conn = mysql.connector.connect(**DB_CONFIG)
        cur = conn.cursor(dictionary=True)
        
        try:
            cur.execute("SELECT id FROM dashboard_users WHERE email=%s", (e,))
            row = cur.fetchone()
            
            if not row:
                QMessageBox.warning(self, "Email Not Found", "No account found with this email address.")
                return

            # Generate 4-digit PIN
            token = f"{random.randint(0, 9999):04d}"
            expiry = datetime.datetime.now() + datetime.timedelta(minutes=20)
            
            cur.execute(
                "UPDATE dashboard_users SET reset_token=%s, reset_token_expiry=%s WHERE id=%s",
                (token, expiry, row['id'])
            )
            conn.commit()

            # Send email
            msg = EmailMessage()
            msg['Subject'] = 'Password Reset PIN - Email Dashboard'
            msg['From'] = EMAIL_CONFIG['username']
            msg['To'] = e
            
            msg.set_content(
                f"Your password reset PIN is: {token}\n"
                f"This PIN expires at: {expiry.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                f"If you did not request this, please ignore this email."
            )
            
            html_content = f"""
            <html>
            <body style="font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 8px;">
                    <h2 style="color: #0078d4; text-align: center;">🔑 Password Reset Request</h2>
                    <p>You requested to reset your password for the Email Dashboard. Use the PIN below to proceed:</p>
                    <div style="text-align: center; background-color: #f8f9fa; padding: 20px; border-radius: 6px; margin: 20px 0;">
                        <span style="font-size: 32px; font-weight: bold; color: #0078d4; letter-spacing: 4px;">{token}</span>
                    </div>
                    <p><strong>Expires at:</strong> {expiry.strftime('%Y-%m-%d %H:%M:%S')}</p>
                    <p style="color: #666; font-size: 14px;">If you did not request this, please ignore this email.</p>
                    <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
                    <p style="color: #666; font-size: 12px; text-align: center;">Email Management Dashboard</p>
                </div>
            </body>
            </html>
            """
            msg.add_alternative(html_content, subtype='html')

            context = ssl.create_default_context()
            try:
                with smtplib.SMTP_SSL(
                    EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port'], context=context
                ) as server:
                    server.login(EMAIL_CONFIG['username'], EMAIL_CONFIG['password'])
                    server.send_message(msg)
                    
                QMessageBox.information(
                    self, "PIN Sent",
                    "A 4-digit PIN has been sent to your email. Please check your inbox and proceed to reset your password."
                )
                self.stack.setCurrentIndex(3)
                
            except Exception as ex:
                QMessageBox.critical(self, "Email Error", f"Failed to send email: {str(ex)}")
        finally:
            cur.close()
            conn.close()