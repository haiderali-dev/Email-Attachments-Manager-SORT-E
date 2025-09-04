import mysql.connector
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QPushButton, QCheckBox, QHBoxLayout, QMessageBox
from config.database import DB_CONFIG
from views.dialogs.custom_tag_rule_dialog import CustomTagRuleDialog

class EditRuleDialog(CustomTagRuleDialog):
    def __init__(self, parent, rule_id, user_id):
        self.rule_id = rule_id
        
        # Load existing rule data
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT r.rule_type, r.operator, r.value, t.name, r.priority, r.enabled
                FROM auto_tag_rules r
                JOIN tags t ON r.tag_id = t.id
                WHERE r.id = %s
            """, (rule_id,))
            
            rule_data = cursor.fetchone()
            if not rule_data:
                raise ValueError("Rule not found")
                
            rule_type, operator, value, tag_name, priority, enabled = rule_data
            
        finally:
            cursor.close()
            conn.close()
        
        # Initialize parent with existing value
        super().__init__(parent, value, user_id)
        
        # Set window title
        self.setWindowTitle("Edit Auto-Tag Rule")
        
        # Populate fields with existing data
        self.rule_type.setCurrentText(rule_type)
        self.operator.setCurrentText(operator)
        self.value.setText(value)
        self.tag_name.setText(tag_name)
        self.priority.setValue(priority)
        
        # Add enabled checkbox
        self.enabled = QCheckBox("Rule Enabled")
        self.enabled.setChecked(enabled)
        self.layout().insertWidget(0, self.enabled)
        
                # Change button text and apply blue style
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

        for i in range(self.layout().count()):
            item = self.layout().itemAt(i)
            if isinstance(item, QHBoxLayout):
                for j in range(item.count()):
                    widget = item.itemAt(j).widget()
                    if isinstance(widget, QPushButton) and widget.text() == "Create Rule":
                        widget.setText("💾 Save Changes")
                        widget.setStyleSheet(blue_btn_style)

    def accept(self):
        """Update the rule"""
        rule_type = self.rule_type.currentText()
        operator = self.operator.currentText()
        value = self.value.text().strip()
        tag_name = self.tag_name.text().strip()
        priority = self.priority.value()
        enabled = self.enabled.isChecked()
        
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
            
            # Update rule (without attachment settings)
            cursor.execute("""
                UPDATE auto_tag_rules 
                SET rule_type=%s, operator=%s, value=%s, tag_id=%s, priority=%s, 
                    save_attachments=%s, attachment_path=%s, enabled=%s
                WHERE id=%s
            """, (rule_type, operator, value, tag_id, priority, False, None, enabled, self.rule_id))
            
            conn.commit()
            QMessageBox.information(self, "Success", "Rule updated successfully!")
            QtWidgets.QDialog.accept(self)  # Call QDialog.accept directly to avoid recursion
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to update rule: {str(e)}")
        finally:
            cursor.close()
            conn.close()