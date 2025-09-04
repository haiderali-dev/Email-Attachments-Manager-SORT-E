import os
import tempfile
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QPushButton,
    QTextEdit, QGroupBox, QFrame, QGridLayout, QFileDialog, QMessageBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QSplitter, QScrollArea,
    QWidget, QSizePolicy, QListWidget, QListWidgetItem
)
from PyQt5.QtCore import Qt, QSize, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QIcon
from styles.modern_style import ModernStyle
from utils.formatters import format_size
from services.attachment_fetch_service import AttachmentFetchService
from views.dialogs.attachment_details_dialog import AttachmentDetailsDialog

class AttachmentFetchWorker(QThread):
    """Worker thread for fetching attachments from IMAP"""
    attachments_loaded = pyqtSignal(list)
    fetch_error = pyqtSignal(str)
    
    def __init__(self, email_id: int, account_id: int):
        super().__init__()
        self.email_id = email_id
        self.account_id = account_id
        self.attachment_fetch_service = AttachmentFetchService()
    
    def run(self):
        try:
            attachments = self.attachment_fetch_service.get_email_attachments(
                self.email_id, self.account_id
            )
            self.attachments_loaded.emit(attachments)
        except Exception as e:
            self.fetch_error.emit(str(e))

class EmailAttachmentsListDialog(QDialog):
    def __init__(self, email_data: dict, parent=None):
        super().__init__(parent)
        self.email_data = email_data
        self.attachments = []
        self.fetch_worker = None
        self.init_ui()
        self.fetch_attachments()
    
    def init_ui(self):
        self.setWindowTitle("📎 Email Attachments")
        self.setModal(True)
        
        # Set window size
        self.resize(800, 600)
        
        # Apply modern styling
        self.setStyleSheet(ModernStyle.get_stylesheet())
        
        # Main layout
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        title_label = QLabel(f"📧 {self.email_data['subject']}")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #2196F3;")
        layout.addWidget(title_label)
        
        # Email info
        email_info = self.create_email_info_panel()
        layout.addWidget(email_info)
        
        # Loading indicator
        self.loading_label = QLabel("fetching attachments from IMAP...")
        self.loading_label.setStyleSheet("color: #666; font-style: italic;")
        layout.addWidget(self.loading_label)
        
        # Attachments list
        self.attachments_group = QGroupBox("📎 Attachments")
        self.attachments_layout = QVBoxLayout(self.attachments_group)
        
        self.attachments_list = QListWidget()
        self.attachments_list.itemDoubleClicked.connect(self.view_attachment)
        self.attachments_layout.addWidget(self.attachments_list)
        
        layout.addWidget(self.attachments_group)
        
        # Action buttons
        button_layout = QHBoxLayout()
        
            # View button
        self.view_button = QPushButton("View Selected")
        self.view_button.clicked.connect(self.view_selected_attachment)
        self.view_button.setEnabled(False)
        self.view_button.setStyleSheet("""
            QPushButton {
                background-color: #3182ce;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #2a4365;
            }
            QPushButton:pressed {
                background-color: #1e3250;
            }
        """)
        button_layout.addWidget(self.view_button)

        # Download button
        self.download_button = QPushButton("Download Selected")
        self.download_button.clicked.connect(self.download_selected_attachment)
        self.download_button.setEnabled(False)
        self.download_button.setStyleSheet("""
            QPushButton {
                background-color: #3182ce;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #2a4365;
            }
            QPushButton:pressed {
                background-color: #1e3250;
            }
        """)
        button_layout.addWidget(self.download_button)

        button_layout.addStretch()

        # Close button
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.close)
        close_button.setStyleSheet("""
            QPushButton {
                background-color: #e53e3e;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #c53030;
            }
            QPushButton:pressed {
                background-color: #9b2c2c;
            }
        """)
        button_layout.addWidget(close_button)

        layout.addLayout(button_layout)
    
    def create_email_info_panel(self):
        """Create the email information panel"""
        panel = QGroupBox("📧 Email Information")
        layout = QVBoxLayout(panel)
        
        # Form layout for email details
        form_layout = QFormLayout()
        form_layout.setVerticalSpacing(10)
        form_layout.setHorizontalSpacing(15)
        
        # Subject
        subject = self.email_data['subject'] or "No Subject"
        subject_label = QLabel(subject)
        subject_label.setWordWrap(True)
        form_layout.addRow("📧 Subject:", subject_label)
        
        # Sender
        sender = self.email_data['sender'] or "Unknown"
        sender_label = QLabel(sender)
        sender_label.setWordWrap(True)
        form_layout.addRow("👤 Sender:", sender_label)
        
        # Date
        email_date = self.email_data['email_date']
        if email_date:
            date_str = email_date.strftime("%Y-%m-%d %H:%M:%S")
        else:
            date_str = "Unknown"
        date_label = QLabel(date_str)
        form_layout.addRow("📅 Date:", date_label)
        
        # Account
        account = self.email_data['account_email'] or "Unknown"
        account_label = QLabel(account)
        form_layout.addRow("📧 Account:", account_label)
        
        # IMAP Host
        imap_host = self.email_data['imap_host'] or "Unknown"
        host_label = QLabel(imap_host)
        form_layout.addRow("🌐 IMAP Host:", host_label)
        
        layout.addLayout(form_layout)
        
        return panel
    
    def fetch_attachments(self):
        """Fetch attachments from IMAP"""
        try:
            import mysql.connector
            from config.database import DB_CONFIG
            
            # Get account ID for this email
            conn = mysql.connector.connect(**DB_CONFIG)
            cursor = conn.cursor()
            
            cursor.execute("SELECT account_id FROM emails WHERE id = %s", (self.email_data['email_id'],))
            result = cursor.fetchone()
            
            cursor.close()
            conn.close()
            
            if not result:
                self.loading_label.setText("❌ Error: Could not determine account for this email")
                return
            
            account_id = result[0]
            
            # Start fetching attachments in background
            self.fetch_worker = AttachmentFetchWorker(self.email_data['email_id'], account_id)
            self.fetch_worker.attachments_loaded.connect(self.on_attachments_loaded)
            self.fetch_worker.fetch_error.connect(self.on_fetch_error)
            self.fetch_worker.start()
            
        except Exception as e:
            self.loading_label.setText(f"❌ Error: {str(e)}")
    
    def on_attachments_loaded(self, attachments):
        """Handle attachments loaded from IMAP"""
        self.attachments = attachments
        self.loading_label.setVisible(False)
        
        if not attachments:
            self.attachments_list.addItem("No attachments found in this email")
            return
        
        # Populate attachments list
        for attachment in attachments:
            filename = attachment['filename']
            size = attachment['size_formatted']
            item_text = f"📎 {filename} ({size})"
            
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, attachment)
            self.attachments_list.addItem(item)
        
        # Enable buttons if attachments found
        if attachments:
            self.view_button.setEnabled(True)
            self.download_button.setEnabled(True)
    
    def on_fetch_error(self, error_message):
        """Handle fetch error"""
        self.loading_label.setText(f"❌ Error fetching attachments: {error_message}")
    
    def view_selected_attachment(self):
        """View the selected attachment"""
        current_item = self.attachments_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "No Selection", "Please select an attachment to view.")
            return
        
        attachment_data = current_item.data(Qt.UserRole)
        if not attachment_data:
            return
        
        self.view_attachment_item(attachment_data)
    
    def download_selected_attachment(self):
        """Download the selected attachment"""
        current_item = self.attachments_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "No Selection", "Please select an attachment to download.")
            return
        
        attachment_data = current_item.data(Qt.UserRole)
        if not attachment_data:
            return
        
        self.download_attachment_item(attachment_data)
    
    def view_attachment(self, item):
        """View attachment when double-clicked"""
        attachment_data = item.data(Qt.UserRole)
        if attachment_data:
            self.view_attachment_item(attachment_data)
    
    def view_attachment_item(self, attachment_data):
        """View a specific attachment"""
        filename = attachment_data['filename']
        temp_path = attachment_data.get('temp_path')
        
        if not temp_path or not os.path.exists(temp_path):
            QMessageBox.warning(self, "Error", "Attachment file not found or already cleaned up.")
            return
        
        try:
            # Open file with default Windows application
            os.startfile(temp_path)
            QMessageBox.information(self, "Success", 
                                  f"Opened '{filename}' with default application")
        except Exception as e:
            QMessageBox.critical(self, "Error", 
                               f"Failed to open attachment: {str(e)}")
    
    def download_attachment_item(self, attachment_data):
        """Download a specific attachment"""
        filename = attachment_data['filename']
        temp_path = attachment_data.get('temp_path')
        
        if not temp_path or not os.path.exists(temp_path):
            QMessageBox.warning(self, "Error", "Attachment file not found or already cleaned up.")
            return
        
        # Get save path from user
        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Attachment",
            filename,
            "All Files (*.*)"
        )
        
        if save_path:
            try:
                import shutil
                shutil.copy2(temp_path, save_path)
                QMessageBox.information(self, "Download Complete", 
                                      f"Attachment saved to:\n{save_path}")
            except Exception as e:
                QMessageBox.critical(self, "Download Error", 
                                   f"Error saving attachment:\n{str(e)}")
    
    def closeEvent(self, event):
        """Handle dialog closing"""
        if self.fetch_worker and self.fetch_worker.isRunning():
            self.fetch_worker.terminate()
            self.fetch_worker.wait()
        event.accept() 