import mysql.connector
import datetime
from typing import Optional, List, Dict, Any
from services.encryption_service import encrypt_text, decrypt_text
from config.database import DB_CONFIG

class EmailAccount:
    """Email account model"""
    
    def __init__(self, id: int = None, dashboard_user_id: int = None, imap_host: str = None,
                 imap_port: int = None, email: str = None, encrypted_password: bytes = None, last_sync: datetime.datetime = None,
                 sync_enabled: bool = True, session_expires: datetime.datetime = None,
                 created_at: datetime.datetime = None):
        self.id = id
        self.dashboard_user_id = dashboard_user_id
        self.imap_host = imap_host
        self.imap_port = imap_port or 993  # Default to 993 if not specified
        self.email = email
        self.encrypted_password = encrypted_password
        self.last_sync = last_sync
        self.sync_enabled = sync_enabled
        self.session_expires = session_expires
        self.created_at = created_at

    @staticmethod
    def create_database():
        """Create the accounts table"""
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS accounts (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    dashboard_user_id INT NOT NULL,
                    imap_host VARCHAR(255),
                    email VARCHAR(255),
                    encrypted_password BLOB,
                    last_sync TIMESTAMP NULL,
                    sync_enabled BOOLEAN DEFAULT TRUE,
                    session_expires TIMESTAMP NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (dashboard_user_id) REFERENCES dashboard_users(id) ON DELETE CASCADE,
                    UNIQUE KEY unique_user_email (dashboard_user_id, email)
                )
            """)
            conn.commit()
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def create_account(user_id: int, imap_host: str, imap_port: int, email: str, password: str) -> Optional['EmailAccount']:
        """Create a new email account"""
        encrypted_password = encrypt_text(password)
        
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO accounts (dashboard_user_id, imap_host, imap_port, email, encrypted_password)
                VALUES (%s, %s, %s, %s, %s)
            """, (user_id, imap_host, imap_port, email, encrypted_password))
            conn.commit()
            
            account_id = cursor.lastrowid
            return EmailAccount(
                id=account_id,
                dashboard_user_id=user_id,
                imap_host=imap_host,
                imap_port=imap_port,
                email=email,
                encrypted_password=encrypted_password,
                created_at=datetime.datetime.now()
            )
        except mysql.connector.errors.IntegrityError:
            return None  # Email already exists for this user
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def get_by_id(account_id: int) -> Optional['EmailAccount']:
        """Get email account by ID"""
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        try:
            cursor.execute("SELECT * FROM accounts WHERE id=%s", (account_id,))
            row = cursor.fetchone()
            
            if not row:
                return None
                
            return EmailAccount(
                id=row['id'],
                dashboard_user_id=row['dashboard_user_id'],
                imap_host=row['imap_host'],
                imap_port=row.get('imap_port', 993),  # Default to 993 if not present
                email=row['email'],
                encrypted_password=row['encrypted_password'],
                last_sync=row['last_sync'],
                sync_enabled=row['sync_enabled'],
                session_expires=row['session_expires'],
                created_at=row['created_at']
            )
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def get_user_accounts(user_id: int) -> List['EmailAccount']:
        """Get all email accounts for a user"""
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        try:
            cursor.execute("""
                SELECT * FROM accounts 
                WHERE dashboard_user_id=%s AND (session_expires IS NULL OR session_expires > NOW())
                ORDER BY created_at DESC
            """, (user_id,))
            
            accounts = []
            for row in cursor.fetchall():
                accounts.append(EmailAccount(
                    id=row['id'],
                    dashboard_user_id=row['dashboard_user_id'],
                    imap_host=row['imap_host'],
                    imap_port=row.get('imap_port', 993),  # Default to 993 if not present
                    email=row['email'],
                    encrypted_password=row['encrypted_password'],
                    last_sync=row['last_sync'],
                    sync_enabled=row['sync_enabled'],
                    session_expires=row['session_expires'],
                    created_at=row['created_at']
                ))
            
            return accounts
        finally:
            cursor.close()
            conn.close()

    def get_password(self) -> str:
        """Get decrypted password"""
        if self.encrypted_password:
            return decrypt_text(self.encrypted_password)
        return ""

    def update_last_sync(self):
        """Update last sync timestamp"""
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        try:
            cursor.execute("UPDATE accounts SET last_sync=NOW() WHERE id=%s", (self.id,))
            conn.commit()
            self.last_sync = datetime.datetime.now()
        finally:
            cursor.close()
            conn.close()

    def update_sync_status(self, enabled: bool):
        """Update sync enabled status"""
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        try:
            cursor.execute("UPDATE accounts SET sync_enabled=%s WHERE id=%s", (enabled, self.id))
            conn.commit()
            self.sync_enabled = enabled
        finally:
            cursor.close()
            conn.close()

    def set_session_expiry(self, expiry: datetime.datetime):
        """Set session expiry"""
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        try:
            cursor.execute("UPDATE accounts SET session_expires=%s WHERE id=%s", (expiry, self.id))
            conn.commit()
            self.session_expires = expiry
        finally:
            cursor.close()
            conn.close()

    def delete(self):
        """Delete this email account"""
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        try:
            cursor.execute("DELETE FROM accounts WHERE id=%s", (self.id,))
            conn.commit()
        finally:
            cursor.close()
            conn.close()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'dashboard_user_id': self.dashboard_user_id,
            'imap_host': self.imap_host,
            'imap_port': self.imap_port,
            'email': self.email,
            'last_sync': self.last_sync,
            'sync_enabled': self.sync_enabled,
            'session_expires': self.session_expires,
            'created_at': self.created_at
        }

    def get_display_info(self) -> str:
        """Get display information for UI"""
        status = "🟢" if self.sync_enabled else "🔴"
        sync_info = f"Last: {self.last_sync.strftime('%m/%d %H:%M')}" if self.last_sync else "Never"
        return f"{status} {self.email} @ {self.imap_host}:{self.imap_port} ({sync_info})" 