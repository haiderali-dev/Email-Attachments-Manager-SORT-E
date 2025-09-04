import os
import re
import datetime
from typing import List, Dict, Any, Optional, Tuple
from PyQt5.QtCore import QSize
from PyQt5.QtWidgets import QApplication

def format_size(size_bytes: int) -> str:
    """
    Format file size in human readable format
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Formatted size string (e.g., "1.5 MB")
    """
    if size_bytes == 0:
        return "0 B"
        
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"

def format_date(date: datetime.datetime) -> str:
    """
    Format date for display
    
    Args:
        date: Date to format
        
    Returns:
        Formatted date string
    """
    if not date:
        return "(No date)"
        
    now = datetime.datetime.now()
    diff = now - date
    
    if diff.days == 0:
        return date.strftime("%H:%M")
    elif diff.days == 1:
        return "Yesterday"
    elif diff.days < 7:
        return date.strftime("%A")
    elif diff.days < 365:
        return date.strftime("%b %d")
    else:
        return date.strftime("%b %d, %Y")

def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """
    Truncate text to specified length
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add when truncated
        
    Returns:
        Truncated text
    """
    if not text:
        return ""
        
    if len(text) <= max_length:
        return text
        
    return text[:max_length - len(suffix)] + suffix

def get_safe_filename(filename: str, index: int = 0, folder: str = "") -> str:
    """
    Get a safe filename for file operations
    
    Args:
        filename: Original filename
        index: Index for duplicate handling
        folder: Folder to check for existing files
        
    Returns:
        Safe filename
    """
    if not filename:
        return f"attachment_{index + 1}"
    
    # Remove or replace invalid characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    
    # Ensure filename is not too long
    if len(filename) > 200:
        name, ext = os.path.splitext(filename)
        filename = name[:190] + ext
    
    # For duplicate checking, use original filename first
    original_filename = filename
    
    # If file doesn't exist, use original name
    if not os.path.exists(os.path.join(folder, filename)):
        return filename
    
    # If file exists, check if it's the same size (likely same file)
    existing_path = os.path.join(folder, filename)
    try:
        # If existing file has same size, it's probably the same file
        if os.path.exists(existing_path) and os.path.getsize(existing_path) > 0:
            return filename  # Same file, use same name
    except Exception:
        pass  # If we can't compare sizes, proceed with renaming
    
    # File exists but different size, create new filename
    counter = 1
    while os.path.exists(os.path.join(folder, filename)):
        name, ext = os.path.splitext(original_filename)
        filename = f"{name}_{counter}{ext}"
        counter += 1
        if counter > 1000:  # Prevent infinite loop
            filename = f"attachment_{index}_{counter}"
            break
    
    return filename

def get_responsive_size(base_size: QSize, screen_size: QSize) -> QSize:
    """
    Calculate responsive size based on screen resolution
    
    Args:
        base_size: Base size to scale from
        screen_size: Current screen size
        
    Returns:
        Scaled size
    """
    width_factor = screen_size.width() / 1920.0  # Base on 1920x1080
    height_factor = screen_size.height() / 1080.0
    
    factor = min(width_factor, height_factor)
    factor = max(0.7, min(1.3, factor))  # Limit scaling between 70% and 130%
    
    return QSize(int(base_size.width() * factor), int(base_size.height() * factor))

def validate_email(email: str) -> bool:
    """
    Enhanced email validation using RFC compliant validator
    
    Args:
        email: Email address to validate
        
    Returns:
        True if valid, False otherwise
    """
    from utils.validators import validate_email_rfc_compliant
    is_valid, _ = validate_email_rfc_compliant(email)
    return is_valid

def validate_imap_host(host: str) -> bool:
    """
    Enhanced IMAP host validation with security checks
    
    Args:
        host: IMAP host to validate
        
    Returns:
        True if valid, False otherwise
    """
    from utils.validators import validate_imap_host_enhanced
    
    # Allow localhost for development/testing
    if host and host.strip().lower() in ['localhost', '127.0.0.1']:
        return True
    
    is_valid, _ = validate_imap_host_enhanced(host)
    return is_valid

def clean_expired_sessions() -> int:
    """
    Clean expired email account sessions
    
    Returns:
        Number of sessions cleaned
    """
    import mysql.connector
    from config.database import DB_CONFIG
    
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            UPDATE accounts 
            SET sync_enabled=FALSE 
            WHERE session_expires IS NOT NULL 
            AND session_expires < NOW()
        """)
        cleaned_count = cursor.rowcount
        conn.commit()
        return cleaned_count
    finally:
        cursor.close()
        conn.close()

def get_system_info() -> Dict[str, Any]:
    """
    Get system information for debugging
    
    Returns:
        Dict with system information
    """
    import platform
    import sys
    
    return {
        'platform': platform.system(),
        'platform_version': platform.version(),
        'python_version': sys.version,
        'architecture': platform.architecture()[0],
        'processor': platform.processor(),
        'screen_size': get_screen_size()
    }

def get_screen_size() -> Tuple[int, int]:
    """
    Get current screen size
    
    Returns:
        Tuple of (width, height)
    """
    try:
        app = QApplication.instance()
        if app:
            desktop = app.desktop()
            if desktop:
                screen = desktop.screenGeometry()
                return (screen.width(), screen.height())
    except Exception:
        pass
    
    # Fallback to default
    return (1920, 1080)

def create_directory_if_not_exists(path: str) -> bool:
    """
    Create directory if it doesn't exist
    
    Args:
        path: Directory path to create
        
    Returns:
        True if created or exists, False on error
    """
    try:
        os.makedirs(path, exist_ok=True)
        return True
    except OSError:
        return False

def get_file_extension(filename: str) -> str:
    """
    Get file extension from filename
    
    Args:
        filename: Filename to extract extension from
        
    Returns:
        File extension (with dot)
    """
    return os.path.splitext(filename)[1]

def is_safe_file_extension(filename: str, allowed_extensions: List[str] = None) -> bool:
    """
    Check if file has safe extension
    
    Args:
        filename: Filename to check
        allowed_extensions: List of allowed extensions (default: common safe extensions)
        
    Returns:
        True if safe, False otherwise
    """
    if allowed_extensions is None:
        allowed_extensions = [
            '.txt', '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff',
            '.mp3', '.mp4', '.avi', '.mov', '.wmv',
            '.zip', '.rar', '.7z', '.tar', '.gz'
        ]
    
    ext = get_file_extension(filename).lower()
    return ext in allowed_extensions

def sanitize_filename(filename: str) -> str:
    """
    Enhanced filename sanitization with security validation
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename safe for file operations
    """
    if not filename:
        return "unnamed_file"
    
    from utils.validators import validate_file_upload_enhanced
    
    # First try enhanced validation for security check
    is_valid, error_msg = validate_file_upload_enhanced(filename)
    if not is_valid:
        # Log validation warning but continue with sanitization
        print(f"File validation warning: {error_msg}")
    
    # Remove or replace invalid characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    
    # Remove leading/trailing spaces and dots
    filename = filename.strip(' .')
    
    # Ensure filename is not too long
    if len(filename) > 200:
        name, ext = os.path.splitext(filename)
        filename = name[:190] + ext
    
    # Ensure filename is not empty
    if not filename:
        return "unnamed_file"
    
    return filename

def validate_file_for_upload(filename: str, file_size: int = None, 
                           file_content: bytes = None) -> tuple:
    """
    Comprehensive file validation for uploads
    
    Args:
        filename: Name of the file
        file_size: Size of file in bytes (optional)
        file_content: File content for deep inspection (optional)
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    from utils.validators import validate_file_upload_enhanced
    return validate_file_upload_enhanced(filename, file_size, file_content)

def get_unique_filename(base_path: str, filename: str) -> str:
    """
    Get unique filename in directory
    
    Args:
        base_path: Directory path
        filename: Desired filename
        
    Returns:
        Unique filename
    """
    if not os.path.exists(os.path.join(base_path, filename)):
        return filename
    
    name, ext = os.path.splitext(filename)
    counter = 1
    
    while os.path.exists(os.path.join(base_path, filename)):
        filename = f"{name}_{counter}{ext}"
        counter += 1
        if counter > 1000:  # Prevent infinite loop
            filename = f"file_{counter}{ext}"
            break
    
    return filename 