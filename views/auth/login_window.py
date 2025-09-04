import datetime
import bcrypt
import mysql.connector
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, 
    QLineEdit, QPushButton, QMessageBox, QCheckBox, QLabel, QGroupBox
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QApplication
from config.database import DB_CONFIG
from styles.modern_style import ModernStyle
from PyQt5.QtCore import QSize

class LoginWindow(QWidget):
    login_successful = pyqtSignal(int)  # Signal to emit user ID on successful login
    
    def __init__(self, stack):
        super().__init__()
        self.stack = stack
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Email Dashboard - Login")
        
        # Get screen size for responsive design
        screen = QApplication.desktop().screenGeometry()
        window_size = ModernStyle.get_responsive_size(QSize(500, 600), screen.size())
        self.resize(window_size)
        
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(40, 40, 40, 40)

                # Header
        header = QLabel("SORT E")
        header.setAlignment(Qt.AlignCenter)
        header.setStyleSheet("""
            font-size: 45pt;
            font-weight: 900;
            font-style: italic;
            color: #3182ce;
            margin-bottom: 20px;
        """)
        layout.addWidget(header)

            # Login form
        form_group = QGroupBox("Welcome! Please login")
        form_group.setStyleSheet("""
    QGroupBox {
        font-size: 14pt;
        font-weight: bold;
        margin-top: 22px;
        color: #333333; /* default for content */
    }

    QGroupBox::title {
        color: #3182ce; /* title text only */
    }
""")
        form_layout = QFormLayout()
        form_layout.setSpacing(20)

        self.username = QLineEdit()
        self.username.setPlaceholderText("Enter username or email")
        self.pw = QLineEdit()
        self.pw.setEchoMode(QLineEdit.Password)
        self.pw.setPlaceholderText("Enter password")
        
        show_cb = QCheckBox("Show password")
        show_cb.stateChanged.connect(lambda s: self.pw.setEchoMode(
            QLineEdit.Normal if s else QLineEdit.Password
        ))
        
        #self.remember = QCheckBox("Remember me")

        form_layout.addRow("Username/Email:", self.username)
        form_layout.addRow("Password:", self.pw)
        form_layout.addRow("", show_cb)
        #form_layout.addRow("", self.remember)

        form_group.setLayout(form_layout)
        layout.addWidget(form_group)

        # Buttons
        btn_layout = QHBoxLayout()
        
        btn_login = QPushButton("Login")
        btn_login.clicked.connect(self.handle_login)
        btn_login.setDefault(True)
        
        btn_register = QPushButton("Register")
        btn_register.clicked.connect(lambda: self.stack.setCurrentIndex(1))
        btn_register.setProperty("class", "success")
        
        btn_forgot = QPushButton("Forgot Password")
        btn_forgot.clicked.connect(lambda: self.stack.setCurrentIndex(2))
        btn_forgot.setProperty("class", "warning")

        btn_layout.addWidget(btn_login)
        btn_layout.addWidget(btn_register)
        btn_layout.addWidget(btn_forgot)
        
        layout.addLayout(btn_layout)
        layout.addStretch()
        
        self.setLayout(layout)
        
        # Connect Enter key
        self.username.returnPressed.connect(self.move_to_password)
        self.pw.returnPressed.connect(self.handle_login)

    def handle_login(self):
        user = self.username.text().strip()
        pwd = self.pw.text().encode()
        
        if not user or not pwd:
            QMessageBox.warning(self, "Missing Information", "Please enter both username and password.")
            return

        conn = mysql.connector.connect(**DB_CONFIG)
        cur = conn.cursor(dictionary=True)
        
        try:
            cur.execute("SELECT * FROM dashboard_users WHERE username=%s OR email=%s", (user, user))
            row = cur.fetchone()
            
            if not row:
                QMessageBox.warning(self, "Error", "User not found.")
                return

            # Check if user is verified
            if not row['is_verified']:
                QMessageBox.warning(
                    self, "Account Not Verified",
                    "Your email address has not been verified. Please check your email for the verification code and complete the registration process."
                )
                return

            now = datetime.datetime.now()
            if row['locked_until'] and now < row['locked_until']:
                QMessageBox.warning(
                    self, "Account Locked",
                    f"Too many failed attempts. Try again after {row['locked_until']}"
                )
                return

            if bcrypt.checkpw(pwd, row['password_hash'].encode()):
                # Successful login
                cur.execute(
                    "UPDATE dashboard_users SET failed_attempts=0, locked_until=NULL, last_login=NOW() WHERE id=%s",
                    (row['id'],)
                )
                conn.commit()
                
                # Clean expired email sessions
                self.clean_expired_sessions(cur, conn)
                
                QMessageBox.information(self, "Success", f"Welcome back, {row['username']}!")
                self.login_successful.emit(row['id'])
            else:
                # Failed login
                attempts = row['failed_attempts'] + 1
                lock_time = None
                if attempts >= 5:
                    lock_time = now + datetime.timedelta(minutes=10)
                    
                cur.execute(
                    "UPDATE dashboard_users SET failed_attempts=%s, locked_until=%s WHERE id=%s",
                    (attempts, lock_time, row['id'])
                )
                conn.commit()
                QMessageBox.warning(self, "Error", "Invalid credentials.")
        finally:
            cur.close()
            conn.close()

    def clean_expired_sessions(self, cursor, conn):
        """Clean expired email account sessions"""
        cursor.execute("""
            UPDATE accounts 
            SET sync_enabled=FALSE 
            WHERE session_expires IS NOT NULL 
            AND session_expires < NOW()
        """)
        conn.commit()

    def move_to_password(self):
        """Move cursor to password field when Enter is pressed in username field"""
        self.pw.setFocus()
        self.pw.selectAll()  # Select all text in password field for easy replacement