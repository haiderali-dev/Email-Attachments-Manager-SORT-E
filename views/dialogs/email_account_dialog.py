import datetime
import mysql.connector
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit, 
    QPushButton, QMessageBox, QGroupBox, QComboBox, QLabel,
    QTextEdit, QFrame, QScrollArea
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QPixmap
from imap_tools import MailBox
from config.database import DB_CONFIG
from config.settings import CONFIG
from services.encryption_service import encrypt_text
import webbrowser

class EmailAccountDialog(QtWidgets.QDialog):
    def __init__(self, parent, user_id):
        super().__init__(parent)
        self.user_id = user_id
        self.setWindowTitle("Add Email Account")
        self.setModal(True)
        self.resize(600, 700)
        
        # Email provider configurations
        self.email_providers = {
            "Multinet": {
                "imap_host": "mail2.multinet.com.pk",
                "port": 993,
                "requires_app_password": False,
                "user_guide_url": "https://multinet.com.pk/email-setup-guide",
                "description": "Multinet email service - uses regular password"
            },
            "Gmail": {
                "imap_host": "imap.gmail.com",
                "port": 993,
                "requires_app_password": True,
                "user_guide_url": "https://youtu.be/lSURGX0JHbA?si=J5uwDrNMvOoNdQfD",
                "description": "Gmail - requires App Password (not regular password)"
            },
            "iCloud": {
                "imap_host": "imap.mail.me.com",
                "port": 993,
                "requires_app_password": True,
                "user_guide_url": "https://youtu.be/b7IrrMvRSsc?si=bhcHoF5TSmg-Pnwf",
                "description": "iCloud Mail - requires App Password (not regular password)"
            },
            "Outlook/Hotmail": {
                "imap_host": "outlook.office365.com",
                "port": 993,
                "requires_app_password": True,
                "user_guide_url": "https://youtu.be/h6ykofBwI8I?si=JonoKfF033ioeUeC",
                "description": "Outlook/Hotmail - requires App Password (not regular password)"
            },
            "Yahoo": {
                "imap_host": "imap.mail.yahoo.com",
                "port": 993,
                "requires_app_password": True,
                "user_guide_url": "https://youtu.be/h_LrGeNV36g?si=OztrQxAuu_4CmAXe",
                "description": "Yahoo Mail - requires App Password (not regular password)"
            },
            "Custom": {
                "imap_host": "",
                "port": 993,
                "requires_app_password": False,
                "user_guide_url": "",
                "description": "Custom IMAP server - enter your own settings"
            }
        }
        
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Header
        header_label = QLabel("Add Email Account")
        header_label.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #2d3748;
                padding: 10px;
            }
        """)
        header_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(header_label)
        
        # Provider Selection
        provider_group = QGroupBox("Select Email Provider")
        provider_layout = QVBoxLayout(provider_group)
        
        # Provider combo box
        self.provider_combo = QComboBox()
        self.provider_combo.addItems(list(self.email_providers.keys()))
        self.provider_combo.currentTextChanged.connect(self.on_provider_changed)
        provider_layout.addWidget(self.provider_combo)
        
        # Provider description
        self.provider_description = QLabel()
        self.provider_description.setWordWrap(True)
        self.provider_description.setStyleSheet("""
            QLabel {
                color: #4a5568;
                font-size: 12px;
                padding: 8px;
                background-color: #f7fafc;
                border-radius: 4px;
                margin: 5px 0;
            }
        """)
        provider_layout.addWidget(self.provider_description)
        
        # User Guide button
        self.user_guide_btn = QPushButton("📖 User Guide - How to Get App Password")
        self.user_guide_btn.clicked.connect(self.open_user_guide)
        self.user_guide_btn.setStyleSheet("""
            QPushButton {
                background-color: #4299e1;
                color: white;
                border: none;
                padding: 10px 16px;
                border-radius: 6px;
                font-weight: 500;
                min-width: 200px;
            }
            QPushButton:hover {
                background-color: #3182ce;
            }
        """)
        provider_layout.addWidget(self.user_guide_btn)
        
        layout.addWidget(provider_group)
        
        # Account Details
        account_group = QGroupBox("Account Details")
        account_layout = QFormLayout(account_group)
        account_layout.setSpacing(10)
        
        # IMAP Host
        self.imap_host = QLineEdit()
        self.imap_host.setPlaceholderText("IMAP server address")
        account_layout.addRow("IMAP Host:", self.imap_host)
        
        # Port
        self.port = QLineEdit()
        self.port.setPlaceholderText("Port number")
        self.port.setText("993")
        account_layout.addRow("Port:", self.port)
        
        # Email
        self.email = QLineEdit()
        self.email.setPlaceholderText("your.email@domain.com")
        account_layout.addRow("Email:", self.email)
        
        # Password
        self.password = QLineEdit()
        self.password.setPlaceholderText("Enter password or App Password")
        self.password.setEchoMode(QLineEdit.Password)
        account_layout.addWidget(self.create_password_info_label())
        account_layout.addRow("Password:", self.password)
        
        layout.addWidget(account_group)
        
        # App Password Warning
        self.app_password_warning = QLabel()
        self.app_password_warning.setWordWrap(True)
        self.app_password_warning.setStyleSheet("""
            QLabel {
                color: #c53030;
                font-size: 12px;
                font-weight: bold;
                padding: 10px;
                background-color: #fed7d7;
                border: 1px solid #feb2b2;
                border-radius: 4px;
                margin: 5px 0;
            }
        """)
        layout.addWidget(self.app_password_warning)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        # Test Connection button
        test_btn = QPushButton("Test Connection")
        test_btn.clicked.connect(self.test_connection)
        test_btn.setStyleSheet(self.get_button_style("blue"))
        
        # Add Account button
        ok_btn = QPushButton("Add Account")
        ok_btn.clicked.connect(self.accept)
        ok_btn.setDefault(True)
        ok_btn.setStyleSheet(self.get_button_style("blue"))
        
        # Cancel button
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet(self.get_button_style("red"))
        
        btn_layout.addWidget(test_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
        
        # Initialize with first provider
        self.on_provider_changed("Multinet")

    def create_password_info_label(self):
        """Create info label for password field"""
        info_label = QLabel("ℹ️ For Gmail, iCloud, Outlook, and Yahoo, you need an App Password, not your regular password.")
        info_label.setWordWrap(True)
        info_label.setStyleSheet("""
            QLabel {
                color: #2b6cb0;
                font-size: 11px;
                padding: 5px;
                background-color: #ebf8ff;
                border-radius: 3px;
                margin: 2px 0;
            }
        """)
        return info_label

    def get_button_style(self, color_type):
        """Get button styling based on color type"""
        if color_type == "blue":
            return """
                QPushButton {
                    background-color: #3182ce;
                    color: white;
                    border: none;
                    padding: 10px 20px;
                    border-radius: 6px;
                    font-weight: 500;
                    min-width: 120px;
                }
                QPushButton:hover {
                    background-color: #2c5282;
                }
                QPushButton:pressed {
                    background-color: #2a4365;
                }
            """
        elif color_type == "red":
            return """
                QPushButton {
                    background-color: #e53e3e;
                    color: white;
                    border: none;
                    padding: 10px 20px;
                    border-radius: 6px;
                    font-weight: 500;
                    min-width: 120px;
                }
                QPushButton:hover {
                    background-color: #c53030;
                }
                QPushButton:pressed {
                    background-color: #9b2c2c;
                }
            """
        return ""

    def on_provider_changed(self, provider_name):
        """Handle provider selection change"""
        provider = self.email_providers[provider_name]
        
        # Update IMAP host and port
        self.imap_host.setText(provider["imap_host"])
        self.port.setText(str(provider["port"]))
        
        # Update description
        self.provider_description.setText(provider["description"])
        
        # Update User Guide button
        if provider["user_guide_url"]:
            self.user_guide_btn.setText(f"📖 User Guide - {provider_name}")
            self.user_guide_btn.setEnabled(True)
        else:
            self.user_guide_btn.setText("📖 User Guide - Custom Setup")
            self.user_guide_btn.setEnabled(False)
        
        # Update App Password warning
        if provider["requires_app_password"]:
            self.app_password_warning.setText(
                f"⚠️ IMPORTANT: {provider_name} requires an App Password, not your regular password. "
                f"Click the User Guide button above to learn how to generate an App Password."
            )
            self.app_password_warning.setVisible(True)
        else:
            self.app_password_warning.setVisible(False)
        
        # Enable/disable host editing for custom
        if provider_name == "Custom":
            self.imap_host.setEnabled(True)
            self.port.setEnabled(True)
        else:
            self.imap_host.setEnabled(False)
            self.port.setEnabled(False)

    def open_user_guide(self):
        """Open user guide for selected provider"""
        provider_name = self.provider_combo.currentText()
        provider = self.email_providers[provider_name]
        
        if provider["user_guide_url"]:
            try:
                webbrowser.open(provider["user_guide_url"])
            except Exception as e:
                QMessageBox.information(self, "User Guide", 
                    f"User Guide for {provider_name}:\n\n"
                    f"Please visit: {provider['user_guide_url']}\n\n"
                    f"This will show you how to generate an App Password for your {provider_name} account.")
        else:
            QMessageBox.information(self, "Custom Setup", 
                "For custom IMAP servers, please refer to your email provider's documentation "
                "for the correct IMAP settings and authentication requirements.")

    def test_connection(self):
        """Test email connection"""
        imap_host = self.imap_host.text().strip()
        port = self.port.text().strip()
        email = self.email.text().strip()
        password = self.password.text().strip()
        
        if not all([imap_host, port, email, password]):
            QMessageBox.warning(self, "Missing Info", "Please fill all fields.")
            return
        
        # Validate port
        try:
            port_num = int(port)
            if port_num <= 0 or port_num > 65535:
                raise ValueError("Invalid port number")
        except ValueError:
            QMessageBox.warning(self, "Invalid Port", "Port must be a valid number between 1 and 65535.")
            return
            
        try:
            # Test connection with port
            with MailBox(imap_host, port=port_num).login(email, password, 'INBOX'):
                QMessageBox.information(self, "✅ Connection Successful", 
                    f"Successfully connected to {imap_host}:{port}\n"
                    f"Email: {email}\n\n"
                    "Your credentials are valid!")
        except Exception as e:
            error_msg = str(e)
            provider_name = self.provider_combo.currentText()
            provider = self.email_providers[provider_name]
            
            if provider["requires_app_password"] and "password" in error_msg.lower():
                QMessageBox.critical(self, "❌ Connection Failed", 
                    f"Failed to connect to {imap_host}:{port}\n\n"
                    f"Error: {error_msg}\n\n"
                    f"💡 {provider_name} requires an App Password, not your regular password.\n"
                    f"Click the User Guide button to learn how to generate an App Password.")
            else:
                QMessageBox.critical(self, "❌ Connection Failed", 
                    f"Failed to connect to {imap_host}:{port}\n\n"
                    f"Error: {error_msg}\n\n"
                    "Please check:\n"
                    "• IMAP host and port are correct\n"
                    "• Email and password are correct\n"
                    "• Your email provider allows IMAP access")

    def accept(self):
        """Add account to database"""
        imap_host = self.imap_host.text().strip()
        port = self.port.text().strip()
        email = self.email.text().strip()
        password = self.password.text().strip()
        
        if not all([imap_host, port, email, password]):
            QMessageBox.warning(self, "Missing Info", "Please fill all fields.")
            return
        
        # Validate port
        try:
            port_num = int(port)
            if port_num <= 0 or port_num > 65535:
                raise ValueError("Invalid port number")
        except ValueError:
            QMessageBox.warning(self, "Invalid Port", "Port must be a valid number between 1 and 65535.")
            return
            
        # Test connection first
        try:
            with MailBox(imap_host, port=port_num).login(email, password, 'INBOX'):
                pass
        except Exception as e:
            error_msg = str(e)
            provider_name = self.provider_combo.currentText()
            provider = self.email_providers[provider_name]
            
            if provider["requires_app_password"] and "password" in error_msg.lower():
                QMessageBox.critical(self, "Connection Failed", 
                    f"Cannot connect to email server:\n{error_msg}\n\n"
                    f"💡 {provider_name} requires an App Password, not your regular password.\n"
                    f"Click the User Guide button to learn how to generate an App Password.")
            else:
                QMessageBox.critical(self, "Connection Failed", 
                    f"Cannot connect to email server:\n{error_msg}")
            return
        
        # Save to database
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        try:
            encrypted_password = encrypt_text(password)
            session_expires = datetime.datetime.now() + datetime.timedelta(days=CONFIG['session_days'])
            
            # Store with port information
            cursor.execute("""
                INSERT INTO accounts (dashboard_user_id, imap_host, imap_port, email, encrypted_password, session_expires)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE 
                imap_host=%s, imap_port=%s, encrypted_password=%s, session_expires=%s, sync_enabled=TRUE
            """, (self.user_id, imap_host, port_num, email, encrypted_password, session_expires,
                  imap_host, port_num, encrypted_password, session_expires))
            
            conn.commit()
            
            provider_name = self.provider_combo.currentText()
            QMessageBox.information(self, "✅ Success", 
                f"Email account added successfully!\n\n"
                f"Provider: {provider_name}\n"
                f"Email: {email}\n"
                f"Server: {imap_host}:{port}\n\n"
                "Your account is now ready to sync emails!")
            
            super().accept()
            
        except mysql.connector.errors.IntegrityError:
            QMessageBox.warning(self, "Duplicate", "This email account is already added.")
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Failed to save account: {str(e)}")
        finally:
            cursor.close()
            conn.close()