import os
import shutil
import datetime
import tempfile
import mimetypes
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QPushButton,
    QTextEdit, QGroupBox, QFrame, QGridLayout, QFileDialog, QMessageBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QSplitter, QScrollArea,
    QWidget, QSizePolicy
)
from PyQt5.QtCore import Qt, QSize, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QIcon
from styles.modern_style import ModernStyle
from utils.formatters import format_size
from views.dialogs.attachment_viewer_dialog import AttachmentViewerDialog
from services.attachment_fetch_service import AttachmentFetchService

class AttachmentFetchWorker(QThread):
    """Background worker for fetching attachments from IMAP"""
    finished = pyqtSignal(list)  # Signal with list of attachments
    error = pyqtSignal(str)      # Signal with error message
    
    def __init__(self, email_id, account_id, filename):
        super().__init__()
        self.email_id = email_id
        self.account_id = account_id
        self.filename = filename
        self.attachment_fetch_service = AttachmentFetchService()
    
    def run(self):
        """Run the IMAP fetch operation in background"""
        try:
            print(f"Background worker: Fetching attachments for email {self.email_id}")
            attachments = self.attachment_fetch_service.get_email_attachments(self.email_id, self.account_id)
            print(f"Background worker: Found {len(attachments)} attachments")
            
            # Find the specific attachment
            target_attachment = None
            for attachment in attachments:
                if attachment.get('filename') == self.filename:
                    target_attachment = attachment
                    break
            
            if target_attachment:
                self.finished.emit([target_attachment])
            else:
                self.error.emit(f"Attachment '{self.filename}' not found in email")
                
        except Exception as e:
            print(f"Background worker error: {e}")
            import traceback
            traceback.print_exc()
            self.error.emit(str(e))

class AttachmentDetailsDialog(QDialog):
    def __init__(self, attachment_data: dict, parent=None):
        super().__init__(parent)
        self.attachment_data = attachment_data
        self.attachment_fetch_service = AttachmentFetchService()
        self.temp_files = []  # Keep track of temp files created by this dialog
        self.worker = None  # Track background worker
        self.init_ui()
    
    def get_readable_mime_type(self, mime_type: str) -> str:
        """Convert MIME type to human-readable format"""
        if not mime_type:
            return "Unknown"
        
        # Common MIME type mappings
        mime_mappings = {
            'application/pdf': 'PDF Document',
            'application/msword': 'Microsoft Word Document',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'Microsoft Word Document (.docx)',
            'application/vnd.ms-excel': 'Microsoft Excel Spreadsheet',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'Microsoft Excel Spreadsheet (.xlsx)',
            'application/vnd.ms-powerpoint': 'Microsoft PowerPoint Presentation',
            'application/vnd.openxmlformats-officedocument.presentationml.presentation': 'Microsoft PowerPoint Presentation (.pptx)',
            'text/plain': 'Text File',
            'text/html': 'HTML Document',
            'image/jpeg': 'JPEG Image',
            'image/png': 'PNG Image',
            'image/gif': 'GIF Image',
            'application/zip': 'ZIP Archive',
            'application/x-rar-compressed': 'RAR Archive',
            'application/octet-stream': 'Binary File',
            'message/rfc822': 'Email Message',
            'multipart/mixed': 'Multipart Message',
            'multipart/alternative': 'Multipart Message',
            'multipart/related': 'Multipart Message'
        }
        
        # Check if we have a mapping
        if mime_type in mime_mappings:
            return mime_mappings[mime_type]
        
        # Try to get from mimetypes module
        try:
            readable_type = mimetypes.guess_type(f"file.{mime_type.split('/')[-1]}")[0]
            if readable_type:
                return readable_type.replace('/', ' ').title()
        except:
            pass
        
        # Fallback: format the MIME type nicely
        return mime_type.replace('/', ' ').title()
    
    def get_email_tags(self, email_id: int) -> list:
        """Get tags associated with the email"""
        try:
            import mysql.connector
            from config.database import DB_CONFIG
            
            conn = mysql.connector.connect(**DB_CONFIG)
            cursor = conn.cursor(dictionary=True)
            
            cursor.execute("""
                SELECT t.name, t.color
                FROM tags t
                JOIN email_tags et ON t.id = et.tag_id
                WHERE et.email_id = %s
                ORDER BY t.name
            """, (email_id,))
            
            tags = cursor.fetchall()
            cursor.close()
            conn.close()
            
            return tags
        except Exception as e:
            print(f"Error fetching tags: {e}")
            return []
    
    def init_ui(self):
        self.setWindowTitle("📎 Attachment Details")
        self.setModal(True)
        
        # Set window size
        self.resize(900, 700)
        
        # Apply modern styling
        self.setStyleSheet(ModernStyle.get_stylesheet())
        
        # Main layout
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        title_label = QLabel(f"📎 {self.attachment_data['filename']}")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #2196F3;")
        layout.addWidget(title_label)
        
        # Create splitter for main content
        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter, 1)
        
        # Left panel - Attachment info
        left_panel = self.create_attachment_info_panel()
        splitter.addWidget(left_panel)
        
        # Right panel - Email info
        right_panel = self.create_email_info_panel()
        splitter.addWidget(right_panel)
        
        # Set splitter proportions
        splitter.setSizes([400, 500])
        
        # Action buttons
        button_layout = QHBoxLayout()
        
                # View button
                # Button style (blue theme)
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
                background-color: #90cdf4;
                color: #e2e8f0;
            }
        """

        # View button
        self.view_button = QPushButton("View Attachment")
        self.view_button.clicked.connect(self.view_attachment)
        self.view_button.setStyleSheet(blue_btn_style)
        button_layout.addWidget(self.view_button)

        # Download button
        self.download_button = QPushButton("Download")
        self.download_button.clicked.connect(self.download_attachment)
        self.download_button.setStyleSheet(blue_btn_style)
        button_layout.addWidget(self.download_button)

        # Open File Path button
        self.open_path_button = QPushButton("Open File Path")
        self.open_path_button.clicked.connect(self.open_file_path)
        self.open_path_button.setStyleSheet(blue_btn_style)
        button_layout.addWidget(self.open_path_button)
        # Check if file exists and if this is an INBOX attachment
        is_inbox_attachment = self.attachment_data.get('is_inbox_attachment', False)
        file_exists = os.path.exists(self.attachment_data['file_path']) if self.attachment_data['file_path'] else False
        
        print(f"Attachment Details Dialog - Button initialization:")
        print(f"  Filename: {self.attachment_data.get('filename')}")
        print(f"  Is INBOX attachment: {is_inbox_attachment}")
        print(f"  File path: {self.attachment_data.get('file_path')}")
        print(f"  File exists: {file_exists}")
        
        # Configure buttons based on attachment type
        if is_inbox_attachment:
            print(f"  Enabling buttons - INBOX attachment")
            # For INBOX attachments, enable view/download, disable open path
            self.view_button.setEnabled(True)
            self.download_button.setEnabled(True)
            self.open_path_button.setEnabled(False)
            self.view_button.setToolTip("View attachment from IMAP server")
            self.download_button.setToolTip("Download attachment from IMAP server")
            self.open_path_button.setToolTip("Not available for server-based attachments")
        else:
            # For downloaded attachments
            if file_exists:
                print(f"  Enabling buttons - local file exists")
                self.view_button.setEnabled(True)
                self.download_button.setEnabled(True)
                self.open_path_button.setEnabled(True)
                self.view_button.setToolTip("View attachment file")
                self.download_button.setToolTip("Download attachment to custom location")
                self.open_path_button.setToolTip("Open file location in explorer")
            else:
                print(f"  Disabling buttons - file doesn't exist")
                self.view_button.setEnabled(False)
                self.download_button.setEnabled(False)
                self.open_path_button.setEnabled(False)
                self.view_button.setToolTip("File not found on disk")
                self.download_button.setToolTip("File not found on disk")
                self.open_path_button.setToolTip("File not found on disk")
        
        button_layout.addStretch()
        
                # Close button
            # Close button (red theme)
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

        close_button = QPushButton("Close")
        close_button.clicked.connect(self.close)
        close_button.setStyleSheet(red_btn_style)
        button_layout.addWidget(close_button)

        layout.addLayout(button_layout)
    
    def create_attachment_info_panel(self):
        """Create the attachment information panel"""
        panel = QGroupBox("📎 Attachment Information")
        layout = QVBoxLayout(panel)
        
        # Form layout for attachment details
        form_layout = QFormLayout()
        form_layout.setVerticalSpacing(10)
        form_layout.setHorizontalSpacing(15)
        
        # Check if this is an INBOX attachment
        is_inbox_attachment = self.attachment_data.get('is_inbox_attachment', False)
        
        # Filename
        filename_label = QLabel(self.attachment_data['filename'])
        filename_label.setWordWrap(True)
        form_layout.addRow("Filename:", filename_label)
        
        # File size
        size = self.attachment_data['file_size'] or 0
        size_label = QLabel(format_size(size))
        form_layout.addRow("Size:", size_label)
        
        # MIME type
        mime_type = self.attachment_data['mime_type'] or "Unknown"
        readable_mime = self.get_readable_mime_type(mime_type)
        mime_label = QLabel(readable_mime)
        form_layout.addRow("File Type:", mime_label)
        
        # Content type (show original if different from MIME type)
        content_type = self.attachment_data['content_type'] or "Unknown"
        if content_type != mime_type and content_type != "Unknown":
            readable_content = self.get_readable_mime_type(content_type)
            content_label = QLabel(readable_content)
            form_layout.addRow("Content Type:", content_label)
        
        if is_inbox_attachment:
            # For INBOX attachments, show IMAP information instead of file path
            form_layout.addRow("Location:", QLabel("INBOX (IMAP Server)"))
            form_layout.addRow("Status:", QLabel("Available on Server"))
            
            # Show account information
            account_email = self.attachment_data.get('account_email', 'Unknown')
            form_layout.addRow("📧 Account:", QLabel(account_email))
            
            imap_host = self.attachment_data.get('imap_host', 'Unknown')
            form_layout.addRow("🌐 IMAP Host:", QLabel(imap_host))
        else:
            # For downloaded attachments, show file path and status
            file_path = self.attachment_data['file_path']
            path_label = QLabel(file_path)
            path_label.setWordWrap(True)
            path_label.setStyleSheet("font-family: monospace; font-size: 11px; color: #666;")
            form_layout.addRow("📁 File Path:", path_label)
            
            # File exists status
            file_exists = os.path.exists(file_path)
            exists_label = QLabel("✅ Available" if file_exists else "❌ Not Found")
            exists_label.setStyleSheet("color: green;" if file_exists else "color: red;")
            form_layout.addRow("📂 Status:", exists_label)
        
        # Created date
        created_date = self.attachment_data['attachment_created']
        if created_date:
            created_str = created_date.strftime("%Y-%m-%d %H:%M:%S")
        else:
            created_str = "Unknown"
        created_label = QLabel(created_str)
        form_layout.addRow("Created:", created_label)
        
        layout.addLayout(form_layout)
        
        # Other attachments from same email
        other_attachments = self.attachment_data.get('other_attachments', [])
        if other_attachments:
            other_group = QGroupBox("📎 Other Attachments from Same Email")
            other_layout = QVBoxLayout(other_group)
            
            other_table = QTableWidget()
            other_table.setColumnCount(3)
            other_table.setHorizontalHeaderLabels(["Filename", "Size", "Type"])
            
            other_table.setRowCount(len(other_attachments))
            for row, attachment in enumerate(other_attachments):
                other_table.setItem(row, 0, QTableWidgetItem(attachment['filename']))
                other_table.setItem(row, 1, QTableWidgetItem(format_size(attachment['file_size'] or 0)))
                other_table.setItem(row, 2, QTableWidgetItem(attachment['mime_type'] or "Unknown"))
            
            header = other_table.horizontalHeader()
            header.setSectionResizeMode(0, QHeaderView.Stretch)
            header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
            
            other_table.setMaximumHeight(150)
            other_layout.addWidget(other_table)
            
            layout.addWidget(other_group)
        
        return panel
    
    def create_email_info_panel(self):
        """Create the email information panel"""
        panel = QGroupBox("📧 Email Information")
        layout = QVBoxLayout(panel)
        
        # Form layout for email details
        form_layout = QFormLayout()
        form_layout.setVerticalSpacing(10)
        form_layout.setHorizontalSpacing(15)
        
        # Subject
        subject = self.attachment_data['subject'] or "No Subject"
        subject_label = QLabel(subject)
        subject_label.setWordWrap(True)
        form_layout.addRow("📧 Subject:", subject_label)
        
        # Sender
        sender = self.attachment_data['sender'] or "Unknown"
        sender_label = QLabel(sender)
        sender_label.setWordWrap(True)
        form_layout.addRow("👤 Sender:", sender_label)
        
        # Recipients
        recipients = self.attachment_data['recipients'] or "Unknown"
        recipients_label = QLabel(recipients)
        recipients_label.setWordWrap(True)
        form_layout.addRow("👥 Recipients:", recipients_label)
        
        # Date
        email_date = self.attachment_data['email_date']
        if email_date:
            date_str = email_date.strftime("%Y-%m-%d %H:%M:%S")
        else:
            date_str = "Unknown"
        date_label = QLabel(date_str)
        form_layout.addRow("📅 Date:", date_label)
        
        # Email size
        email_size = self.attachment_data['email_size'] or 0
        email_size_label = QLabel(format_size(email_size))
        form_layout.addRow("Email Size:", email_size_label)
        
        # Priority
        priority = self.attachment_data['priority'] or "normal"
        priority_label = QLabel(priority.title())
        form_layout.addRow("Priority:", priority_label)
        
        # Read status
        read_status = self.attachment_data['read_status']
        read_label = QLabel("✅ Read" if read_status else "📧 Unread")
        read_label.setStyleSheet("color: green;" if read_status else "color: blue;")
        form_layout.addRow("Status:", read_label)
        
        # Account
        account = self.attachment_data['account_email'] or "Unknown"
        account_label = QLabel(account)
        form_layout.addRow("📧 Account:", account_label)
        
        # IMAP Host
        imap_host = self.attachment_data['imap_host'] or "Unknown"
        host_label = QLabel(imap_host)
        form_layout.addRow("🌐 IMAP Host:", host_label)
        
        # Tags
        tags = self.get_email_tags(self.attachment_data['email_id'])
        if tags:
            tags_text = ", ".join([f"🏷️ {tag['name']}" for tag in tags])
            tags_label = QLabel(tags_text)
            tags_label.setWordWrap(True)
            form_layout.addRow("🏷️ Tags:", tags_label)
        else:
            tags_label = QLabel("No tags")
            tags_label.setStyleSheet("color: #999;")
            form_layout.addRow("🏷️ Tags:", tags_label)
        
        layout.addLayout(form_layout)
        
        # Email body
        body_group = QGroupBox("📝 Email Body")
        body_layout = QVBoxLayout(body_group)
        
        body_text = QTextEdit()
        body_text.setReadOnly(True)
        body_text.setMaximumHeight(200)
        
        email_body = self.attachment_data['body'] or "No body content"
        # Truncate if too long
        if len(email_body) > 1000:
            email_body = email_body[:1000] + "...\n\n[Content truncated]"
        
        body_text.setPlainText(email_body)
        body_layout.addWidget(body_text)
        
        layout.addWidget(body_group)
        
        return panel
    
    def view_attachment(self):
        """Open attachment with default Windows application (same as Email Actions)"""
        file_path = self.attachment_data['file_path']
        filename = self.attachment_data['filename']
        is_inbox_attachment = self.attachment_data.get('is_inbox_attachment', False)
        
        print(f"View attachment called for: {filename}")
        print(f"Is INBOX attachment: {is_inbox_attachment}")
        print(f"File path: {file_path}")
        print(f"File exists: {os.path.exists(file_path) if file_path else False}")
        
        # For INBOX attachments, fetch from IMAP in background
        if is_inbox_attachment or not os.path.exists(file_path):
            try:
                print("Starting background IMAP fetch...")
                
                # Get email and account info
                email_id = self.attachment_data['email_id']
                account_id = self.get_account_id_from_email(email_id)
                
                print(f"Email ID: {email_id}, Account ID: {account_id}")
                
                if not account_id:
                    QMessageBox.warning(self, "Error", 
                                      "Could not determine account for this email")
                    return
                
                # Disable buttons during fetch
                self.view_button.setEnabled(False)
                self.download_button.setEnabled(False)
                self.view_button.setText("Fetching...")
                
                # Create and start background worker
                self.worker = AttachmentFetchWorker(email_id, account_id, filename)
                self.worker.finished.connect(self.on_attachment_fetched_for_view)
                self.worker.error.connect(self.on_attachment_fetch_error)
                self.worker.start()
                    
            except Exception as e:
                print(f"Error starting background fetch: {e}")
                import traceback
                traceback.print_exc()
                QMessageBox.critical(self, "Error", 
                                   f"Failed to start attachment fetch: {str(e)}")
                # Re-enable buttons
                self.view_button.setEnabled(True)
                self.download_button.setEnabled(True)
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
                    background-color: #90cdf4;
                    color: #e2e8f0;
                }
            """

            # Update text and style
            self.view_button.setText("View Attachment")
            self.view_button.setStyleSheet(blue_btn_style)
        else:
            # For downloaded attachments, open local file
            try:
                print(f"Opening local file: {file_path}")
                # Open file with default Windows application
                os.startfile(file_path)
                QMessageBox.information(self, "Success", 
                                      f"Opened '{filename}' with default application")
            except Exception as e:
                print(f"Error opening local file: {e}")
                QMessageBox.critical(self, "Error", 
                                   f"Failed to open attachment: {str(e)}")
    
    def on_attachment_fetched_for_view(self, attachments):
        """Handle successful attachment fetch for viewing"""
        try:
            target_attachment = attachments[0]
            filename = self.attachment_data['filename']
            
            # Create temporary file and open it
            temp_path = target_attachment.get('temp_path')
            print(f"Temp path: {temp_path}")
            print(f"Temp file exists: {os.path.exists(temp_path) if temp_path else False}")
            
            if temp_path and os.path.exists(temp_path):
                print(f"Opening file: {temp_path}")
                # Add to our temp files list to prevent cleanup
                self.temp_files.append(temp_path)
                os.startfile(temp_path)
                QMessageBox.information(self, "Success", 
                                      f"Opened '{filename}' with default application")
            else:
                QMessageBox.warning(self, "Error", 
                                  "Failed to create temporary file for viewing")
                
        except Exception as e:
            print(f"Error in on_attachment_fetched_for_view: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Error", 
                               f"Failed to open attachment: {str(e)}")
        finally:
            # Re-enable buttons
            self.view_button.setEnabled(True)
            self.download_button.setEnabled(True)
            self.view_button.setText("View Attachment")
    
    def on_attachment_fetch_error(self, error_message):
        """Handle attachment fetch error"""
        print(f"Attachment fetch error: {error_message}")
        QMessageBox.critical(self, "Error", 
                           f"Failed to fetch attachment: {error_message}")
        # Re-enable buttons
        self.view_button.setEnabled(True)
        self.download_button.setEnabled(True)
    
    def get_account_id_from_email(self, email_id: int) -> int:
        """Get account ID for an email"""
        try:
            import mysql.connector
            from config.database import DB_CONFIG
            
            conn = mysql.connector.connect(**DB_CONFIG)
            cursor = conn.cursor()
            
            cursor.execute("SELECT account_id FROM emails WHERE id = %s", (email_id,))
            result = cursor.fetchone()
            
            cursor.close()
            conn.close()
            
            account_id = result[0] if result else None
            print(f"Account ID for email {email_id}: {account_id}")
            return account_id
        except Exception as e:
            print(f"Error getting account ID: {e}")
            return None
    
    def download_attachment(self):
        """Download attachment to custom path"""
        file_path = self.attachment_data['file_path']
        filename = self.attachment_data['filename']
        is_inbox_attachment = self.attachment_data.get('is_inbox_attachment', False)
        
        print(f"Download attachment called for: {filename}")
        print(f"Is INBOX attachment: {is_inbox_attachment}")
        
        # For INBOX attachments, fetch from IMAP first
        if is_inbox_attachment or not os.path.exists(file_path):
            try:
                print("Starting background IMAP fetch for download...")
                
                # Get email and account info
                email_id = self.attachment_data['email_id']
                account_id = self.get_account_id_from_email(email_id)
                
                print(f"Email ID: {email_id}, Account ID: {account_id}")
                
                if not account_id:
                    QMessageBox.warning(self, "Error", 
                                      "Could not determine account for this email")
                    return
                
                # Disable buttons during fetch
                self.view_button.setEnabled(False)
                self.download_button.setEnabled(False)
                self.download_button.setText("⏳ Fetching...")
                
                # Create and start background worker
                self.worker = AttachmentFetchWorker(email_id, account_id, filename)
                self.worker.finished.connect(self.on_attachment_fetched_for_download)
                self.worker.error.connect(self.on_attachment_fetch_error_download)
                self.worker.start()
                        
            except Exception as e:
                print(f"Error starting background fetch for download: {e}")
                import traceback
                traceback.print_exc()
                QMessageBox.critical(self, "Download Error", 
                                   f"Failed to start attachment fetch: {str(e)}")
                # Re-enable buttons
                self.view_button.setEnabled(True)
                self.download_button.setEnabled(True)
                self.download_button.setText("💾 Download")
        else:
            # For downloaded attachments, copy from local file
            # Get save path from user
            save_path, _ = QFileDialog.getSaveFileName(
                self,
                "Save Attachment",
                filename,
                "All Files (*.*)"
            )
            
            if save_path:
                try:
                    print(f"Copying local file from {file_path} to {save_path}")
                    # Copy file to selected location
                    shutil.copy2(file_path, save_path)
                    QMessageBox.information(self, "Download Complete", 
                                          f"Attachment saved to:\n{save_path}")
                except Exception as e:
                    print(f"Error copying local file: {e}")
                    QMessageBox.critical(self, "Download Error", 
                                       f"Error saving attachment:\n{str(e)}")
    
    def on_attachment_fetched_for_download(self, attachments):
        """Handle successful attachment fetch for download"""
        try:
            target_attachment = attachments[0]
            filename = self.attachment_data['filename']
            
            # Get save path from user
            save_path, _ = QFileDialog.getSaveFileName(
                self,
                "Save Attachment",
                filename,
                "All Files (*.*)"
            )
            
            if save_path:
                # Copy temporary file to selected location
                temp_path = target_attachment.get('temp_path')
                print(f"Temp path for download: {temp_path}")
                print(f"Temp file exists: {os.path.exists(temp_path) if temp_path else False}")
                
                if temp_path and os.path.exists(temp_path):
                    shutil.copy2(temp_path, save_path)
                    print(f"Successfully copied to: {save_path}")
                    QMessageBox.information(self, "Download Complete", 
                                          f"Attachment saved to:\n{save_path}")
                else:
                    QMessageBox.warning(self, "Error", 
                                      "Failed to create temporary file for download")
                    
        except Exception as e:
            print(f"Error in on_attachment_fetched_for_download: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Download Error", 
                               f"Error downloading attachment:\n{str(e)}")
        finally:
            # Re-enable buttons
            self.view_button.setEnabled(True)
            self.download_button.setEnabled(True)
            self.download_button.setText("💾 Download")
    
    def on_attachment_fetch_error_download(self, error_message):
        """Handle attachment fetch error for download"""
        print(f"Attachment fetch error for download: {error_message}")
        QMessageBox.critical(self, "Download Error", 
                           f"Failed to fetch attachment: {error_message}")
        # Re-enable buttons
        self.view_button.setEnabled(True)
        self.download_button.setEnabled(True)
        self.download_button.setText("💾 Download")
    
    def open_file_path(self):
        """Open the file path in the default file explorer"""
        file_path = self.attachment_data['file_path']
        if file_path and os.path.exists(file_path):
            try:
                print(f"Opening file path: {file_path}")
                # Get the directory containing the file
                file_dir = os.path.dirname(file_path)
                os.startfile(file_dir)
                QMessageBox.information(self, "Success", 
                                      f"Opened file location:\n{file_dir}")
            except Exception as e:
                print(f"Error opening file path: {e}")
                QMessageBox.critical(self, "Error", 
                                   f"Failed to open file location:\n{str(e)}")
        else:
            QMessageBox.warning(self, "Warning", 
                               f"File path '{file_path}' not found or does not exist.")
    
    def closeEvent(self, event):
        """Handle dialog closing"""
        # Clean up background worker
        if self.worker and self.worker.isRunning():
            self.worker.quit()
            self.worker.wait()
        
        # Clean up temp files when dialog closes
        try:
            for temp_file in self.temp_files:
                if os.path.exists(temp_file):
                    try:
                        os.unlink(temp_file)
                        print(f"Cleaned up temp file: {temp_file}")
                    except Exception as e:
                        print(f"Error cleaning up temp file {temp_file}: {e}")
        except Exception as e:
            print(f"Error during cleanup: {e}")
        
        event.accept() 