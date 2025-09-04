import re
import mysql.connector
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit, 
    QPushButton, QMessageBox, QGroupBox, QComboBox,
    QSpinBox, QCheckBox, QTextEdit, QFileDialog, QApplication
)
from config.database import DB_CONFIG

class CustomTagRuleDialog(QtWidgets.QDialog):
    def __init__(self, parent, initial_value, user_id):
        super().__init__(parent)
        self.user_id = user_id
        self.setWindowTitle("Create Custom Tag Rule")
        self.setModal(True)
        self.resize(500, 500)
        
        layout = QVBoxLayout(self)
        
        # Rule configuration
        config_group = QGroupBox("Rule Configuration")
        config_layout = QFormLayout(config_group)
        
        self.rule_type = QComboBox()
        self.rule_type.addItems(["sender", "subject", "body", "domain"])
        
        self.operator = QComboBox()
        self.operator.addItems(["contains", "equals", "starts_with", "ends_with", "regex"])
        
        self.value = QLineEdit()
        self.value.setText(initial_value)
        
        self.tag_name = QLineEdit()
        
        self.priority = QSpinBox()
        self.priority.setRange(0, 10)
        self.priority.setValue(5)
        
        config_layout.addRow("Rule Type:", self.rule_type)
        config_layout.addRow("Operator:", self.operator)
        config_layout.addRow("Value:", self.value)
        config_layout.addRow("Tag Name:", self.tag_name)
        config_layout.addRow("Priority:", self.priority)
        
        layout.addWidget(config_group)
        
        # Preview
        preview_group = QGroupBox("Preview")
        preview_layout = QVBoxLayout(preview_group)
        
        self.preview_text = QTextEdit()
        self.preview_text.setMaximumHeight(100)
        self.preview_text.setReadOnly(True)
        preview_layout.addWidget(self.preview_text)
        
        layout.addWidget(preview_group)
        
        # Update preview when values change
        for widget in [self.rule_type, self.operator, self.value, self.tag_name]:
            if isinstance(widget, QComboBox):
                widget.currentTextChanged.connect(self.update_preview)
            elif isinstance(widget, QLineEdit):
                widget.textChanged.connect(self.update_preview)
        
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
        """

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

                # Buttons
        btn_layout = QHBoxLayout()

        create_btn = QPushButton("Create Rule")
        create_btn.clicked.connect(self.accept)
        create_btn.setDefault(True)
        create_btn.setStyleSheet(blue_btn_style)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet(red_btn_style)

        btn_layout.addWidget(create_btn)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addStretch()
        
        layout.addLayout(btn_layout)
        
        self.update_preview()

    def update_preview(self):
        """Update rule preview"""
        rule_text = f"When {self.rule_type.currentText()} {self.operator.currentText()} '{self.value.text()}'\n"
        rule_text += f"Then tag as '{self.tag_name.text()}'\n"
        rule_text += f"Priority: {self.priority.value()}"
        
        self.preview_text.setPlainText(rule_text)

    def accept(self):
        """Create the rule and apply to existing emails"""
        rule_type = self.rule_type.currentText()
        operator = self.operator.currentText()
        value = self.value.text().strip()
        tag_name = self.tag_name.text().strip()
        priority = self.priority.value()
        
        if not all([rule_type, operator, value, tag_name]):
            QMessageBox.warning(self, "Missing Information", "Please fill all required fields.")
            return
        
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        try:
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
            
            # Create rule (without attachment settings)
            cursor.execute("""
                INSERT INTO auto_tag_rules (rule_type, operator, value, tag_id, priority, 
                                          save_attachments, attachment_path, dashboard_user_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (rule_type, operator, value, tag_id, priority, False, None, self.user_id))
            
            rule_id = cursor.lastrowid
            conn.commit()
            
            # Apply rule to existing emails
            affected_emails = self.apply_rule_to_existing_emails(cursor, conn, rule_type, operator, value, tag_id)
            
            success_message = f"Custom tag rule created successfully!\n\n"
            success_message += f"Rule: When {rule_type} {operator} '{value}'\n"
            success_message += f"Then: Tag as '{tag_name}'\n"
            success_message += f"\nApplied to {affected_emails} existing emails."
            
            QMessageBox.information(self, "Success", success_message)
            super().accept()
            
        except mysql.connector.errors.IntegrityError:
            QMessageBox.warning(self, "Duplicate Rule", "A similar rule already exists.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create rule: {str(e)}")
        finally:
            cursor.close()
            conn.close()

    def apply_rule_to_existing_emails(self, cursor, conn, rule_type, operator, value, tag_id):
        """Apply the new rule to all existing emails for this user"""
        try:
            # Get all emails for accounts belonging to this user
            cursor.execute("""
                SELECT e.id, e.sender, e.subject, e.body
                FROM emails e
                INNER JOIN accounts a ON e.account_id = a.id
                WHERE a.dashboard_user_id = %s
            """, (self.user_id,))
            
            emails = cursor.fetchall()
            affected_count = 0
            
            for email_id, sender, subject, body in emails:
                try:
                    # Check if rule matches this email
                    if self.check_rule_match(rule_type, operator, value, sender, subject, body):
                        # Apply tag
                        cursor.execute("INSERT IGNORE INTO email_tags (email_id, tag_id) VALUES (%s, %s)",
                                     (email_id, tag_id))
                        
                        if cursor.rowcount > 0:
                            affected_count += 1
                                
                except mysql.connector.Error:
                    continue  # Skip this email if there's an error
            
            conn.commit()
            return affected_count
            
        except Exception as e:
            print(f"Error applying rule to existing emails: {e}")
            return 0

    def check_rule_match(self, rule_type, operator, value, sender, subject, body):
        """Check if a rule matches an email"""
        try:
            # Determine target text based on rule type
            target_text = ""
            
            if rule_type == 'sender':
                target_text = (sender or "").lower()
            elif rule_type == 'subject':
                target_text = (subject or "").lower()
            elif rule_type == 'body':
                target_text = (body or "").lower()
            elif rule_type == 'domain':
                if sender and '@' in sender:
                    try:
                        target_text = sender.split('@')[1].lower()
                    except IndexError:
                        target_text = ""
                else:
                    target_text = ""
            
            value_lower = (value or "").lower()
            
            # Apply operator
            if operator == 'contains':
                return value_lower in target_text
            elif operator == 'equals':
                return value_lower == target_text
            elif operator == 'starts_with':
                return target_text.startswith(value_lower)
            elif operator == 'ends_with':
                return target_text.endswith(value_lower)
            elif operator == 'regex':
                try:
                    return bool(re.search(value, target_text, re.IGNORECASE))
                except re.error:
                    return False
            
            return False
            
        except Exception as e:
            print(f"Error checking rule match: {e}")
            return False