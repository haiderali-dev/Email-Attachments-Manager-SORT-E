import os
import tempfile
import mimetypes
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit, 
    QPushButton, QMessageBox, QGroupBox, QListWidget, QListWidgetItem,
    QLabel, QTextEdit, QFileDialog, QSplitter, QWidget, QScrollArea,
    QFrame, QSizePolicy, QApplication, QProgressBar
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt5.QtGui import QPixmap, QFont
import mysql.connector
from config.database import DB_CONFIG
from services.attachment_service import AttachmentService
from services.attachment_fetch_service import AttachmentFetchService
from utils.helpers import format_size, get_safe_filename

class AttachmentFetchThread(QThread):
    """Thread for fetching attachments to prevent UI freezing"""
    attachments_loaded = pyqtSignal(list)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, email_id, account_id):
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
            self.error_occurred.emit(str(e))

class AttachmentViewerDialog(QDialog):
    def __init__(self, parent, email_id, user_id):
        super().__init__(parent)
        self.email_id = email_id
        self.user_id = user_id
        self.attachment_service = AttachmentService()
        self.attachment_fetch_service = AttachmentFetchService()
        self.temp_files = []  # Track temporary files for cleanup
        self.current_attachment_data = None
        self.attachments = []  # Store fetched attachments
        self.fetch_thread = None
        
        self.setWindowTitle("📎 Email Attachments")
        self.setModal(True)
        self.resize(800, 600)
        
        self.init_ui()
        self.load_attachments()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Email info
        info_group = QGroupBox("📧 Email Information")
        info_layout = QFormLayout(info_group)
        
        self.email_subject = QLabel()
        self.email_sender = QLabel()
        self.email_date = QLabel()
        
        info_layout.addRow("Subject:", self.email_subject)
        info_layout.addRow("From:", self.email_sender)
        info_layout.addRow("Date:", self.email_date)
        
        layout.addWidget(info_group)
        
        # Loading progress
        self.loading_progress = QProgressBar()
        self.loading_progress.setVisible(False)
        layout.addWidget(self.loading_progress)
        
        # Main content area
        main_splitter = QSplitter(Qt.Horizontal)
        
        # Left panel - Attachment list
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        attachment_list_group = QGroupBox("📎 Attachments")
        attachment_list_layout = QVBoxLayout(attachment_list_group)
        
        self.attachment_list = QListWidget()
        self.attachment_list.itemClicked.connect(self.attachment_selected)
        attachment_list_layout.addWidget(self.attachment_list)
        
            # Blue button style
        blue_btn_style = """
            QPushButton {
                background-color: #3182ce;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: 500;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #2a4365;
            }
            QPushButton:pressed {
                background-color: #1e3250;
            }
            QPushButton:disabled {
                background-color: #90cdf4;  /* lighter blue when disabled */
                color: #e2e8f0;
            }
        """

        # Attachment actions
        action_layout = QHBoxLayout()

        self.view_btn = QPushButton("Open")
        self.view_btn.clicked.connect(self.open_attachment)
        self.view_btn.setEnabled(False)
        self.view_btn.setStyleSheet(blue_btn_style)

        self.save_btn = QPushButton("Save As...")
        self.save_btn.clicked.connect(self.save_attachment)
        self.save_btn.setEnabled(False)
        self.save_btn.setStyleSheet(blue_btn_style)

        self.save_all_btn = QPushButton("Save All...")
        self.save_all_btn.clicked.connect(self.save_all_attachments)
        self.save_all_btn.setEnabled(False)
        self.save_all_btn.setStyleSheet(blue_btn_style)
        action_layout.addWidget(self.view_btn)
        action_layout.addWidget(self.save_btn)
        action_layout.addWidget(self.save_all_btn)
        action_layout.addStretch()
        
        attachment_list_layout.addLayout(action_layout)
        left_layout.addWidget(attachment_list_group)
        
        # Right panel - Attachment viewer
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        viewer_group = QGroupBox("Attachment Viewer")
        viewer_layout = QVBoxLayout(viewer_group)
        
        self.attachment_info = QLabel("Select an attachment to view")
        self.attachment_info.setAlignment(Qt.AlignCenter)
        self.attachment_info.setStyleSheet("color: #666666; font-style: italic; padding: 10px;")
        self.attachment_info.setMinimumHeight(60)
        
        self.attachment_content = QTextEdit()
        self.attachment_content.setReadOnly(True)
        self.attachment_content.setVisible(False)
        self.attachment_content.setStyleSheet("""
            QTextEdit {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                padding: 8px;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 12px;
            }
        """)
        self.attachment_content.setMinimumHeight(300)
        
        self.attachment_image = QLabel()
        self.attachment_image.setAlignment(Qt.AlignCenter)
        self.attachment_image.setVisible(False)
        self.attachment_image.setMinimumHeight(300)
        self.attachment_image.setStyleSheet("""
            QLabel {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                padding: 10px;
            }
        """)
        
        viewer_layout.addWidget(self.attachment_info)
        viewer_layout.addWidget(self.attachment_content)
        viewer_layout.addWidget(self.attachment_image)
        
        right_layout.addWidget(viewer_group)
        
        # Add panels to splitter
        main_splitter.addWidget(left_panel)
        main_splitter.addWidget(right_panel)
        main_splitter.setSizes([300, 500])
        
        layout.addWidget(main_splitter)
        
                # Red button style
        red_btn_style = """
            QPushButton {
                background-color: #e53e3e;
                color: white;
                border: none;
                padding: 8px 16px;
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

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        close_btn.setStyleSheet(red_btn_style)
    def load_attachments(self):
        """Load attachments for the current email"""
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        try:
            # Get email info and account ID
            cursor.execute("""
                SELECT e.subject, e.sender, e.date, e.has_attachment, e.account_id
                FROM emails e
                WHERE e.id = %s
            """, (self.email_id,))
            
            result = cursor.fetchone()
            if not result:
                QMessageBox.warning(self, "Error", "Email not found.")
                return
                
            subject, sender, date, has_attachment, account_id = result
            
            # Update email info
            self.email_subject.setText(subject or "(No subject)")
            self.email_sender.setText(sender or "(Unknown sender)")
            self.email_date.setText(date.strftime("%Y-%m-%d %H:%M:%S") if date else "(No date)")
            
            if not has_attachment:
                self.attachment_list.addItem("No attachments found")
                return
            
            # Show loading progress
            self.loading_progress.setVisible(True)
            self.loading_progress.setRange(0, 0)  # Indeterminate progress
            
            # Start fetching attachments in background thread
            self.fetch_thread = AttachmentFetchThread(self.email_id, account_id)
            self.fetch_thread.attachments_loaded.connect(self.on_attachments_loaded)
            self.fetch_thread.error_occurred.connect(self.on_fetch_error)
            self.fetch_thread.start()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load email info: {str(e)}")
        finally:
            cursor.close()
            conn.close()

    def on_attachments_loaded(self, attachments):
        """Handle attachments loaded from background thread"""
        self.loading_progress.setVisible(False)
        self.attachments = attachments
        
        if not self.attachments:
            self.attachment_list.addItem("No attachments found")
            return
        
        # Display attachments in list
        for attachment in self.attachments:
            filename = attachment['filename']
            size = attachment['size_formatted']
            item = QListWidgetItem(f"📎 {filename} ({size})")
            item.setData(Qt.UserRole, attachment)  # Store attachment data
            self.attachment_list.addItem(item)
        
        # Enable save all button
        self.save_all_btn.setEnabled(True)

    def on_fetch_error(self, error_message):
        """Handle error from background thread"""
        self.loading_progress.setVisible(False)
        QMessageBox.critical(self, "Error", f"Failed to load attachments: {error_message}")
        self.attachment_list.addItem("Error loading attachments")

    def attachment_selected(self, item):
        """Handle attachment selection"""
        if item.text() == "No attachments found" or item.text() == "Error loading attachments":
            self.view_btn.setEnabled(False)
            self.save_btn.setEnabled(False)
            return
            
        self.view_btn.setEnabled(True)
        self.save_btn.setEnabled(True)
        
        # Get attachment data from item
        attachment_data = item.data(Qt.UserRole)
        if not attachment_data:
            return
        
        # Update attachment info
        filename = attachment_data['filename']
        size = attachment_data['size_formatted']
        self.attachment_info.setText(f"Selected: {filename}\nSize: {size}")
        
        # Store current attachment data for viewing/saving
        self.current_attachment_data = attachment_data

    def open_attachment(self):
        """Open attachment with default Windows application"""
        if not self.current_attachment_data:
            QMessageBox.warning(self, "No Selection", "Please select an attachment to view.")
            return
            
        try:
            filename = self.current_attachment_data['filename']
            temp_path = self.current_attachment_data.get('temp_path')
            
            if not temp_path or not os.path.exists(temp_path):
                QMessageBox.warning(self, "Error", "Attachment file not found or already cleaned up.")
                return
            
            print(f"Opening attachment: {filename}")
            print(f"Temp path: {temp_path}")
            print(f"File size: {os.path.getsize(temp_path)} bytes")
            
            # Open file with default Windows application
            os.startfile(temp_path)
            
            # Update attachment info to show it's opened
            self.attachment_info.setText(f"Opened: {filename}\nSize: {self.current_attachment_data['size_formatted']}\nOpened with default application")
            print(f"Opened '{filename}' with default application")
                
        except Exception as e:
            print(f"Error opening attachment: {e}")
            QMessageBox.critical(self, "Error", f"Failed to open attachment: {str(e)}")

    def save_attachment(self):
        """Save current attachment to custom path"""
        if not self.current_attachment_data:
            QMessageBox.warning(self, "No Selection", "Please select an attachment to save.")
            return
            
        filename = self.current_attachment_data['filename']
        temp_path = self.current_attachment_data.get('temp_path')
        
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
        
        if not save_path:
            return
            
        try:
            # Copy the temporary file to the user's chosen location
            import shutil
            shutil.copy2(temp_path, save_path)
            
            QMessageBox.information(self, "Success", 
                f"Attachment '{filename}' has been saved to:\n{save_path}")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save attachment: {str(e)}")

    def save_all_attachments(self):
        """Save all attachments to a selected folder"""
        if not self.attachments:
            QMessageBox.warning(self, "No Attachments", "No attachments to save.")
            return
        
        # Get folder from user
        folder = QFileDialog.getExistingDirectory(self, "Select Folder to Save All Attachments")
        
        if not folder:
            return
            
        try:
            import shutil
            saved_count = 0
            
            for attachment in self.attachments:
                temp_path = attachment.get('temp_path')
                if temp_path and os.path.exists(temp_path):
                    filename = attachment['filename']
                    filepath = os.path.join(folder, filename)
                    
                    # Copy the temporary file to the user's chosen location
                    shutil.copy2(temp_path, filepath)
                    saved_count += 1
            
            QMessageBox.information(self, "Success", 
                f"Saved {saved_count} attachments to:\n{folder}")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save attachments: {str(e)}")

    def get_mime_type(self, filename):
        """Get MIME type for filename"""
        mime_type, _ = mimetypes.guess_type(filename)
        return mime_type or 'application/octet-stream'

    def closeEvent(self, event):
        """Clean up temporary files when dialog is closed"""
        try:
            # Stop the fetch thread if it's running
            if self.fetch_thread and self.fetch_thread.isRunning():
                self.fetch_thread.terminate()
                self.fetch_thread.wait()
            
            # Clean up our temporary files
            for temp_file in self.temp_files:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
            
            # Clean up attachment fetch service temp files
            if hasattr(self, 'attachment_fetch_service'):
                self.attachment_fetch_service.cleanup_temp_files()
                
        except Exception as e:
            print(f"Error cleaning up temporary files: {e}")
        
        super().closeEvent(event) 