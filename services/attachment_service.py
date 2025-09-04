import os
import shutil
import hashlib
import mimetypes
from typing import List, Dict, Any, Optional
from utils.helpers import get_safe_filename, format_size, create_directory_if_not_exists
from models.attachment import Attachment

class AttachmentService:
    """Email attachment handling service"""
    
    def __init__(self):
        self.base_attachment_dir = 'attachments'
        self.should_stop = False

    def save_attachments_safe(self, attachments: List, base_path: str, email_id: int) -> Dict[str, Any]:
        """
        Save email attachments with improved error handling and duplicate prevention
        
        Args:
            attachments: List of email attachments
            base_path: Base directory path for saving
            email_id: Email ID for organization
            
        Returns:
            Dict with results: {'saved': int, 'skipped': int, 'errors': List[str]}
        """
        if not base_path or not attachments:
            return {'saved': 0, 'skipped': 0, 'errors': []}
            
        # Create base directory if it doesn't exist
        if not create_directory_if_not_exists(base_path):
            return {'saved': 0, 'skipped': 0, 'errors': ['Failed to create base directory']}
        
        # Create email-specific folder
        email_folder = os.path.join(base_path, f"email_{email_id}")
        if not create_directory_if_not_exists(email_folder):
            return {'saved': 0, 'skipped': 0, 'errors': ['Failed to create email folder']}
        
        # Get list of existing files to avoid duplicates
        existing_files = set()
        if os.path.exists(email_folder):
            existing_files = set(os.listdir(email_folder))
        
        # Save each attachment
        saved_count = 0
        skipped_count = 0
        errors = []
        
        for i, attachment in enumerate(attachments):
            if self.should_stop:
                break
                
            try:
                # Get safe filename
                filename = self._get_safe_filename(attachment, i, email_folder)
                
                # Check if this exact file already exists
                if filename in existing_files:
                    # Additionally check file size to ensure it's not a partial download
                    existing_filepath = os.path.join(email_folder, filename)
                    if os.path.exists(existing_filepath) and os.path.getsize(existing_filepath) > 0:
                        print(f"Attachment {filename} already exists for email {email_id}, skipping")
                        skipped_count += 1
                        continue
                
                filepath = os.path.join(email_folder, filename)
                
                # Write attachment data
                with open(filepath, 'wb') as f:
                    if hasattr(attachment, 'payload'):
                        f.write(attachment.payload)
                    elif hasattr(attachment, 'content'):
                        f.write(attachment.content)
                    else:
                        errors.append(f"Attachment {i} has no payload or content")
                        continue
                
                # Get file size and MIME type
                file_size = os.path.getsize(filepath)
                mime_type, _ = mimetypes.guess_type(filename)
                
                # Save to database
                try:
                    Attachment.create_attachment(
                        email_id=email_id,
                        filename=filename,
                        file_path=filepath,
                        file_size=file_size,
                        mime_type=mime_type,
                        content_type=getattr(attachment, 'content_type', mime_type)
                    )
                except Exception as db_error:
                    errors.append(f"Database error for {filename}: {db_error}")
                    # Continue anyway since file was saved
                
                saved_count += 1
                print(f"Saved new attachment: {filename}")
                        
            except Exception as att_error:
                errors.append(f"Error saving attachment {i} for email {email_id}: {att_error}")
                continue
        
        return {
            'saved': saved_count,
            'skipped': skipped_count,
            'errors': errors
        }

    def _get_safe_filename(self, attachment, index: int, folder: str) -> str:
        """
        Get a safe filename for the attachment with better duplicate handling
        
        Args:
            attachment: Email attachment object
            index: Attachment index
            folder: Folder to check for existing files
            
        Returns:
            Safe filename
        """
        try:
            # Try to get filename from attachment
            if hasattr(attachment, 'filename') and attachment.filename:
                filename = str(attachment.filename)
            elif hasattr(attachment, 'name') and attachment.name:
                filename = str(attachment.name)
            else:
                filename = f"attachment_{index + 1}"
            
            return get_safe_filename(filename, index, folder)
            
        except Exception as e:
            print(f"Error getting safe filename: {e}")
            return f"attachment_{index + 1}"

    def save_email_attachments(self, email_id: int, attachment_path: str) -> Dict[str, Any]:
        """
        Save attachments for a specific email
        
        Args:
            email_id: Email ID
            attachment_path: Path to save attachments
            
        Returns:
            Dict with results
        """
        # This would typically fetch attachments from the email
        # For now, return empty result
        return {'saved': 0, 'skipped': 0, 'errors': ['Not implemented']}

    def get_attachment_info(self, file_path: str) -> Dict[str, Any]:
        """
        Get information about an attachment file
        
        Args:
            file_path: Path to the attachment file
            
        Returns:
            Dict with file information
        """
        if not os.path.exists(file_path):
            return {'error': 'File not found'}
            
        try:
            stat = os.stat(file_path)
            file_size = stat.st_size
            
            return {
                'filename': os.path.basename(file_path),
                'size': file_size,
                'size_formatted': format_size(file_size),
                'created': stat.st_ctime,
                'modified': stat.st_mtime,
                'path': file_path
            }
        except Exception as e:
            return {'error': str(e)}

    def get_email_attachments(self, email_id: int, base_path: str) -> List[Dict[str, Any]]:
        """
        Get all attachments for an email
        
        Args:
            email_id: Email ID
            base_path: Base attachment directory
            
        Returns:
            List of attachment information dictionaries
        """
        email_folder = os.path.join(base_path, f"email_{email_id}")
        
        if not os.path.exists(email_folder):
            return []
            
        attachments = []
        try:
            for filename in os.listdir(email_folder):
                file_path = os.path.join(email_folder, filename)
                if os.path.isfile(file_path):
                    info = self.get_attachment_info(file_path)
                    if 'error' not in info:
                        attachments.append(info)
        except Exception as e:
            print(f"Error getting attachments for email {email_id}: {e}")
            
        return attachments

    def delete_attachment(self, file_path: str) -> bool:
        """
        Delete an attachment file
        
        Args:
            file_path: Path to the file to delete
            
        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
            return False
        except Exception as e:
            print(f"Error deleting attachment {file_path}: {e}")
            return False

    def delete_email_attachments(self, email_id: int, base_path: str) -> bool:
        """
        Delete all attachments for an email
        
        Args:
            email_id: Email ID
            base_path: Base attachment directory
            
        Returns:
            True if deleted successfully, False otherwise
        """
        email_folder = os.path.join(base_path, f"email_{email_id}")
        
        try:
            if os.path.exists(email_folder):
                shutil.rmtree(email_folder)
                return True
            return False
        except Exception as e:
            print(f"Error deleting attachments for email {email_id}: {e}")
            return False

    def find_duplicate_attachments(self, base_path: str) -> List[Dict[str, Any]]:
        """
        Find duplicate attachments based on file hash
        
        Args:
            base_path: Base attachment directory
            
        Returns:
            List of duplicate groups
        """
        if not os.path.exists(base_path):
            return []
            
        file_hashes = {}
        duplicates = []
        
        try:
            for root, dirs, files in os.walk(base_path):
                for filename in files:
                    file_path = os.path.join(root, filename)
                    try:
                        file_hash = self._calculate_file_hash(file_path)
                        if file_hash in file_hashes:
                            file_hashes[file_hash].append(file_path)
                        else:
                            file_hashes[file_hash] = [file_path]
                    except Exception as e:
                        print(f"Error processing file {file_path}: {e}")
                        continue
            
            # Find groups with duplicates
            for file_hash, file_paths in file_hashes.items():
                if len(file_paths) > 1:
                    duplicates.append({
                        'hash': file_hash,
                        'files': file_paths,
                        'size': os.path.getsize(file_paths[0]) if file_paths else 0,
                        'count': len(file_paths)
                    })
                    
        except Exception as e:
            print(f"Error finding duplicates: {e}")
            
        return duplicates

    def _calculate_file_hash(self, file_path: str, chunk_size: int = 8192) -> str:
        """
        Calculate MD5 hash of a file
        
        Args:
            file_path: Path to the file
            chunk_size: Size of chunks to read
            
        Returns:
            MD5 hash string
        """
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(chunk_size), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def clean_duplicate_attachments(self, base_path: str, keep_original: bool = True) -> Dict[str, Any]:
        """
        Clean duplicate attachments
        
        Args:
            base_path: Base attachment directory
            keep_original: Whether to keep the original file (True) or the first file (False)
            
        Returns:
            Dict with cleanup results
        """
        duplicates = self.find_duplicate_attachments(base_path)
        
        cleaned_count = 0
        freed_space = 0
        errors = []
        
        for duplicate_group in duplicates:
            try:
                files = duplicate_group['files']
                if len(files) < 2:
                    continue
                    
                # Sort files by modification time (oldest first)
                files.sort(key=lambda x: os.path.getmtime(x))
                
                # Keep the first file (oldest) and delete the rest
                files_to_delete = files[1:] if keep_original else files[:-1]
                
                for file_path in files_to_delete:
                    try:
                        file_size = os.path.getsize(file_path)
                        if self.delete_attachment(file_path):
                            cleaned_count += 1
                            freed_space += file_size
                    except Exception as e:
                        errors.append(f"Error deleting {file_path}: {e}")
                        
            except Exception as e:
                errors.append(f"Error processing duplicate group: {e}")
        
        return {
            'cleaned_count': cleaned_count,
            'freed_space': freed_space,
            'freed_space_formatted': format_size(freed_space),
            'errors': errors
        }

    def get_attachment_statistics(self, base_path: str) -> Dict[str, Any]:
        """
        Get statistics about attachments
        
        Args:
            base_path: Base attachment directory
            
        Returns:
            Dict with statistics
        """
        if not os.path.exists(base_path):
            return {'total_files': 0, 'total_size': 0, 'email_count': 0}
            
        total_files = 0
        total_size = 0
        email_count = 0
        
        try:
            for root, dirs, files in os.walk(base_path):
                if 'email_' in root:
                    email_count += 1
                    
                for filename in files:
                    file_path = os.path.join(root, filename)
                    try:
                        file_size = os.path.getsize(file_path)
                        total_files += 1
                        total_size += file_size
                    except Exception:
                        continue
                        
        except Exception as e:
            print(f"Error getting attachment statistics: {e}")
            
        return {
            'total_files': total_files,
            'total_size': total_size,
            'total_size_formatted': format_size(total_size),
            'email_count': email_count
        }

    def stop_operations(self):
        """Stop attachment operations"""
        self.should_stop = True 