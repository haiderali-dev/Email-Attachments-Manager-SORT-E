import mysql.connector
import datetime
from typing import Optional, List, Dict, Any, Tuple
from config.database import DB_CONFIG

class Email:
    """Email model"""
    
    def __init__(self, id: int = None, uid: str = None, subject: str = None, sender: str = None,
                 recipients: str = None, date: datetime.datetime = None, has_attachment: bool = False,
                 body: str = None, body_text: str = None, body_html: str = None, 
                 body_format: str = 'text', size_bytes: int = 0, read_status: bool = False,
                 priority: str = 'normal', account_id: int = None, created_at: datetime.datetime = None,
                 updated_at: datetime.datetime = None):
        self.id = id
        self.uid = uid
        self.subject = subject
        self.sender = sender
        self.recipients = recipients
        self.date = date
        self.has_attachment = has_attachment
        self.body = body  # Keep for backward compatibility
        self.body_text = body_text
        self.body_html = body_html
        self.body_format = body_format
        self.size_bytes = size_bytes
        self.read_status = read_status
        self.priority = priority
        self.account_id = account_id
        self.created_at = created_at
        self.updated_at = updated_at

    @staticmethod
    def create_database():
        """Create the emails table"""
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS emails (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    uid VARCHAR(255),
                    subject TEXT,
                    sender TEXT,
                    recipients TEXT,
                    date DATETIME,
                    has_attachment BOOLEAN DEFAULT FALSE,
                    body LONGTEXT,
                    body_text LONGTEXT,
                    body_html LONGTEXT,
                    body_format ENUM('text', 'html', 'both') DEFAULT 'text',
                    size_bytes INT DEFAULT 0,
                    read_status BOOLEAN DEFAULT FALSE,
                    priority ENUM('high','normal','low') DEFAULT 'normal',
                    account_id INT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE,
                    UNIQUE KEY(uid, account_id),
                    INDEX idx_date (date),
                    INDEX idx_sender (sender(100)),
                    INDEX idx_subject (subject(100)),
                    INDEX idx_body_format (body_format)
                )
            """)
            conn.commit()
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def create_email(uid: str, subject: str, sender: str, recipients: str, date: datetime.datetime,
                    has_attachment: bool, body: str, size_bytes: int, account_id: int,
                    body_text: str = None, body_html: str = None, body_format: str = 'text') -> Optional['Email']:
        """Create a new email with enhanced body format support"""
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        try:
            # If new format fields are not provided, use the old body field
            if body_text is None and body_html is None:
                body_text = body
                body_format = 'text'
            
            cursor.execute("""
                INSERT INTO emails (uid, subject, sender, recipients, date, has_attachment, 
                                  body, body_text, body_html, body_format, size_bytes, account_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (uid, subject, sender, recipients, date, has_attachment, body, 
                  body_text, body_html, body_format, size_bytes, account_id))
            conn.commit()
            
            email_id = cursor.lastrowid
            return Email(
                id=email_id,
                uid=uid,
                subject=subject,
                sender=sender,
                recipients=recipients,
                date=date,
                has_attachment=has_attachment,
                body=body,
                body_text=body_text,
                body_html=body_html,
                body_format=body_format,
                size_bytes=size_bytes,
                account_id=account_id,
                created_at=datetime.datetime.now()
            )
        except mysql.connector.errors.IntegrityError:
            return None  # Email already exists
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def get_by_id(email_id: int) -> Optional['Email']:
        """Get email by ID"""
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        try:
            cursor.execute("SELECT * FROM emails WHERE id=%s", (email_id,))
            row = cursor.fetchone()
            
            if not row:
                return None
                
            return Email(
                id=row['id'],
                uid=row['uid'],
                subject=row['subject'],
                sender=row['sender'],
                recipients=row['recipients'],
                date=row['date'],
                has_attachment=row['has_attachment'],
                body=row.get('body'),  # For backward compatibility
                body_text=row.get('body_text'),
                body_html=row.get('body_html'),
                body_format=row.get('body_format', 'text'),
                size_bytes=row['size_bytes'],
                read_status=row['read_status'],
                priority=row['priority'],
                account_id=row['account_id'],
                created_at=row['created_at']
            )
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def get_account_emails(account_id: int, search_text: str = None, status_filter: str = None,
                          limit: int = None) -> List['Email']:
        """Get emails for an account with optional filtering"""
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        try:
            query = """
                SELECT e.*, GROUP_CONCAT(t.name ORDER BY t.name SEPARATOR ', ') as tags
                FROM emails e
                LEFT JOIN email_tags et ON e.id = et.email_id
                LEFT JOIN tags t ON et.tag_id = t.id
                WHERE e.account_id = %s
            """
            params = [account_id]
            
            # Apply search filter
            if search_text:
                query += " AND (e.subject LIKE %s OR e.sender LIKE %s OR e.body LIKE %s)"
                search_pattern = f"%{search_text}%"
                params.extend([search_pattern, search_pattern, search_pattern])
            
            # Apply status filter
            if status_filter == "Unread":
                query += " AND e.read_status = FALSE"
            elif status_filter == "Read":
                query += " AND e.read_status = TRUE"
            elif status_filter == "With Attachments":
                query += " AND e.has_attachment = TRUE"
            
            query += " GROUP BY e.id ORDER BY e.date DESC"
            
            if limit:
                query += f" LIMIT {limit}"
            
            cursor.execute(query, params)
            
            emails = []
            for row in cursor.fetchall():
                email = Email(
                    id=row['id'],
                    uid=row['uid'],
                    subject=row['subject'],
                    sender=row['sender'],
                    recipients=row['recipients'],
                    date=row['date'],
                    has_attachment=row['has_attachment'],
                    body=row.get('body'),  # For backward compatibility
                    body_text=row.get('body_text'),
                    body_html=row.get('body_html'),
                    body_format=row.get('body_format', 'text'),
                    size_bytes=row['size_bytes'],
                    read_status=row['read_status'],
                    priority=row['priority'],
                    account_id=row['account_id'],
                    created_at=row['created_at']
                )
                # Add tags as attribute
                email.tags = row['tags']
                emails.append(email)
            
            return emails
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def get_emails_by_tag(account_id: int, tag_name: str) -> List['Email']:
        """Get emails with a specific tag"""
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        try:
            query = """
                SELECT e.*, GROUP_CONCAT(DISTINCT t2.name ORDER BY t2.name SEPARATOR ', ') as all_tags
                FROM emails e
                INNER JOIN email_tags et ON e.id = et.email_id
                LEFT JOIN email_tags et2 ON e.id = et2.email_id
                LEFT JOIN tags t2 ON et2.tag_id = t2.id
                WHERE e.account_id = %s AND et.tag_id = (SELECT id FROM tags WHERE name = %s)
                GROUP BY e.id
                ORDER BY e.date DESC
            """
            
            cursor.execute(query, (account_id, tag_name))
            
            emails = []
            for row in cursor.fetchall():
                email = Email(
                    id=row['id'],
                    uid=row['uid'],
                    subject=row['subject'],
                    sender=row['sender'],
                    recipients=row['recipients'],
                    date=row['date'],
                    has_attachment=row['has_attachment'],
                    body=row.get('body'),  # For backward compatibility
                    body_text=row.get('body_text'),
                    body_html=row.get('body_html'),
                    body_format=row.get('body_format', 'text'),
                    size_bytes=row['size_bytes'],
                    read_status=row['read_status'],
                    priority=row['priority'],
                    account_id=row['account_id'],
                    created_at=row['created_at']
                )
                email.tags = row['all_tags']
                emails.append(email)
            
            return emails
        finally:
            cursor.close()
            conn.close()

    def mark_as_read(self):
        """Mark email as read"""
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        try:
            cursor.execute("UPDATE emails SET read_status=TRUE WHERE id=%s", (self.id,))
            conn.commit()
            self.read_status = True
        finally:
            cursor.close()
            conn.close()

    def mark_as_unread(self):
        """Mark email as unread"""
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        try:
            cursor.execute("UPDATE emails SET read_status=FALSE WHERE id=%s", (self.id,))
            conn.commit()
            self.read_status = False
        finally:
            cursor.close()
            conn.close()

    def delete(self):
        """Delete this email"""
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        try:
            cursor.execute("DELETE FROM emails WHERE id=%s", (self.id,))
            conn.commit()
        finally:
            cursor.close()
            conn.close()

    def get_best_body_content(self, prefer_html: bool = True) -> Tuple[str, str]:
        """
        Get the best available body content
        
        Args:
            prefer_html: Whether to prefer HTML over text when both available
            
        Returns:
            Tuple of (content, format) where format is 'html' or 'text'
        """
        if prefer_html and self.body_html:
            return self.body_html, 'html'
        elif self.body_text:
            return self.body_text, 'text'
        elif self.body_html:
            return self.body_html, 'html'
        elif self.body:  # Fallback to old body field
            return self.body, 'text'
        else:
            return "", 'text'
    
    def has_html_content(self) -> bool:
        """Check if email has HTML content"""
        return bool(self.body_html)
    
    def has_text_content(self) -> bool:
        """Check if email has plain text content"""
        return bool(self.body_text or self.body)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'uid': self.uid,
            'subject': self.subject,
            'sender': self.sender,
            'recipients': self.recipients,
            'date': self.date,
            'has_attachment': self.has_attachment,
            'body': self.body,
            'body_text': self.body_text,
            'body_html': self.body_html,
            'body_format': self.body_format,
            'size_bytes': self.size_bytes,
            'read_status': self.read_status,
            'priority': self.priority,
            'account_id': self.account_id,
            'created_at': self.created_at
        }

    def get_display_info(self) -> str:
        """Get display information for UI"""
        status_icon = "📧" if not self.read_status else "📖"
        attachment_icon = "📎" if self.has_attachment else ""
        date_str = self.date.strftime("%m/%d %H:%M") if self.date else ""
        
        # Truncate long text
        display_subject = (self.subject[:50] + "...") if len(self.subject) > 50 else self.subject
        display_sender = (self.sender[:30] + "...") if len(self.sender) > 30 else self.sender
        
        item_text = f"{status_icon} {attachment_icon} [{date_str}] {display_subject}\n    From: {display_sender}"
        if hasattr(self, 'tags') and self.tags:
            item_text += f" 🏷️ {self.tags}"
        
        return item_text 