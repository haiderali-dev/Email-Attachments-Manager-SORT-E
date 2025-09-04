import os
import tempfile
import mimetypes
from typing import List, Dict, Any, Optional
from imap_tools import MailBox, AND
import mysql.connector
from config.database import DB_CONFIG

class AttachmentFetchService:
    """Service for fetching email attachments from IMAP servers"""
    
    def __init__(self):
        self.temp_dir = tempfile.mkdtemp(prefix="email_attachments_")
        self.temp_files = []  # Keep track of created temp files
    
    def get_email_attachments(self, email_id: int, account_id: int) -> List[Dict[str, Any]]:
        """
        Fetch attachments for a specific email from IMAP server
        
        Args:
            email_id: Database email ID
            account_id: Database account ID
            
        Returns:
            List of attachment dictionaries with filename, size, content, etc.
        """
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        try:
            # Get email UID and account details
            cursor.execute("""
                SELECT e.uid, a.imap_host, a.imap_port, a.email, a.encrypted_password
                FROM emails e
                JOIN accounts a ON e.account_id = a.id
                WHERE e.id = %s AND e.account_id = %s
            """, (email_id, account_id))
            
            result = cursor.fetchone()
            if not result:
                print(f"No email found with ID {email_id} and account ID {account_id}")
                return []
                
            uid, imap_host, imap_port, email, encrypted_password = result
            
            # Fetch attachments from IMAP
            attachments = self._fetch_attachments_from_imap(
                imap_host, imap_port, email, encrypted_password, uid
            )
            
            return attachments
            
        except Exception as e:
            print(f"Error fetching attachments for email {email_id}: {e}")
            return []
        finally:
            cursor.close()
            conn.close()
    
    def _fetch_attachments_from_imap(self, imap_host: str, imap_port: int, email: str, 
                                   encrypted_password: bytes, uid: str) -> List[Dict[str, Any]]:
        """
        Fetch attachments from IMAP server
        
        Args:
            imap_host: IMAP server host
            imap_port: IMAP server port
            email: Email address
            encrypted_password: Encrypted password
            uid: Email UID
            
        Returns:
            List of attachment dictionaries
        """
        try:
            from services.encryption_service import decrypt_text
            
            # Decrypt password
            password = decrypt_text(encrypted_password)
            
            # Connect to IMAP server
            with MailBox(imap_host, port=imap_port).login(email, password) as mailbox:
                # Find the specific email by UID
                messages = mailbox.fetch(AND(uid=uid))
                
                attachments = []
                for msg in messages:
                    if hasattr(msg, 'attachments') and msg.attachments:
                        for i, attachment in enumerate(msg.attachments):
                            try:
                                # Get attachment info
                                filename = attachment.filename or f"attachment_{i}"
                                mime_type = self._get_mime_type(filename)
                                
                                # Get attachment content
                                if hasattr(attachment, 'payload'):
                                    content = attachment.payload
                                elif hasattr(attachment, 'content'):
                                    content = attachment.content
                                else:
                                    print(f"No content found for attachment {filename}")
                                    continue
                                
                                size = len(content) if content else 0
                                
                                # Create temporary file for viewing
                                temp_file = self._create_temp_file(content, filename)
                                if not temp_file:
                                    print(f"Failed to create temp file for {filename}")
                                    continue
                                
                                attachment_info = {
                                    'filename': filename,
                                    'size': size,
                                    'size_formatted': self._format_size(size),
                                    'mime_type': mime_type,
                                    'temp_path': temp_file,
                                    'content': content
                                }
                                
                                attachments.append(attachment_info)
                                print(f"Successfully processed attachment: {filename} ({self._format_size(size)})")
                                
                            except Exception as att_error:
                                print(f"Error processing attachment {i}: {att_error}")
                                continue
                
                print(f"Found {len(attachments)} attachments for email UID {uid}")
                return attachments
                
        except Exception as e:
            print(f"Error connecting to IMAP server: {e}")
            return []
    
    def _get_mime_type(self, filename: str) -> str:
        """Get MIME type for filename"""
        mime_type, _ = mimetypes.guess_type(filename)
        return mime_type or 'application/octet-stream'
    
    def _format_size(self, size_bytes: int) -> str:
        """Format file size in human readable format"""
        if size_bytes == 0:
            return "0 B"
        
        size_names = ["B", "KB", "MB", "GB"]
        i = 0
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024.0
            i += 1
        
        return f"{size_bytes:.1f} {size_names[i]}"
    
    def _create_temp_file(self, content: bytes, filename: str) -> Optional[str]:
        """Create temporary file for attachment viewing"""
        try:
            # Create temporary file with proper extension
            suffix = os.path.splitext(filename)[1]
            if not suffix:
                # If no extension, try to determine from MIME type
                mime_type = self._get_mime_type(filename)
                if mime_type.startswith('text/'):
                    suffix = '.txt'
                elif mime_type.startswith('image/'):
                    suffix = '.img'
                else:
                    suffix = '.bin'
            
            with tempfile.NamedTemporaryFile(
                delete=False, 
                suffix=suffix,
                dir=self.temp_dir
            ) as temp_file:
                temp_path = temp_file.name
                
                # Write attachment content
                temp_file.write(content)
                temp_file.flush()  # Ensure content is written to disk
                
                # Verify file was created and has content
                if os.path.exists(temp_path) and os.path.getsize(temp_path) > 0:
                    print(f"Created temp file: {temp_path} ({os.path.getsize(temp_path)} bytes)")
                    self.temp_files.append(temp_path)  # Track the temp file
                    return temp_path
                else:
                    print(f"Failed to create temp file for {filename}")
                    return None
                
        except Exception as e:
            print(f"Error creating temp file for {filename}: {e}")
            return None
    
    def cleanup_temp_files(self):
        """Clean up temporary files"""
        try:
            import shutil
            # Clean up individual temp files
            for temp_file in self.temp_files:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
                    print(f"Cleaned up temp file: {temp_file}")
            
            # Clean up temp directory
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
                print(f"Cleaned up temp directory: {self.temp_dir}")
        except Exception as e:
            print(f"Error cleaning up temp files: {e}")
    
    def __del__(self):
        """Cleanup on object destruction - but don't do it immediately"""
        # Don't clean up immediately to allow time for file operations
        pass 