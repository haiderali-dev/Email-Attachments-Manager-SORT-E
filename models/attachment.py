import mysql.connector
import datetime
import os
from typing import Optional, List, Dict, Any
from config.database import DB_CONFIG

class Attachment:
    """Attachment model"""
    
    def __init__(self, id: int = None, email_id: int = None, filename: str = None,
                 file_path: str = None, file_size: int = 0, mime_type: str = None,
                 content_type: str = None, created_at: datetime.datetime = None):
        self.id = id
        self.email_id = email_id
        self.filename = filename
        self.file_path = file_path
        self.file_size = file_size
        self.mime_type = mime_type
        self.content_type = content_type
        self.created_at = created_at

    @staticmethod
    def create_database():
        """Create the attachments table"""
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS attachments (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    email_id INT NOT NULL,
                    filename VARCHAR(255) NOT NULL,
                    file_path TEXT NOT NULL,
                    file_size INT DEFAULT 0,
                    mime_type VARCHAR(100),
                    content_type VARCHAR(100),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (email_id) REFERENCES emails(id) ON DELETE CASCADE,
                    INDEX idx_email_id (email_id),
                    INDEX idx_filename (filename(100)),
                    INDEX idx_mime_type (mime_type)
                )
            """)
            conn.commit()
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def create_attachment(email_id: int, filename: str, file_path: str, file_size: int = 0,
                         mime_type: str = None, content_type: str = None) -> Optional['Attachment']:
        """Create a new attachment record"""
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO attachments (email_id, filename, file_path, file_size, mime_type, content_type)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (email_id, filename, file_path, file_size, mime_type, content_type))
            conn.commit()
            
            attachment_id = cursor.lastrowid
            return Attachment(
                id=attachment_id,
                email_id=email_id,
                filename=filename,
                file_path=file_path,
                file_size=file_size,
                mime_type=mime_type,
                content_type=content_type,
                created_at=datetime.datetime.now()
            )
        except mysql.connector.errors.IntegrityError:
            return None  # Attachment already exists
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def get_by_id(attachment_id: int) -> Optional['Attachment']:
        """Get attachment by ID"""
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        try:
            cursor.execute("""
                SELECT * FROM attachments WHERE id = %s
            """, (attachment_id,))
            
            result = cursor.fetchone()
            if result:
                return Attachment(**result)
            return None
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def get_by_email_id(email_id: int) -> List['Attachment']:
        """Get all attachments for an email"""
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        try:
            cursor.execute("""
                SELECT * FROM attachments WHERE email_id = %s ORDER BY filename
            """, (email_id,))
            
            results = cursor.fetchall()
            return [Attachment(**result) for result in results]
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def create_device_attachment(attachment_id: int, original_filename: str, device_filename: str, device_path: str) -> bool:
        """Create a record of attachment saved to device"""
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO device_attachments (attachment_id, original_filename, device_filename, device_path)
                VALUES (%s, %s, %s, %s)
            """, (attachment_id, original_filename, device_filename, device_path))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error creating device attachment record: {e}")
            return False
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def search_attachments(search_query: str, user_id: int = None, account_id: int = None) -> List[Dict[str, Any]]:
        """
        Search downloaded attachments with related email metadata
        
        Args:
            search_query: Search term to match against filename, email subject, sender, body, etc.
            user_id: Optional user ID filter
            account_id: Optional account ID filter
            
        Returns:
            List of attachment dictionaries with email metadata
        """
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        try:
            # Build the search query
            search_pattern = f"%{search_query}%"
            
            # Base query with email metadata and device attachment info
            query = """
                SELECT 
                    a.id as attachment_id,
                    a.filename,
                    a.file_path,
                    a.file_size,
                    a.mime_type,
                    a.content_type,
                    a.created_at as attachment_created,
                    e.id as email_id,
                    e.subject,
                    e.sender,
                    e.body,
                    e.date as email_date,
                    e.has_attachment,
                    acc.email as account_email,
                    acc.imap_host,
                    da.device_filename,
                    da.device_path,
                    da.saved_at
                FROM attachments a
                JOIN emails e ON a.email_id = e.id
                JOIN accounts acc ON e.account_id = acc.id
                LEFT JOIN device_attachments da ON a.id = da.attachment_id
                WHERE (
                    LOWER(a.filename) LIKE LOWER(%s) OR
                    LOWER(e.subject) LIKE LOWER(%s) OR
                    LOWER(e.sender) LIKE LOWER(%s) OR
                    LOWER(e.body) LIKE LOWER(%s) OR
                    LOWER(a.mime_type) LIKE LOWER(%s) OR
                    LOWER(da.device_filename) LIKE LOWER(%s)
                )
            """
            
            params = [search_pattern, search_pattern, search_pattern, search_pattern, search_pattern, search_pattern]
            
            # Add user filter if provided
            if user_id:
                query += " AND acc.dashboard_user_id = %s"
                params.append(user_id)
            
            # Add account filter if provided
            if account_id:
                query += " AND e.account_id = %s"
                params.append(account_id)
            
            query += " ORDER BY e.date DESC, a.filename"
            
            cursor.execute(query, params)
            results = cursor.fetchall()
            
            return results
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def search_all_attachments(search_query: str, user_id: int = None, account_id: int = None) -> List[Dict[str, Any]]:
        """
        Search all attachments from IMAP (including those not downloaded to device)
        
        Args:
            search_query: Search term to match against filename, email subject, sender, body, etc.
            user_id: Optional user ID filter
            account_id: Optional account ID filter
            
        Returns:
            List of attachment dictionaries with email metadata
        """
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        try:
            # Clean the search query
            search_query = search_query.strip()
            if not search_query:
                # If no search query, return all attachments
                search_pattern = "%"
            else:
                # Use the search query as a phrase for more specific matching, case-insensitive
                search_pattern = f"%{search_query.lower()}%"
            
            # First, get downloaded attachments that match the search
            downloaded_query = """
                SELECT 
                    a.id as attachment_id,
                    a.filename,
                    a.file_path,
                    a.file_size,
                    a.mime_type,
                    a.content_type,
                    a.created_at as attachment_created,
                    e.id as email_id,
                    e.subject,
                    e.sender,
                    e.body,
                    e.date as email_date,
                    e.has_attachment,
                    acc.email as account_email,
                    acc.imap_host,
                    acc.id as account_id,
                    FALSE as is_inbox_attachment,
                    da.device_filename,
                    da.device_path,
                    da.saved_at
                FROM attachments a
                JOIN emails e ON a.email_id = e.id
                JOIN accounts acc ON e.account_id = acc.id
                LEFT JOIN device_attachments da ON a.id = da.attachment_id
                WHERE (
                    LOWER(a.filename) LIKE LOWER(%s) OR
                    LOWER(e.subject) LIKE LOWER(%s) OR
                    LOWER(e.sender) LIKE LOWER(%s) OR
                    LOWER(e.body) LIKE LOWER(%s) OR
                    LOWER(a.mime_type) LIKE LOWER(%s) OR
                    LOWER(e.recipients) LIKE LOWER(%s) OR
                    LOWER(da.device_filename) LIKE LOWER(%s)
                )
            """
            
            downloaded_params = [search_pattern] * 7
            
            # Add user filter if provided
            if user_id:
                downloaded_query += " AND acc.dashboard_user_id = %s"
                downloaded_params.append(user_id)
            
            # Add account filter if provided
            if account_id:
                downloaded_query += " AND e.account_id = %s"
                downloaded_params.append(account_id)
            
            downloaded_query += " ORDER BY e.date DESC, a.filename"
            
            cursor.execute(downloaded_query, downloaded_params)
            downloaded_results = cursor.fetchall()
            
            # Get list of email IDs that already have downloaded attachments
            downloaded_email_ids = [result['email_id'] for result in downloaded_results]
            
            # Then, get emails with attachments that match (excluding those already downloaded)
            inbox_query = """
                SELECT 
                    NULL as attachment_id,
                    'Multiple Attachments' as filename,
                    '' as file_path,
                    0 as file_size,
                    'Unknown' as mime_type,
                    'Unknown' as content_type,
                    NOW() as attachment_created,
                    e.id as email_id,
                    e.subject,
                    e.sender,
                    e.body,
                    e.date as email_date,
                    e.has_attachment,
                    acc.email as account_email,
                    acc.imap_host,
                    acc.id as account_id,
                    TRUE as is_inbox_attachment
                FROM emails e
                JOIN accounts acc ON e.account_id = acc.id
                WHERE e.has_attachment = TRUE AND (
                    LOWER(e.subject) LIKE LOWER(%s) OR
                    LOWER(e.sender) LIKE LOWER(%s) OR
                    LOWER(e.body) LIKE LOWER(%s) OR
                    LOWER(e.recipients) LIKE LOWER(%s)
                )
            """
            
            inbox_params = [search_pattern] * 4
            
            # Exclude emails that already have downloaded attachments
            if downloaded_email_ids:
                placeholders = ','.join(['%s'] * len(downloaded_email_ids))
                inbox_query += f" AND e.id NOT IN ({placeholders})"
                inbox_params.extend(downloaded_email_ids)
            
            # Add user filter if provided
            if user_id:
                inbox_query += " AND acc.dashboard_user_id = %s"
                inbox_params.append(user_id)
            
            # Add account filter if provided
            if account_id:
                inbox_query += " AND e.account_id = %s"
                inbox_params.append(account_id)
            
            inbox_query += " ORDER BY e.date DESC"
            
            cursor.execute(inbox_query, inbox_params)
            inbox_results = cursor.fetchall()
            
            # Now fetch real attachment metadata for INBOX results
            enhanced_inbox_results = []
            from services.attachment_fetch_service import AttachmentFetchService
            attachment_fetch_service = AttachmentFetchService()
            
            for inbox_result in inbox_results:
                try:
                    # Get real attachment metadata from IMAP
                    attachments = attachment_fetch_service.get_email_attachments(
                        inbox_result['email_id'], 
                        inbox_result['account_id']
                    )
                    
                    if attachments:
                        # Create a result for each attachment found
                        for attachment in attachments:
                            enhanced_result = inbox_result.copy()
                            enhanced_result['attachment_id'] = None  # Not in database
                            enhanced_result['filename'] = attachment['filename']
                            enhanced_result['file_size'] = attachment['size']
                            enhanced_result['mime_type'] = attachment.get('mime_type', 'Unknown')
                            enhanced_result['content_type'] = attachment.get('content_type', 'Unknown')
                            enhanced_inbox_results.append(enhanced_result)
                    else:
                        # Keep the original result if no attachments found
                        enhanced_inbox_results.append(inbox_result)
                        
                except Exception as e:
                    print(f"Error fetching attachments for email {inbox_result['email_id']}: {e}")
                    # Keep the original result if there's an error
                    enhanced_inbox_results.append(inbox_result)
            
            # Combine downloaded and INBOX results
            all_results = downloaded_results + enhanced_inbox_results
            
            # Sort by email date (newest first) and then by filename
            all_results.sort(key=lambda x: (x['email_date'], x['filename']), reverse=True)
            
            return all_results
            
        except Exception as e:
            print(f"search_all_attachments error: {e}")
            import traceback
            traceback.print_exc()
            raise
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def get_attachment_with_email_metadata(attachment_id: int) -> Optional[Dict[str, Any]]:
        """Get attachment with full email metadata"""
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        try:
            cursor.execute("""
                SELECT 
                    a.id as attachment_id,
                    a.filename,
                    a.file_path,
                    a.file_size,
                    a.mime_type,
                    a.content_type,
                    a.created_at as attachment_created,
                    e.id as email_id,
                    e.subject,
                    e.sender,
                    e.recipients,
                    e.body,
                    e.date as email_date,
                    e.has_attachment,
                    e.size_bytes as email_size,
                    e.read_status,
                    e.priority,
                    acc.email as account_email,
                    acc.imap_host
                FROM attachments a
                JOIN emails e ON a.email_id = e.id
                JOIN accounts acc ON e.account_id = acc.id
                WHERE a.id = %s
            """, (attachment_id,))
            
            result = cursor.fetchone()
            if result:
                # Get other attachments from the same email
                cursor.execute("""
                    SELECT id, filename, file_size, mime_type
                    FROM attachments 
                    WHERE email_id = %s AND id != %s
                    ORDER BY filename
                """, (result['email_id'], attachment_id))
                
                other_attachments = cursor.fetchall()
                result['other_attachments'] = other_attachments
                
                return result
            return None
        finally:
            cursor.close()
            conn.close()

    def delete(self) -> bool:
        """Delete this attachment record"""
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        try:
            cursor.execute("DELETE FROM attachments WHERE id = %s", (self.id,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            cursor.close()
            conn.close()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'email_id': self.email_id,
            'filename': self.filename,
            'file_path': self.file_path,
            'file_size': self.file_size,
            'mime_type': self.mime_type,
            'content_type': self.content_type,
            'created_at': self.created_at
        }

    def get_display_info(self) -> str:
        """Get display information for the attachment"""
        size_str = f"{self.file_size:,} bytes" if self.file_size else "Unknown size"
        return f"{self.filename} ({size_str})" 