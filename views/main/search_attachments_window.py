import os
import datetime
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QPushButton, QMessageBox, QLabel, QTableWidget,
    QTableWidgetItem, QHeaderView, QComboBox, QGroupBox, QFrame,
    QGridLayout, QSizePolicy, QSpacerItem, QApplication, QFileDialog,
    QProgressBar, QTextEdit, QSplitter
)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QSize
from PyQt5.QtGui import QFont, QIcon, QPalette, QColor
from PyQt5 import QtWidgets, QtCore
from models.attachment import Attachment
from styles.modern_style import ModernStyle
from views.dialogs.attachment_details_dialog import AttachmentDetailsDialog
from views.dialogs.email_attachments_list_dialog import EmailAttachmentsListDialog
from utils.formatters import format_size

class SearchAttachmentsWorker(QThread):
    """Worker thread for searching attachments"""
    search_completed = pyqtSignal(list)
    search_error = pyqtSignal(str)
    
    def __init__(self, search_query: str, user_id: int, source: str = "device", account_id: int = None):
        super().__init__()
        self.search_query = search_query
        self.user_id = user_id
        self.source = source  # "inbox", "device", or "all"
        self.account_id = account_id
    
    def run(self):
        try:
            if self.source == "inbox" or self.source == "all":
                # Search all attachments from IMAP (including downloaded ones for "all")
                results = Attachment.search_all_attachments(
                    self.search_query, 
                    self.user_id, 
                    self.account_id
                )
                
                if self.source == "inbox":
                    # For INBOX only, filter to show only non-downloaded attachments
                    # (those without attachment_id - server-based only)
                    results = [r for r in results if r.get('attachment_id') is None]
                    
            else:  # device
                # Search only downloaded attachments
                results = Attachment.search_attachments(
                    self.search_query, 
                    self.user_id, 
                    self.account_id
                )
                
            self.search_completed.emit(results)
            
        except Exception as e:
            print(f"Search worker error: {e}")
            import traceback
            traceback.print_exc()
            self.search_error.emit(str(e))

class SearchAttachmentsWindow(QMainWindow):
    def __init__(self, user_id: int, parent=None):
        super().__init__(parent)
        self.user_id = user_id
        self.current_account_id = None
        self.search_results = []
        self.search_worker = None
        
        self.init_ui()
        self.load_user_accounts()
    
    def init_ui(self):
        self.setWindowTitle("🔍 Search Attachments")
        
        # Get screen size for responsive design
        screen = QApplication.desktop().screenGeometry()
        window_size = ModernStyle.get_responsive_size(QSize(1200, 800), screen.size())
        self.resize(window_size)
        
        # Center window
        self.move(screen.center() - self.rect().center())
        
        # Apply modern styling
        self.setStyleSheet(ModernStyle.get_stylesheet())
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Search panel
        search_panel = self.create_search_panel()
        main_layout.addWidget(search_panel)
        
        # Results panel
        results_panel = self.create_results_panel()
        main_layout.addWidget(results_panel, 1)
        
        # Status bar
        self.statusBar().showMessage("Ready to search attachments")
    
    def create_search_panel(self):
        """Create the search input panel"""
        panel = QGroupBox("🔍 Search Attachments")
        layout = QVBoxLayout(panel)
        
        # Search input row
        search_layout = QHBoxLayout()
        
        # Search field
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Enter search terms (filename, subject, sender, body, etc.)")
        self.search_input.setMinimumHeight(40)
        self.search_input.returnPressed.connect(self.perform_search)
        search_layout.addWidget(self.search_input, 1)
        
        # Source filter (INBOX/DEVICE/ALL)
        self.source_combo = QComboBox()
        self.source_combo.addItem("📥 INBOX", "inbox")
        self.source_combo.addItem("💾 DEVICE", "device")
        self.source_combo.addItem("🌐 ALL", "all")
        self.source_combo.setMinimumHeight(40)
        search_layout.addWidget(self.source_combo)
        
        # Account filter
        self.account_combo = QComboBox()
        self.account_combo.addItem("All Accounts", None)
        self.account_combo.setMinimumHeight(40)
        search_layout.addWidget(self.account_combo)
        
        # Search button
        self.search_button = QPushButton("🔍 Search")
        self.search_button.setMinimumHeight(40)
        self.search_button.clicked.connect(self.perform_search)
        search_layout.addWidget(self.search_button)
        
        layout.addLayout(search_layout)
        
        # Search info
        info_label = QLabel("💡 Search across: filename, email subject, sender, body content, domain, and file type. Use multiple words for better results.")
        info_label.setStyleSheet("color: #666; font-size: 12px;")
        layout.addWidget(info_label)
        
        return panel
    
    def create_results_panel(self):
        """Create the results display panel"""
        panel = QGroupBox("📎 Search Results")
        layout = QVBoxLayout(panel)
        
        # Results table
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(5)
        self.results_table.setHorizontalHeaderLabels([
            "📎 File Name", "📧 Subject", "👤 Sender", "📁 Path in Device", "🏷️ Tag"
        ])
        
        # Set table properties
        header = self.results_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)  # File Name
        header.setSectionResizeMode(1, QHeaderView.Stretch)  # Subject
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Sender
        header.setSectionResizeMode(3, QHeaderView.Stretch)  # Path in Device
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # Tag
        
        self.results_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.results_table.setAlternatingRowColors(True)
        self.results_table.doubleClicked.connect(self.view_attachment_details)
        
        layout.addWidget(self.results_table)
        
        # Results info
        self.results_info = QLabel("No search performed yet")
        self.results_info.setStyleSheet("color: #666; font-size: 12px; padding: 5px;")
        layout.addWidget(self.results_info)
        
        return panel
    
    def load_user_accounts(self):
        """Load user's email accounts into the combo box"""
        try:
            import mysql.connector
            from config.database import DB_CONFIG
            
            conn = mysql.connector.connect(**DB_CONFIG)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, email, imap_host 
                FROM accounts 
                WHERE dashboard_user_id = %s 
                ORDER BY email
            """, (self.user_id,))
            
            accounts = cursor.fetchall()
            
            # Clear existing items except "All Accounts"
            self.account_combo.clear()
            self.account_combo.addItem("All Accounts", None)
            
            for account_id, email, imap_host in accounts:
                display_text = f"{email} ({imap_host})"
                self.account_combo.addItem(display_text, account_id)
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            print(f"Error loading accounts: {e}")
    
    def perform_search(self):
        """Perform the attachment search"""
        search_query = self.search_input.text().strip()
        
        # Allow empty search to show all attachments
        if not search_query:
            search_query = ""  # Empty string will show all attachments
        
        # Get selected source and account ID
        source = self.source_combo.currentData()
        account_id = self.account_combo.currentData()
        
        # Update UI
        self.search_button.setEnabled(False)
        self.search_button.setText("🔍 Searching...")
        self.statusBar().showMessage("Searching attachments...")
        
        # Clear previous results
        self.results_table.setRowCount(0)
        self.results_info.setText("Searching...")
        
        # Start search worker
        self.search_worker = SearchAttachmentsWorker(search_query, self.user_id, source, account_id)
        self.search_worker.search_completed.connect(self.on_search_completed)
        self.search_worker.search_error.connect(self.on_search_error)
        self.search_worker.start()
    
    def on_search_completed(self, results):
        """Handle search completion"""
        self.search_results = results
        self.display_results(results)
        
        # Update UI
        self.search_button.setEnabled(True)
        self.search_button.setText("🔍 Search")
        self.statusBar().showMessage(f"Found {len(results)} attachments")
    
    def on_search_error(self, error_message):
        """Handle search error"""
        QMessageBox.critical(self, "Search Error", f"Error performing search: {error_message}")
        
        # Update UI
        self.search_button.setEnabled(True)
        self.search_button.setText("🔍 Search")
        self.statusBar().showMessage("Search failed")
    
    def display_results(self, results):
        """Display search results in the table"""
        self.results_table.setRowCount(len(results))
        
        for row, result in enumerate(results):
            # File Name (show both original and device filename if available)
            original_filename = result.get('filename', 'Unknown Attachment')
            device_filename = result.get('device_filename')
            
            if device_filename and device_filename != original_filename:
                filename_display = f"{original_filename} → {device_filename}"
            else:
                filename_display = original_filename
                
            filename_item = QTableWidgetItem(filename_display)
            filename_item.setData(Qt.UserRole, result.get('attachment_id'))
            self.results_table.setItem(row, 0, filename_item)
            
            # Subject
            subject = result['subject'] or "No Subject"
            subject_item = QTableWidgetItem(subject)
            self.results_table.setItem(row, 1, subject_item)
            
            # Sender
            sender = result['sender'] or "Unknown"
            sender_item = QTableWidgetItem(sender)
            self.results_table.setItem(row, 2, sender_item)
            
            # Path in Device
            device_path = result.get('device_path')
            if device_path:
                # Show the directory name where the device file is located
                directory_path = os.path.dirname(device_path)
                folder_name = os.path.basename(directory_path)
                if folder_name and folder_name != "":
                    path_display = folder_name
                else:
                    path_display = "Root"
            else:
                attachment_id = result.get('attachment_id')
                if attachment_id:
                    # For downloaded attachments without device path, get the original file path
                    try:
                        import mysql.connector
                        from config.database import DB_CONFIG
                        
                        conn = mysql.connector.connect(**DB_CONFIG)
                        cursor = conn.cursor()
                        
                        cursor.execute("""
                            SELECT file_path FROM attachments WHERE id = %s
                        """, (attachment_id,))
                        
                        path_result = cursor.fetchone()
                        if path_result and path_result[0]:
                            file_path = path_result[0]
                            # Show the directory name where the file is located
                            directory_path = os.path.dirname(file_path)
                            folder_name = os.path.basename(directory_path)
                            if folder_name and folder_name != "":
                                path_display = folder_name
                            else:
                                path_display = "Root"
                        else:
                            path_display = "Not downloaded"
                        
                        cursor.close()
                        conn.close()
                        
                    except Exception as e:
                        path_display = "Error loading path"
                else:
                    # For INBOX attachments (not downloaded)
                    path_display = "Not downloaded"
            
            path_item = QTableWidgetItem(path_display)
            self.results_table.setItem(row, 3, path_item)
            
            # Tag
            # Get tags for this attachment/email
            try:
                import mysql.connector
                from config.database import DB_CONFIG
                
                conn = mysql.connector.connect(**DB_CONFIG)
                cursor = conn.cursor()
                
                email_id = result.get('email_id')
                if email_id:
                    cursor.execute("""
                        SELECT GROUP_CONCAT(t.name ORDER BY t.name SEPARATOR ', ') as tags
                        FROM email_tags et
                        LEFT JOIN tags t ON et.tag_id = t.id
                        WHERE et.email_id = %s
                    """, (email_id,))
                    
                    tag_result = cursor.fetchone()
                    tags = tag_result[0] if tag_result and tag_result[0] else "No tags"
                else:
                    tags = "No tags"
                
                cursor.close()
                conn.close()
                
            except Exception as e:
                tags = "Error loading tags"
            
            tag_item = QTableWidgetItem(tags)
            self.results_table.setItem(row, 4, tag_item)
        
        # Update results info
        if results:
            self.results_info.setText(f"Found {len(results)} attachment(s)")
        else:
            self.results_info.setText("No attachments found matching your search criteria")
    
    def view_attachment_details(self, index):
        """Open attachment details dialog"""
        row = index.row()
        if row >= 0 and row < len(self.search_results):
            result = self.search_results[row]
            attachment_id = result.get('attachment_id')
            
            if attachment_id:
                # Device attachment - get full details from database
                attachment_data = Attachment.get_attachment_with_email_metadata(attachment_id)
                
                if attachment_data:
                    dialog = AttachmentDetailsDialog(attachment_data, self)
                    dialog.exec_()
                else:
                    QMessageBox.warning(self, "Error", "Could not load attachment details.")
            else:
                # INBOX attachment - create proper attachment data structure
                attachment_data = {
                    'attachment_id': None,
                    'filename': result.get('filename', 'Unknown Attachment'),
                    'file_path': '',  # No local file path for INBOX attachments
                    'file_size': result.get('file_size', 0),
                    'mime_type': result.get('mime_type', 'Unknown'),
                    'content_type': result.get('content_type', 'Unknown'),
                    'attachment_created': result.get('attachment_created'),
                    'email_id': result.get('email_id'),
                    'subject': result.get('subject'),
                    'sender': result.get('sender'),
                    'recipients': '',
                    'body': result.get('body'),
                    'email_date': result.get('email_date'),
                    'has_attachment': True,
                    'email_size': 0,
                    'read_status': False,
                    'priority': 'normal',
                    'account_email': result.get('account_email'),
                    'imap_host': result.get('imap_host'),
                    'other_attachments': [],
                    'is_inbox_attachment': True  # Flag to identify INBOX attachments
                }
                
                dialog = AttachmentDetailsDialog(attachment_data, self)
                dialog.exec_()
    
    def closeEvent(self, event):
        """Handle window closing"""
        if self.search_worker and self.search_worker.isRunning():
            self.search_worker.terminate()
            self.search_worker.wait()
        event.accept() 