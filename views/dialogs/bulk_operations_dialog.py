import mysql.connector
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit, 
    QPushButton, QMessageBox, QGroupBox, QComboBox, QTextEdit
)
from config.database import DB_CONFIG

class BulkOperationsDialog(QtWidgets.QDialog):
    def __init__(self, parent, account_id, user_id):
        super().__init__(parent)
        self.account_id = account_id
        self.user_id = user_id
        self.setWindowTitle("Bulk Email Operations")
        self.setModal(True)
        self.resize(600, 500)
        
        layout = QVBoxLayout(self)
        
        # Operation selection
        operation_group = QGroupBox("Select Operation")
        operation_layout = QVBoxLayout(operation_group)
        
        self.operation_combo = QComboBox()
        self.operation_combo.addItems([
            "Mark all as read",
            "Mark all as unread", 
            "Delete old emails",
            "Tag emails by sender domain",
            "Remove emails from sender",
            "Clean up duplicate emails"
        ])
        operation_layout.addWidget(self.operation_combo)
        
        layout.addWidget(operation_group)
        
        # Parameters
        params_group = QGroupBox("Parameters")
        params_layout = QFormLayout(params_group)
        
        self.param_edit = QLineEdit()
        self.param_edit.setPlaceholderText("Enter parameter (e.g., number of days, sender email, tag name)")
        
        self.tag_edit = QLineEdit()
        self.tag_edit.setPlaceholderText("Tag name (for tagging operations)")
        
        params_layout.addRow("Parameter:", self.param_edit)
        params_layout.addRow("Tag Name:", self.tag_edit)
        
        layout.addWidget(params_group)
        
        # Preview
        preview_group = QGroupBox("Preview")
        preview_layout = QVBoxLayout(preview_group)
        
        self.preview_text = QTextEdit()
        self.preview_text.setMaximumHeight(150)
        self.preview_text.setReadOnly(True)
        preview_layout.addWidget(self.preview_text)
        
        layout.addWidget(preview_group)
        
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

        # Buttons
        btn_layout = QHBoxLayout()

        preview_btn = QPushButton("Preview")
        preview_btn.clicked.connect(self.preview_operation)
        preview_btn.setStyleSheet(blue_btn_style)

        execute_btn = QPushButton("Execute")
        execute_btn.clicked.connect(self.execute_operation)
        execute_btn.setStyleSheet(blue_btn_style)

        btn_layout.addWidget(preview_btn)
        btn_layout.addWidget(execute_btn)
        btn_layout.addStretch()
       
        
        layout.addLayout(btn_layout)

    def preview_operation(self):
        """Preview the bulk operation"""
        if not self.account_id:
            self.preview_text.setPlainText("No account selected.")
            return
            
        operation = self.operation_combo.currentText()
        param = self.param_edit.text().strip()
        
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        try:
            preview_text = ""
            
            if operation == "Mark all as read":
                cursor.execute("SELECT COUNT(*) FROM emails WHERE account_id=%s AND read_status=FALSE", 
                             (self.account_id,))
                count = cursor.fetchone()[0]
                preview_text = f"Will mark {count} unread emails as read."
                
            elif operation == "Mark all as unread":
                cursor.execute("SELECT COUNT(*) FROM emails WHERE account_id=%s AND read_status=TRUE", 
                             (self.account_id,))
                count = cursor.fetchone()[0]
                preview_text = f"Will mark {count} read emails as unread."
                
            elif operation == "Delete old emails":
                if not param.isdigit():
                    preview_text = "Please enter number of days as parameter."
                else:
                    days = int(param)
                    cursor.execute("""
                        SELECT COUNT(*) FROM emails 
                        WHERE account_id=%s AND date < DATE_SUB(NOW(), INTERVAL %s DAY)
                    """, (self.account_id, days))
                    count = cursor.fetchone()[0]
                    preview_text = f"Will delete {count} emails older than {days} days."
                    
            elif operation == "Tag emails by sender domain":
                tag_name = self.tag_edit.text().strip()
                if not tag_name:
                    preview_text = "Please enter a tag name."
                else:
                    cursor.execute("""
                        SELECT SUBSTRING_INDEX(sender, '@', -1) as domain, COUNT(*) as count
                        FROM emails 
                        WHERE account_id=%s AND sender IS NOT NULL
                        GROUP BY domain
                        ORDER BY count DESC
                        LIMIT 10
                    """, (self.account_id,))
                    domains = cursor.fetchall()
                    preview_text = f"Will tag emails by domain with '{tag_name}':\n\n"
                    for domain, count in domains:
                        preview_text += f"{domain}: {count} emails\n"
                        
            elif operation == "Remove emails from sender":
                if not param:
                    preview_text = "Please enter sender email or pattern."
                else:
                    cursor.execute("""
                        SELECT COUNT(*) FROM emails 
                        WHERE account_id=%s AND sender LIKE %s
                    """, (self.account_id, f"%{param}%"))
                    count = cursor.fetchone()[0]
                    preview_text = f"Will delete {count} emails from senders matching '{param}'."
                    
            elif operation == "Clean up duplicate emails":
                cursor.execute("""
                    SELECT COUNT(*) - COUNT(DISTINCT uid) as duplicates
                    FROM emails 
                    WHERE account_id=%s
                """, (self.account_id,))
                count = cursor.fetchone()[0]
                preview_text = f"Will remove {count} duplicate emails."
            
            self.preview_text.setPlainText(preview_text)
            
        finally:
            cursor.close()
            conn.close()

    def execute_operation(self):
        """Execute the bulk operation"""
        reply = QMessageBox.question(
            self, "Confirm Operation",
            "Are you sure you want to execute this bulk operation?\n\n"
            "This action may affect many emails and cannot be undone.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
            
        operation = self.operation_combo.currentText()
        param = self.param_edit.text().strip()
        tag_name = self.tag_edit.text().strip()
        
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        try:
            affected_count = 0
            
            if operation == "Mark all as read":
                cursor.execute("UPDATE emails SET read_status=TRUE WHERE account_id=%s AND read_status=FALSE", 
                             (self.account_id,))
                affected_count = cursor.rowcount
                
            elif operation == "Mark all as unread":
                cursor.execute("UPDATE emails SET read_status=FALSE WHERE account_id=%s AND read_status=TRUE", 
                             (self.account_id,))
                affected_count = cursor.rowcount
                
            elif operation == "Delete old emails":
                if param.isdigit():
                    days = int(param)
                    cursor.execute("DELETE FROM emails WHERE account_id=%s AND date < DATE_SUB(NOW(), INTERVAL %s DAY)", 
                                 (self.account_id, days))
                    affected_count = cursor.rowcount
                    
            elif operation == "Tag emails by sender domain":
                if tag_name:
                    # Get or create tag
                    cursor.execute("SELECT id FROM tags WHERE name=%s AND dashboard_user_id=%s", 
                                 (tag_name, self.user_id))
                    result = cursor.fetchone()
                    
                    if result:
                        tag_id = result[0]
                    else:
                        cursor.execute("INSERT INTO tags (name, dashboard_user_id) VALUES (%s, %s)", 
                                     (tag_name, self.user_id))
                        conn.commit()
                        tag_id = cursor.lastrowid
                    
                    # Tag emails by domain
                    cursor.execute("SELECT id, sender FROM emails WHERE account_id=%s AND sender IS NOT NULL", 
                                 (self.account_id,))
                    emails = cursor.fetchall()
                    
                    for email_id, sender in emails:
                        if '@' in sender:
                            try:
                                cursor.execute("INSERT INTO email_tags (email_id, tag_id) VALUES (%s, %s)", 
                                             (email_id, tag_id))
                                affected_count += 1
                            except mysql.connector.errors.IntegrityError:
                                pass
                                
            elif operation == "Remove emails from sender":
                if param:
                    cursor.execute("DELETE FROM emails WHERE account_id=%s AND sender LIKE %s", 
                                 (self.account_id, f"%{param}%"))
                    affected_count = cursor.rowcount
                    
            elif operation == "Clean up duplicate emails":
                cursor.execute("""
                    DELETE e1 FROM emails e1
                    INNER JOIN emails e2 
                    WHERE e1.id > e2.id 
                    AND e1.uid = e2.uid 
                    AND e1.account_id = %s 
                    AND e2.account_id = %s
                """, (self.account_id, self.account_id))
                affected_count = cursor.rowcount
            
            conn.commit()
            
            QMessageBox.information(
                self, "Operation Complete",
                f"Bulk operation completed successfully!\n\nAffected items: {affected_count}"
            )
            
            # Refresh parent window
            if hasattr(self.parent(), 'refresh_emails'):
                self.parent().refresh_emails()
                self.parent().update_statistics()
            
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "Operation Failed", f"Bulk operation failed: {str(e)}")
        finally:
            cursor.close()
            conn.close()