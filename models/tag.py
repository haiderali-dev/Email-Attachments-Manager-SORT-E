import mysql.connector
import datetime
from typing import Optional, List, Dict, Any
from config.database import DB_CONFIG

class Tag:
    """Tag model"""
    
    def __init__(self, id: int = None, name: str = None, color: str = "#2180F3",
                 dashboard_user_id: int = None, created_at: datetime.datetime = None):
        self.id = id
        self.name = name
        self.color = color
        self.dashboard_user_id = dashboard_user_id
        self.created_at = created_at

    @staticmethod
    def create_database():
        """Create the tags table"""
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tags (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(100),
                    color VARCHAR(7) DEFAULT '#2196F3',
                    dashboard_user_id INT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (dashboard_user_id) REFERENCES dashboard_users(id) ON DELETE CASCADE,
                    UNIQUE KEY unique_user_tag (dashboard_user_id, name)
                )
            """)
            conn.commit()
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def create_tag(name: str, user_id: int, color: str = '#2196F3') -> Optional['Tag']:
        """Create a new tag"""
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO tags (name, color, dashboard_user_id) VALUES (%s, %s, %s)
            """, (name, color, user_id))
            conn.commit()
            
            tag_id = cursor.lastrowid
            return Tag(
                id=tag_id,
                name=name,
                color=color,
                dashboard_user_id=user_id,
                created_at=datetime.datetime.now()
            )
        except mysql.connector.errors.IntegrityError:
            return None  # Tag already exists for this user
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def get_or_create_tag(name: str, user_id: int, color: str = '#2196F3') -> 'Tag':
        """Get existing tag or create new one"""
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        try:
            # Try to get existing tag
            cursor.execute("SELECT * FROM tags WHERE name=%s AND dashboard_user_id=%s", 
                         (name, user_id))
            row = cursor.fetchone()
            
            if row:
                return Tag(
                    id=row['id'],
                    name=row['name'],
                    color=row['color'],
                    dashboard_user_id=row['dashboard_user_id'],
                    created_at=row['created_at']
                )
            else:
                # Create new tag
                cursor.execute("""
                    INSERT INTO tags (name, color, dashboard_user_id) VALUES (%s, %s, %s)
                """, (name, color, user_id))
                conn.commit()
                
                tag_id = cursor.lastrowid
                return Tag(
                    id=tag_id,
                    name=name,
                    color=color,
                    dashboard_user_id=user_id,
                    created_at=datetime.datetime.now()
                )
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def get_by_id(tag_id: int) -> Optional['Tag']:
        """Get tag by ID"""
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        try:
            cursor.execute("SELECT * FROM tags WHERE id=%s", (tag_id,))
            row = cursor.fetchone()
            
            if not row:
                return None
                
            return Tag(
                id=row['id'],
                name=row['name'],
                color=row['color'],
                dashboard_user_id=row['dashboard_user_id'],
                created_at=row['created_at']
            )
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def get_by_name(name: str, user_id: int) -> Optional['Tag']:
        """Get tag by name for a specific user"""
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        try:
            cursor.execute("SELECT * FROM tags WHERE name=%s AND dashboard_user_id=%s", 
                         (name, user_id))
            row = cursor.fetchone()
            
            if not row:
                return None
                
            return Tag(
                id=row['id'],
                name=row['name'],
                color=row['color'],
                dashboard_user_id=row['dashboard_user_id'],
                created_at=row['created_at']
            )
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def get_user_tags(user_id: int, account_id: int = None) -> List['Tag']:
        """Get all tags for a user with usage counts"""
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        try:
            if account_id:
                # Get tags with usage counts for specific account
                cursor.execute("""
                    SELECT t.*, COUNT(et.email_id) as usage_count
                    FROM tags t
                    LEFT JOIN email_tags et ON t.id = et.tag_id
                    LEFT JOIN emails e ON et.email_id = e.id
                    WHERE t.dashboard_user_id = %s AND (e.account_id = %s OR e.account_id IS NULL)
                    GROUP BY t.id, t.name, t.color, t.dashboard_user_id, t.created_at
                    ORDER BY usage_count DESC, t.name
                """, (user_id, account_id))
            else:
                # Get all tags for user
                cursor.execute("""
                    SELECT t.*, COUNT(et.email_id) as usage_count
                    FROM tags t
                    LEFT JOIN email_tags et ON t.id = et.tag_id
                    WHERE t.dashboard_user_id = %s
                    GROUP BY t.id, t.name, t.color, t.dashboard_user_id, t.created_at
                    ORDER BY usage_count DESC, t.name
                """, (user_id,))
            
            tags = []
            for row in cursor.fetchall():
                tag = Tag(
                    id=row['id'],
                    name=row['name'],
                    color=row['color'],
                    dashboard_user_id=row['dashboard_user_id'],
                    created_at=row['created_at']
                )
                tag.usage_count = row['usage_count']
                tags.append(tag)
            
            return tags
        finally:
            cursor.close()
            conn.close()

    def add_to_email(self, email_id: int) -> bool:
        """Add this tag to an email"""
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        try:
            cursor.execute("INSERT IGNORE INTO email_tags (email_id, tag_id) VALUES (%s, %s)", 
                         (email_id, self.id))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            cursor.close()
            conn.close()

    def remove_from_email(self, email_id: int) -> bool:
        """Remove this tag from an email"""
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        try:
            cursor.execute("DELETE FROM email_tags WHERE email_id=%s AND tag_id=%s", 
                         (email_id, self.id))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            cursor.close()
            conn.close()

    def get_emails(self, account_id: int = None) -> List[int]:
        """Get list of email IDs that have this tag"""
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        try:
            if account_id:
                cursor.execute("""
                    SELECT et.email_id FROM email_tags et
                    JOIN emails e ON et.email_id = e.id
                    WHERE et.tag_id = %s AND e.account_id = %s
                """, (self.id, account_id))
            else:
                cursor.execute("SELECT email_id FROM email_tags WHERE tag_id = %s", (self.id,))
            
            return [row[0] for row in cursor.fetchall()]
        finally:
            cursor.close()
            conn.close()

    def update_color(self, color: str):
        """Update tag color"""
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        try:
            cursor.execute("UPDATE tags SET color=%s WHERE id=%s", (color, self.id))
            conn.commit()
            self.color = color
        finally:
            cursor.close()
            conn.close()

    def delete(self):
        """Delete this tag (will remove from all emails)"""
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        try:
            cursor.execute("DELETE FROM tags WHERE id=%s", (self.id,))
            conn.commit()
        finally:
            cursor.close()
            conn.close()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'color': self.color,
            'dashboard_user_id': self.dashboard_user_id,
            'created_at': self.created_at,
            'usage_count': getattr(self, 'usage_count', 0)
        }

    def get_display_info(self) -> str:
        """Get display information for UI"""
        usage_count = getattr(self, 'usage_count', 0)
        return f"{self.name} ({usage_count})" 