import mysql.connector
import datetime
import re
from typing import Optional, List, Dict, Any
from config.database import DB_CONFIG

class AutoTagRule:
    """Auto-tag rule model"""
    
    def __init__(self, id: int = None, rule_type: str = None, operator: str = 'contains',
                 value: str = None, tag_id: int = None, enabled: bool = True, priority: int = 0,
                 save_attachments: bool = False, attachment_path: str = None,
                 dashboard_user_id: int = None, created_at: datetime.datetime = None):
        self.id = id
        self.rule_type = rule_type
        self.operator = operator
        self.value = value
        self.tag_id = tag_id
        self.enabled = enabled
        self.priority = priority
        self.save_attachments = save_attachments
        self.attachment_path = attachment_path
        self.dashboard_user_id = dashboard_user_id
        self.created_at = created_at

    @staticmethod
    def create_database():
        """Create the auto_tag_rules table"""
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS auto_tag_rules (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    rule_type ENUM('sender','subject','body','domain') NOT NULL,
                    operator ENUM('contains','equals','starts_with','ends_with','regex') DEFAULT 'contains',
                    value TEXT NOT NULL,
                    tag_id INT NOT NULL,
                    enabled BOOLEAN DEFAULT TRUE,
                    priority INT DEFAULT 0,
                    save_attachments BOOLEAN DEFAULT FALSE,
                    attachment_path TEXT NULL,
                    dashboard_user_id INT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE,
                    FOREIGN KEY (dashboard_user_id) REFERENCES dashboard_users(id) ON DELETE CASCADE
                )
            """)
            conn.commit()
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def create_rule(rule_type: str, operator: str, value: str, tag_id: int, user_id: int,
                   save_attachments: bool = False, attachment_path: str = None, priority: int = 0) -> Optional['AutoTagRule']:
        """Create a new auto-tag rule"""
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO auto_tag_rules (rule_type, operator, value, tag_id, dashboard_user_id,
                                          save_attachments, attachment_path, priority)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (rule_type, operator, value, tag_id, user_id, save_attachments, attachment_path, priority))
            conn.commit()
            
            rule_id = cursor.lastrowid
            return AutoTagRule(
                id=rule_id,
                rule_type=rule_type,
                operator=operator,
                value=value,
                tag_id=tag_id,
                dashboard_user_id=user_id,
                save_attachments=save_attachments,
                attachment_path=attachment_path,
                priority=priority,
                created_at=datetime.datetime.now()
            )
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def get_by_id(rule_id: int) -> Optional['AutoTagRule']:
        """Get rule by ID"""
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        try:
            cursor.execute("SELECT * FROM auto_tag_rules WHERE id=%s", (rule_id,))
            row = cursor.fetchone()
            
            if not row:
                return None
                
            return AutoTagRule(
                id=row['id'],
                rule_type=row['rule_type'],
                operator=row['operator'],
                value=row['value'],
                tag_id=row['tag_id'],
                enabled=row['enabled'],
                priority=row['priority'],
                save_attachments=row['save_attachments'],
                attachment_path=row['attachment_path'],
                dashboard_user_id=row['dashboard_user_id'],
                created_at=row['created_at']
            )
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def get_user_rules(user_id: int) -> List['AutoTagRule']:
        """Get all auto-tag rules for a user"""
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        try:
            cursor.execute("""
                SELECT r.*, t.name as tag_name
                FROM auto_tag_rules r
                JOIN tags t ON r.tag_id = t.id
                WHERE r.dashboard_user_id = %s
                ORDER BY r.priority DESC, r.rule_type
            """, (user_id,))
            
            rules = []
            for row in cursor.fetchall():
                rule = AutoTagRule(
                    id=row['id'],
                    rule_type=row['rule_type'],
                    operator=row['operator'],
                    value=row['value'],
                    tag_id=row['tag_id'],
                    enabled=row['enabled'],
                    priority=row['priority'],
                    save_attachments=row['save_attachments'],
                    attachment_path=row['attachment_path'],
                    dashboard_user_id=row['dashboard_user_id'],
                    created_at=row['created_at']
                )
                rule.tag_name = row['tag_name']
                rules.append(rule)
            
            return rules
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def get_active_rules(user_id: int) -> List['AutoTagRule']:
        """Get all active auto-tag rules for a user"""
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        try:
            cursor.execute("""
                SELECT r.*, t.name as tag_name
                FROM auto_tag_rules r
                JOIN tags t ON r.tag_id = t.id
                WHERE r.dashboard_user_id = %s AND r.enabled = TRUE
                ORDER BY r.priority DESC, r.id
            """, (user_id,))
            
            rules = []
            for row in cursor.fetchall():
                rule = AutoTagRule(
                    id=row['id'],
                    rule_type=row['rule_type'],
                    operator=row['operator'],
                    value=row['value'],
                    tag_id=row['tag_id'],
                    enabled=row['enabled'],
                    priority=row['priority'],
                    save_attachments=row['save_attachments'],
                    attachment_path=row['attachment_path'],
                    dashboard_user_id=row['dashboard_user_id'],
                    created_at=row['created_at']
                )
                rule.tag_name = row['tag_name']
                rules.append(rule)
            
            return rules
        finally:
            cursor.close()
            conn.close()

    def update(self, rule_type: str = None, operator: str = None, value: str = None,
               tag_id: int = None, enabled: bool = None, priority: int = None,
               save_attachments: bool = None, attachment_path: str = None):
        """Update rule fields"""
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        try:
            # Build update query dynamically
            updates = []
            params = []
            
            if rule_type is not None:
                updates.append("rule_type = %s")
                params.append(rule_type)
                self.rule_type = rule_type
                
            if operator is not None:
                updates.append("operator = %s")
                params.append(operator)
                self.operator = operator
                
            if value is not None:
                updates.append("value = %s")
                params.append(value)
                self.value = value
                
            if tag_id is not None:
                updates.append("tag_id = %s")
                params.append(tag_id)
                self.tag_id = tag_id
                
            if enabled is not None:
                updates.append("enabled = %s")
                params.append(enabled)
                self.enabled = enabled
                
            if priority is not None:
                updates.append("priority = %s")
                params.append(priority)
                self.priority = priority
                
            if save_attachments is not None:
                updates.append("save_attachments = %s")
                params.append(save_attachments)
                self.save_attachments = save_attachments
                
            if attachment_path is not None:
                updates.append("attachment_path = %s")
                params.append(attachment_path)
                self.attachment_path = attachment_path
            
            if updates:
                params.append(self.id)
                query = f"UPDATE auto_tag_rules SET {', '.join(updates)} WHERE id = %s"
                cursor.execute(query, params)
                conn.commit()
        finally:
            cursor.close()
            conn.close()

    def toggle_enabled(self):
        """Toggle rule enabled status"""
        self.update(enabled=not self.enabled)

    def delete(self):
        """Delete this rule"""
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        try:
            cursor.execute("DELETE FROM auto_tag_rules WHERE id=%s", (self.id,))
            conn.commit()
        finally:
            cursor.close()
            conn.close()

    def check_match(self, sender: str, subject: str, body: str) -> bool:
        """Check if this rule matches an email"""
        try:
            target_text = ""
            
            if self.rule_type == 'sender':
                target_text = sender.lower() if sender else ""
            elif self.rule_type == 'subject':
                target_text = subject.lower() if subject else ""
            elif self.rule_type == 'body':
                target_text = body.lower() if body else ""
            elif self.rule_type == 'domain':
                if sender and '@' in sender:
                    try:
                        target_text = sender.split('@')[1].lower()
                    except IndexError:
                        target_text = ""
                else:
                    target_text = ""
            
            value_lower = self.value.lower() if self.value else ""
            
            if self.operator == 'contains':
                return value_lower in target_text
            elif self.operator == 'equals':
                return value_lower == target_text
            elif self.operator == 'starts_with':
                return target_text.startswith(value_lower)
            elif self.operator == 'ends_with':
                return target_text.endswith(value_lower)
            elif self.operator == 'regex':
                try:
                    return bool(re.search(self.value, target_text, re.IGNORECASE))
                except re.error:
                    return False
            
            return False
            
        except Exception as e:
            print(f"Error checking rule match: {e}")
            return False

    def apply_to_email(self, email_id: int) -> bool:
        """Apply this rule to an email (add tag)"""
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        try:
            cursor.execute("INSERT IGNORE INTO email_tags (email_id, tag_id) VALUES (%s, %s)", 
                         (email_id, self.tag_id))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            cursor.close()
            conn.close()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'rule_type': self.rule_type,
            'operator': self.operator,
            'value': self.value,
            'tag_id': self.tag_id,
            'enabled': self.enabled,
            'priority': self.priority,
            'save_attachments': self.save_attachments,
            'attachment_path': self.attachment_path,
            'dashboard_user_id': self.dashboard_user_id,
            'created_at': self.created_at,
            'tag_name': getattr(self, 'tag_name', None)
        }

    def get_display_info(self) -> str:
        """Get display information for UI"""
        status = "✅" if self.enabled else "❌"
        attachment_status = "💾" if self.save_attachments else "❌"
        display_value = (self.value[:30] + "...") if len(self.value) > 30 else self.value
        tag_name = getattr(self, 'tag_name', 'Unknown')
        
        return f"{status} {self.rule_type} {self.operator} '{display_value}' → {tag_name} {attachment_status}" 