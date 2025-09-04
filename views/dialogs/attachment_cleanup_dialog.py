import os
import mysql.connector
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QPushButton, 
    QMessageBox, QGroupBox, QLabel, QTextEdit, QApplication
)
from config.database import DB_CONFIG
from utils.formatters import format_size

class AttachmentCleanupDialog(QtWidgets.QDialog):
    def __init__(self, parent, user_id):
        super().__init__(parent)
        self.user_id = user_id
        self.setWindowTitle("Clean Duplicate Attachments")
        self.setModal(True)
        self.resize(700, 500)
        
        layout = QVBoxLayout(self)
        
        # Info section
        info_group = QGroupBox("Attachment Cleanup")
        info_layout = QVBoxLayout(info_group)
        
        info_text = QLabel(
            "This tool helps you identify and clean up duplicate attachment downloads.\n\n"
            "It will scan all attachment folders for your auto-tag rules and:\n"
            "• Identify folders with duplicate files\n"
            "• Show disk space usage\n"
            "• Allow you to clean up duplicates\n\n"
            "⚠️ This operation cannot be undone. Please backup important files first."
        )
        info_text.setWordWrap(True)
        info_layout.addWidget(info_text)
        
        layout.addWidget(info_group)
        
        # Scan results
        results_group = QGroupBox("Scan Results")
        results_layout = QVBoxLayout(results_group)
        
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setMaximumHeight(200)
        results_layout.addWidget(self.results_text)
        
        layout.addWidget(results_group)
        
       # Action buttons
        btn_layout = QHBoxLayout()

        scan_btn = QPushButton("Scan Attachments")
        scan_btn.clicked.connect(self.scan_attachments)

        clean_btn = QPushButton("Clean Duplicates")
        clean_btn.clicked.connect(self.clean_duplicates)
        clean_btn.setProperty("class", "warning")
        clean_btn.setEnabled(False)
        self.clean_btn = clean_btn

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.reject)

        # Styles
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

        # Apply styles
        scan_btn.setStyleSheet(blue_btn_style)
        clean_btn.setStyleSheet(blue_btn_style)
        close_btn.setStyleSheet(red_btn_style)

        # Add to layout
        btn_layout.addWidget(scan_btn)
        btn_layout.addWidget(clean_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)

        # Initialize state
        self.attachment_paths = []
        self.duplicate_info = []

    def scan_attachments(self):
        """Scan for attachment folders and duplicates"""
        self.results_text.clear()
        self.results_text.append("Scanning attachment folders...\n")
        QApplication.processEvents()
        
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        try:
            # Get all attachment paths for this user's rules
            cursor.execute("""
                SELECT DISTINCT attachment_path
                FROM auto_tag_rules
                WHERE dashboard_user_id=%s 
                AND save_attachments=TRUE 
                AND attachment_path IS NOT NULL
                AND attachment_path != ''
            """, (self.user_id,))
            
            paths = cursor.fetchall()
            
            if not paths:
                self.results_text.append("No attachment paths found in auto-tag rules.")
                return
            
            total_size = 0
            total_folders = 0
            total_files = 0
            duplicate_folders = []
            
            for (path,) in paths:
                if not os.path.exists(path):
                    self.results_text.append(f"❌ Path not found: {path}")
                    continue
                
                self.results_text.append(f"Scanning: {path}")
                QApplication.processEvents()
                
                # Scan all email folders in this path
                for item in os.listdir(path):
                    item_path = os.path.join(path, item)
                    if os.path.isdir(item_path) and item.startswith('email_'):
                        total_folders += 1
                        folder_files = []
                        folder_size = 0
                        
                        try:
                            for file in os.listdir(item_path):
                                file_path = os.path.join(item_path, file)
                                if os.path.isfile(file_path):
                                    file_size = os.path.getsize(file_path)
                                    folder_files.append((file, file_size))
                                    folder_size += file_size
                                    total_files += 1
                        except Exception as e:
                            self.results_text.append(f"    ❌ Error reading {item}: {e}")
                            continue
                        
                        total_size += folder_size
                        
                        # Check for potential duplicates (same filenames)
                        filenames = [f[0] for f in folder_files]
                        if len(filenames) != len(set(filenames)):
                            duplicate_folders.append((item_path, folder_files))
            
            # Display results
            self.results_text.append(f"\nSCAN SUMMARY:")
            self.results_text.append(f"Total attachment folders: {total_folders}")
            self.results_text.append(f"Total files: {total_files}")
            self.results_text.append(f"Total size: {format_size(total_size)}")
            
            if duplicate_folders:
                self.results_text.append(f"\n⚠️ POTENTIAL ISSUES:")
                self.results_text.append(f"Folders with duplicate filenames: {len(duplicate_folders)}")
                
                for folder_path, files in duplicate_folders[:5]:  # Show first 5
                    folder_name = os.path.basename(folder_path)
                    self.results_text.append(f"  📁 {folder_name}: {len(files)} files")
                
                if len(duplicate_folders) > 5:
                    self.results_text.append(f"  ... and {len(duplicate_folders) - 5} more")
                
                self.duplicate_info = duplicate_folders
                self.clean_btn.setEnabled(True)
            else:
                self.results_text.append(f"\n✅ No obvious duplicates found.")
                self.clean_btn.setEnabled(False)
            
        except Exception as e:
            self.results_text.append(f"\n❌ Scan error: {str(e)}")
        finally:
            cursor.close()
            conn.close()

    def clean_duplicates(self):
        """Clean up duplicate attachments"""
        if not self.duplicate_info:
            return
            
        reply = QMessageBox.question(
            self, "Confirm Cleanup",
            f"This will attempt to clean up {len(self.duplicate_info)} folders with potential duplicates.\n\n"
            "⚠️ This action cannot be undone!\n\n"
            "Continue?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        cleaned_folders = 0
        freed_space = 0
        
        for folder_path, files in self.duplicate_info:
            try:
                # Group files by name
                file_groups = {}
                for filename, size in files:
                    if filename not in file_groups:
                        file_groups[filename] = []
                    file_groups[filename].append((filename, size))
                
                # For each group with duplicates, keep only the largest file
                for filename, file_list in file_groups.items():
                    if len(file_list) > 1:
                        # Sort by size, keep largest
                        file_list.sort(key=lambda x: x[1], reverse=True)
                        
                        # Remove smaller duplicates
                        for filename, size in file_list[1:]:
                            file_path = os.path.join(folder_path, filename)
                            if os.path.exists(file_path):
                                os.remove(file_path)
                                freed_space += size
                
                cleaned_folders += 1
                
            except Exception as e:
                self.results_text.append(f"❌ Error cleaning {folder_path}: {e}")
        
        self.results_text.append(f"\n✅ CLEANUP COMPLETE:")
        self.results_text.append(f"Cleaned folders: {cleaned_folders}")
        self.results_text.append(f"Space freed: {format_size(freed_space)}")
        
        self.clean_btn.setEnabled(False)