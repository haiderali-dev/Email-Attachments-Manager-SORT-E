import os
import shutil
import hashlib
import mimetypes
import mysql.connector
from datetime import datetime
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit, 
    QPushButton, QMessageBox, QGroupBox, QComboBox, QTextEdit, 
    QFileDialog, QApplication, QLabel, QProgressBar, QCheckBox,
    QListWidget, QListWidgetItem, QSplitter, QFrame
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from config.database import DB_CONFIG
from utils.formatters import format_size
from utils.helpers import get_safe_filename, create_directory_if_not_exists

class AttachmentFetchWorker(QThread):
    """Worker thread for fetching attachments directly from IMAP server"""
    progress = pyqtSignal(str)
    file_conflict = pyqtSignal(str, str, str)  # original_name, device_path, conflict_type
    finished = pyqtSignal(int, int, list)  # saved_count, skipped_count, errors
    error = pyqtSignal(str)
    
    def __init__(self, tag_id, user_id, save_path, conflict_resolution):
        super().__init__()
        self.tag_id = tag_id
        self.user_id = user_id
        self.save_path = save_path
        self.conflict_resolution = conflict_resolution  # 'latest', 'version', 'replace'
        self.should_stop = False
        self.conflict_responses = {}  # Store user responses for conflicts
        
    def set_conflict_response(self, original_name, response):
        """Set user response for a file conflict"""
        self.conflict_responses[original_name] = response
        
    def stop(self):
        """Stop the worker thread"""
        self.should_stop = True
        
    def run(self):
        try:
            conn = mysql.connector.connect(**DB_CONFIG)
            cursor = conn.cursor(dictionary=True)
            
            # Get all emails with the specified tag and their account details
            cursor.execute("""
                SELECT DISTINCT e.id, e.subject, e.sender, e.date, e.uid, e.has_attachment,
                       a.id as account_id, a.imap_host, a.imap_port, a.email, a.encrypted_password
                FROM emails e
                INNER JOIN email_tags et ON e.id = et.email_id
                INNER JOIN accounts a ON e.account_id = a.id
                WHERE et.tag_id = %s AND a.dashboard_user_id = %s
                ORDER BY e.date DESC
            """, (self.tag_id, self.user_id))
            
            emails = cursor.fetchall()
            if not emails:
                self.progress.emit("No emails found for this tag")
                self.finished.emit(0, 0, [])
                return
                
            self.progress.emit(f"Found {len(emails)} emails for this tag")
            
            # Create save directory
            if not create_directory_if_not_exists(self.save_path):
                self.error.emit("Failed to create save directory")
                return
                
            saved_count = 0
            skipped_count = 0
            errors = []
            
            # Get existing files in save directory
            existing_files = set()
            if os.path.exists(self.save_path):
                existing_files = set(os.listdir(self.save_path))
            
            # Track file versions for versioning
            file_versions = {}
            
            # Group emails by account for efficient IMAP connections
            from collections import defaultdict
            account_emails = defaultdict(list)
            for email in emails:
                account_emails[email['account_id']].append(email)
            
            # Process each account
            for account_id, account_emails_list in account_emails.items():
                if self.should_stop:
                    break
                
                # Get account details
                account_email = account_emails_list[0]
                imap_host = account_email['imap_host']
                imap_port = account_email['imap_port']
                email_address = account_email['email']
                encrypted_password = account_email['encrypted_password']
                
                # Decrypt password
                from services.encryption_service import decrypt_text
                password = decrypt_text(encrypted_password)
                
                self.progress.emit(f"Connecting to {email_address}...")
                
                try:
                    # Connect to IMAP server
                    from imap_tools import MailBox, AND
                    with MailBox(imap_host, port=imap_port).login(email_address, password, 'INBOX') as mailbox:
                        self.progress.emit(f"Connected to {email_address}")
                        
                        # Process each email for this account
                        for email in account_emails_list:
                            if self.should_stop:
                                break
                                
                            self.progress.emit(f"Fetching attachments for: {email['subject']}")
                            
                            try:
                                # Get email from IMAP server using UID
                                uid = email['uid']
                                messages = list(mailbox.fetch(AND(uid=uid)))
                                
                                if not messages:
                                    errors.append(f"Email not found on server: {email['subject']}")
                                    continue
                                
                                msg = messages[0]
                                
                                # Check if email has attachments
                                if not hasattr(msg, 'attachments') or not msg.attachments:
                                    continue
                                
                                self.progress.emit(f"Found {len(msg.attachments)} attachments in: {email['subject']}")
                                
                                # Process each attachment
                                for attachment in msg.attachments:
                                    if self.should_stop:
                                        break
                                    
                                    try:
                                        original_filename = attachment.filename or f"attachment_{saved_count + 1}"
                                        
                                        # Start with original filename
                                        target_filename = original_filename
                                        
                                        # Check for conflicts
                                        if target_filename in existing_files:
                                            if self.conflict_resolution == 'latest':
                                                # Always overwrite with latest
                                                pass
                                            elif self.conflict_resolution == 'version':
                                                # Version the file - find next available version
                                                target_filename = self._get_versioned_filename(
                                                    original_filename, existing_files
                                                )
                                            elif self.conflict_resolution == 'replace':
                                                # Ask user for each conflict
                                                if original_filename not in self.conflict_responses:
                                                    # Emit signal to get user response
                                                    self.file_conflict.emit(
                                                        original_filename, 
                                                        os.path.join(self.save_path, target_filename),
                                                        'exists'
                                                    )
                                                    # Wait for response (this will be handled by the main thread)
                                                    while original_filename not in self.conflict_responses:
                                                        if self.should_stop:
                                                            return
                                                        self.msleep(100)
                                                    
                                                    response = self.conflict_responses[original_filename]
                                                    if response == 'skip':
                                                        skipped_count += 1
                                                        continue
                                                    elif response.startswith('custom:'):
                                                        # Use custom filename provided by user
                                                        custom_name = response[7:]  # Remove 'custom:' prefix
                                                        target_filename = custom_name
                                                        
                                                        # Check if custom name also conflicts
                                                        if target_filename in existing_files:
                                                            # Ask user again for this custom name conflict
                                                            self.file_conflict.emit(
                                                                custom_name,
                                                                os.path.join(self.save_path, target_filename),
                                                                'exists'
                                                            )
                                                            # Wait for response
                                                            while custom_name not in self.conflict_responses:
                                                                if self.should_stop:
                                                                    return
                                                                self.msleep(100)
                                                            
                                                            custom_response = self.conflict_responses[custom_name]
                                                            if custom_response == 'skip':
                                                                skipped_count += 1
                                                                continue
                                                            elif custom_response.startswith('custom:'):
                                                                target_filename = custom_response[7:]
                                                            elif custom_response == 'replace':
                                                                pass  # Use the custom name as is
                                                    elif response == 'rename':
                                                        target_filename = self._get_unique_filename(
                                                            original_filename, existing_files
                                                        )
                                        
                                        # Save attachment to target path
                                        target_path = os.path.join(self.save_path, target_filename)
                                        
                                        with open(target_path, 'wb') as f:
                                            f.write(attachment.payload)
                                        
                                        # Record device attachment - create attachment record if needed
                                        try:
                                            # Check if attachment exists in database
                                            cursor.execute("""
                                                SELECT id FROM attachments 
                                                WHERE email_id = %s AND filename = %s
                                            """, (email['id'], original_filename))
                                            
                                            attachment_record = cursor.fetchone()
                                            attachment_id = None
                                            
                                            if attachment_record:
                                                # Use existing attachment record
                                                attachment_id = attachment_record['id']
                                            else:
                                                # Create new attachment record since we're fetching from server
                                                from models.attachment import Attachment
                                                new_attachment = Attachment.create_attachment(
                                                    email_id=email['id'],
                                                    filename=original_filename,
                                                    file_path=target_path,  # Use the saved path
                                                    file_size=len(attachment.payload),
                                                    mime_type=getattr(attachment, 'content_type', None)
                                                )
                                                if new_attachment:
                                                    attachment_id = new_attachment.id
                                            
                                            # Record device attachment if we have an attachment ID
                                            if attachment_id:
                                                from models.attachment import Attachment
                                                Attachment.create_device_attachment(
                                                    attachment_id,
                                                    original_filename,
                                                    target_filename,
                                                    target_path
                                                )
                                                self.progress.emit(f"Recorded device attachment: {target_filename}")
                                        except Exception as db_error:
                                            # Continue even if we can't record in database
                                            self.progress.emit(f"Warning: Could not record device attachment for {target_filename}")
                                            pass
                                        
                                        # Update tracking
                                        existing_files.add(target_filename)
                                        if target_filename not in file_versions:
                                            file_versions[target_filename] = 1
                                        else:
                                            file_versions[target_filename] += 1
                                        
                                        saved_count += 1
                                        self.progress.emit(f"Saved: {target_filename}")
                                        
                                    except Exception as e:
                                        errors.append(f"Error processing attachment {original_filename}: {str(e)}")
                                        continue
                                        
                            except Exception as e:
                                errors.append(f"Error processing email {email['subject']}: {str(e)}")
                                continue
                                
                except Exception as e:
                    errors.append(f"Error connecting to {email_address}: {str(e)}")
                    continue
            
            cursor.close()
            conn.close()
            
            if not self.should_stop:
                self.finished.emit(saved_count, skipped_count, errors)
            else:
                self.finished.emit(saved_count, skipped_count, errors + ["Operation cancelled"])
                
        except Exception as e:
            self.error.emit(f"Error: {str(e)}")
    

    
    def _get_versioned_filename(self, original_filename, existing_files):
        """Get versioned filename by finding the next sequential version"""
        name, ext = os.path.splitext(original_filename)
        
        # Find the highest existing version number
        max_version = 0
        for existing_file in existing_files:
            if existing_file.startswith(name + "_") and existing_file.endswith(ext):
                try:
                    version_part = existing_file[len(name + "_"):-len(ext)]
                    version_num = int(version_part)
                    max_version = max(max_version, version_num)
                except ValueError:
                    continue
        
        # Return the next version
        return f"{name}_{max_version + 1}{ext}"
    
    def _get_unique_filename(self, original_filename, existing_files):
        """Get unique filename by finding the next available number"""
        name, ext = os.path.splitext(original_filename)
        
        # Find the highest existing number
        max_number = 0
        for existing_file in existing_files:
            if existing_file.startswith(name + "_") and existing_file.endswith(ext):
                try:
                    number_part = existing_file[len(name + "_"):-len(ext)]
                    number = int(number_part)
                    max_number = max(max_number, number)
                except ValueError:
                    continue
        
        # Return the next available number
        return f"{name}_{max_number + 1}{ext}"

class TagAttachmentsDialog(QDialog):
    def __init__(self, parent, user_id):
        super().__init__(parent)
        self.user_id = user_id
        self.selected_tag_id = None
        self.fetch_worker = None
        self.conflict_responses = {}
        
        self.setWindowTitle("Fetch Attachments from Server by Tag")
        self.setModal(True)
        self.resize(600, 500)
        
        self.init_ui()
        self.load_tags()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Apply modern styling
        self.setStyleSheet("""
            QDialog {
                background-color: #ffffff;
                color: #2d3748;
            }
            QGroupBox {
                font-weight: 600;
                border: 2px solid #e2e8f0;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 10px;
                color: #2d3748;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 10px 0 10px;
                background-color: #f8fafc;
                color: #2d3748;
            }
            QLabel {
                color: #2d3748;
                font-size: 11pt;
            }
            QPushButton {
                background-color: #3182ce;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: 500;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #2a4365;
            }
            QPushButton:pressed {
                background-color: #1e3250;
            }
            QPushButton:disabled {
                background-color: #a0aec0;
                color: #e2e8f0;
            }
            QPushButton[class="success"] {
                background-color: #4299e1;  /* Light Blue */
                color: white;
            }
            QPushButton[class="success"]:hover {
                background-color: #2b6cb0;  /* Dark Blue */
            }
            QPushButton[class="warning"] {
                background-color: #ed8936;
            }
            QPushButton[class="warning"]:hover {
                background-color: #dd6b20;
            }
            QPushButton[class="danger"] {
                background-color: #e53e3e;
            }
            QPushButton[class="danger"]:hover {
                background-color: #c53030;
            }
            QComboBox {
                border: 2px solid #e2e8f0;
                border-radius: 6px;
                padding: 6px 12px;
                background-color: white;
                color: #2d3748;
            }
            QComboBox:focus {
                border-color: #3182ce;
            }
            QLineEdit {
                border: 2px solid #e2e8f0;
                border-radius: 6px;
                padding: 6px 12px;
                background-color: white;
                color: #2d3748;
            }
            QLineEdit:focus {
                border-color: #3182ce;
            }
            QProgressBar {
                border: 2px solid #e2e8f0;
                border-radius: 6px;
                text-align: center;
                background-color: #f7fafc;
            }
            QProgressBar::chunk {
                background-color: #3182ce;
                border-radius: 4px;
            }
        """)

        
        # Tag selection
        tag_group = QGroupBox("Select Tag")
        tag_layout = QFormLayout(tag_group)
        
        self.tag_combo = QComboBox()
        self.tag_combo.currentIndexChanged.connect(self.tag_selection_changed)
        tag_layout.addRow("Tag:", self.tag_combo)
        
        # Tag info
        self.tag_info_label = QLabel("Select a tag to see attachment information")
        self.tag_info_label.setWordWrap(True)
        tag_layout.addRow("Info:", self.tag_info_label)
        
        layout.addWidget(tag_group)
        
        # Save settings
        save_group = QGroupBox("Save Settings")
        save_layout = QFormLayout(save_group)
        
        # Save path
        path_layout = QHBoxLayout()
        self.save_path = QLineEdit()
        self.save_path.setPlaceholderText("Select folder to save attachments...")
        
        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self.browse_save_path)
        browse_btn.setProperty("class", "success")  # Green color for browse button
        
        path_layout.addWidget(self.save_path)
        path_layout.addWidget(browse_btn)
        save_layout.addRow("Save Path:", path_layout)
        
        # Conflict resolution
        self.conflict_combo = QComboBox()
        self.conflict_combo.addItems([
            "Store the latest file",
            "Version it (file_1.pdf, file_2.pdf, etc.)",
            "Replace or Custom Name (ask for each conflict)"
        ])
        save_layout.addRow("Conflict Resolution:", self.conflict_combo)
        
        layout.addWidget(save_group)
        
        # Progress
        progress_group = QGroupBox("Progress")
        progress_layout = QVBoxLayout(progress_group)
        
        self.progress_label = QLabel("Ready to fetch attachments from email server")
        progress_layout.addWidget(self.progress_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        progress_layout.addWidget(self.progress_bar)
        
        layout.addWidget(progress_group)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        self.fetch_btn = QPushButton("Fetch Attachments from Server")
        self.fetch_btn.clicked.connect(self.start_fetch)
        self.fetch_btn.setEnabled(False)
        self.fetch_btn.setProperty("class", "success")  # Green color for fetch button
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setProperty("class", "danger")  # Red color for cancel button
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.fetch_btn)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
    
    def load_tags(self):
        """Load available tags for the user"""
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        try:
            cursor.execute("""
                SELECT t.id, t.name, t.color, COUNT(DISTINCT et.email_id) as email_count
                FROM tags t
                LEFT JOIN email_tags et ON t.id = et.tag_id
                LEFT JOIN emails e ON et.email_id = e.id
                LEFT JOIN accounts a ON e.account_id = a.id
                WHERE t.dashboard_user_id = %s AND (a.dashboard_user_id = %s OR a.dashboard_user_id IS NULL)
                GROUP BY t.id, t.name, t.color
                ORDER BY t.name
            """, (self.user_id, self.user_id))
            
            tags = cursor.fetchall()
            
            self.tag_combo.clear()
            self.tag_combo.addItem("Select a tag...", None)
            
            for tag in tags:
                display_text = f"{tag['name']} ({tag['email_count']} emails)"
                self.tag_combo.addItem(display_text, tag['id'])
                
        finally:
            cursor.close()
            conn.close()
    
    def tag_selection_changed(self):
        """Handle tag selection change"""
        tag_id = self.tag_combo.currentData()
        self.selected_tag_id = tag_id
        
        if tag_id:
            self.update_tag_info(tag_id)
            self.fetch_btn.setEnabled(bool(self.save_path.text().strip()))
        else:
            self.tag_info_label.setText("Select a tag to see attachment information")
            self.fetch_btn.setEnabled(False)
    
    def update_tag_info(self, tag_id):
        """Update tag information display"""
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        try:
            # Get tag details and email count
            cursor.execute("""
                SELECT t.name, COUNT(DISTINCT e.id) as email_count
                FROM tags t
                LEFT JOIN email_tags et ON t.id = et.tag_id
                LEFT JOIN emails e ON et.email_id = e.id
                LEFT JOIN accounts a ON e.account_id = a.id
                WHERE t.id = %s AND t.dashboard_user_id = %s
                GROUP BY t.id, t.name
            """, (tag_id, self.user_id))
            
            result = cursor.fetchone()
            if result:
                info_text = f"Tag: {result['name']}\n"
                info_text += f"Emails: {result['email_count']}\n"
                info_text += f"📎 Will fetch attachments directly from email server\n"
                info_text += f"💡 No pre-downloaded files required"
                
                self.tag_info_label.setText(info_text)
            else:
                self.tag_info_label.setText("Tag not found")
                
        finally:
            cursor.close()
            conn.close()
    
    def browse_save_path(self):
        """Browse for save path"""
        folder = QFileDialog.getExistingDirectory(self, "Select Folder to Save Attachments")
        if folder:
            self.save_path.setText(folder)
            self.fetch_btn.setEnabled(bool(self.selected_tag_id))
    
    def start_fetch(self):
        """Start fetching attachments"""
        if not self.selected_tag_id:
            QMessageBox.warning(self, "No Tag Selected", "Please select a tag first.")
            return
            
        if not self.save_path.text().strip():
            QMessageBox.warning(self, "No Save Path", "Please select a save path first.")
            return
        
        # Get conflict resolution strategy
        conflict_index = self.conflict_combo.currentIndex()
        conflict_strategies = ['latest', 'version', 'replace']
        conflict_strategy = conflict_strategies[conflict_index]
        
        # Create and start worker
        self.fetch_worker = AttachmentFetchWorker(
            self.selected_tag_id,
            self.user_id,
            self.save_path.text().strip(),
            conflict_strategy
        )
        
        self.fetch_worker.progress.connect(self.update_progress)
        self.fetch_worker.file_conflict.connect(self.handle_file_conflict)
        self.fetch_worker.finished.connect(self.fetch_finished)
        self.fetch_worker.error.connect(self.fetch_error)
        
        # Update UI
        self.fetch_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        
        self.fetch_worker.start()
    
    def update_progress(self, message):
        """Update progress message"""
        self.progress_label.setText(message)
    
    def handle_file_conflict(self, original_name, device_path, conflict_type):
        """Handle file conflict by asking user"""
        if conflict_type == 'exists':
            # Create custom dialog for better user experience
            from PyQt5.QtWidgets import QInputDialog
            
            # Show options dialog first
            response = QMessageBox.question(
                self,
                "File Conflict",
                f"File '{original_name}' already exists at:\n{device_path}\n\nWhat would you like to do?\n\nYes = Replace existing file\nNo = Save with custom name\nCancel = Skip this file",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
                QMessageBox.Yes
            )
            
            if response == QMessageBox.Yes:
                # Replace
                self.fetch_worker.set_conflict_response(original_name, 'replace')
            elif response == QMessageBox.No:
                # Ask for custom name
                name, ext = os.path.splitext(original_name)
                custom_name, ok = QInputDialog.getText(
                    self,
                    "Enter Custom Filename",
                    f"Enter a custom name for '{original_name}':",
                    text=f"{name}_custom{ext}"
                )
                
                if ok and custom_name.strip():
                    # Store the custom name
                    self.fetch_worker.set_conflict_response(original_name, f'custom:{custom_name.strip()}')
                else:
                    # User cancelled or entered empty name, skip
                    self.fetch_worker.set_conflict_response(original_name, 'skip')
            else:
                # Skip
                self.fetch_worker.set_conflict_response(original_name, 'skip')
    
    def fetch_finished(self, saved_count, skipped_count, errors):
        """Handle fetch completion"""
        self.progress_bar.setVisible(False)
        self.fetch_btn.setEnabled(True)
        
        # Show results
        message = f"Fetch completed!\n\n"
        message += f"✅ Saved: {saved_count} files\n"
        message += f"⏭️ Skipped: {skipped_count} files\n"
        
        if errors:
            message += f"\n❌ Errors ({len(errors)}):\n"
            for error in errors[:5]:  # Show first 5 errors
                message += f"• {error}\n"
            if len(errors) > 5:
                message += f"• ... and {len(errors) - 5} more errors"
        
        QMessageBox.information(self, "Fetch Complete", message)
        
        if saved_count > 0:
            self.accept()
    
    def fetch_error(self, error_message):
        """Handle fetch error"""
        self.progress_bar.setVisible(False)
        self.fetch_btn.setEnabled(True)
        QMessageBox.critical(self, "Fetch Error", f"Error: {error_message}")
    
    def closeEvent(self, event):
        """Handle dialog closing"""
        if self.fetch_worker and self.fetch_worker.isRunning():
            self.fetch_worker.stop()
            self.fetch_worker.wait()
        event.accept()
