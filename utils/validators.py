import re
import ipaddress
import urllib.parse
from typing import Tuple, List
from config.settings import PASSWORD_REGEX

def validate_password(password):
    """Validate password against security requirements"""
    return PASSWORD_REGEX.match(password) is not None

def validate_email_rfc_compliant(email: str) -> Tuple[bool, str]:
    """
    Enhanced RFC 5322 compliant email validation
    
    Args:
        email: Email address to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not email:
        return False, "Email address is required"
    
    email = email.strip()
    
    # Check length limits
    if len(email) > 254:  # RFC 5321 limit
        return False, "Email address too long (max 254 characters)"
    
    # Must contain exactly one @ symbol
    if email.count('@') != 1:
        return False, "Email must contain exactly one @ symbol"
    
    local, domain = email.rsplit('@', 1)
    
    # Validate local part (before @)
    if not local or len(local) > 64:  # RFC 5321 limit
        return False, "Invalid local part (max 64 characters)"
    
    # Local part validation
    if local.startswith('.') or local.endswith('.'):
        return False, "Local part cannot start or end with a dot"
    
    if '..' in local:
        return False, "Local part cannot contain consecutive dots"
    
    # Allowed characters in local part
    local_pattern = r'^[a-zA-Z0-9!#$%&\'*+/=?^_`{|}~-]+(\.[a-zA-Z0-9!#$%&\'*+/=?^_`{|}~-]+)*$'
    if not re.match(local_pattern, local):
        return False, "Invalid characters in local part"
    
    # Validate domain part (after @)
    if not domain or len(domain) > 253:  # RFC 1035 limit
        return False, "Invalid domain part (max 253 characters)"
    
    # Domain must not start or end with hyphen
    if domain.startswith('-') or domain.endswith('-'):
        return False, "Domain cannot start or end with hyphen"
    
    # Check for valid domain format
    domain_parts = domain.split('.')
    if len(domain_parts) < 2:
        return False, "Domain must have at least one dot"
    
    for part in domain_parts:
        if not part:
            return False, "Domain parts cannot be empty"
        if len(part) > 63:  # RFC 1035 limit
            return False, "Domain part too long (max 63 characters)"
        if not re.match(r'^[a-zA-Z0-9-]+$', part):
            return False, "Invalid characters in domain part"
        if part.startswith('-') or part.endswith('-'):
            return False, "Domain parts cannot start or end with hyphen"
    
    # Last part should be valid TLD (at least 2 characters, letters only)
    tld = domain_parts[-1]
    if len(tld) < 2 or not re.match(r'^[a-zA-Z]+$', tld):
        return False, "Invalid top-level domain"
    
    return True, "Valid email address"

def validate_imap_host_enhanced(host: str) -> Tuple[bool, str]:
    """
    Enhanced IMAP host validation with security checks
    
    Args:
        host: IMAP host to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not host or not host.strip():
        return False, "IMAP host is required"
    
    host = host.strip()
    
    # Check length
    if len(host) > 253:
        return False, "Host name too long (max 253 characters)"
    
    # Check for dangerous characters
    dangerous_chars = ['<', '>', '"', '\'', '&', ';', '|', '`', '$']
    if any(char in host for char in dangerous_chars):
        return False, "Host contains invalid characters"
    
    # Try to parse as IP address first
    try:
        ip = ipaddress.ip_address(host)
        # Check for private/localhost IPs in production
        if ip.is_loopback:
            return False, "Localhost addresses not allowed"
        return True, "Valid IP address"
    except ValueError:
        pass  # Not an IP, continue with hostname validation
    
    # Hostname validation
    if host.startswith('.') or host.endswith('.'):
        return False, "Host cannot start or end with dot"
    
    if '..' in host:
        return False, "Host cannot contain consecutive dots"
    
    # Split into parts
    parts = host.split('.')
    if len(parts) < 2:
        return False, "Host must have at least one dot (except IP addresses)"
    
    for part in parts:
        if not part:
            return False, "Host parts cannot be empty"
        if len(part) > 63:
            return False, "Host part too long (max 63 characters)"
        if not re.match(r'^[a-zA-Z0-9-]+$', part):
            return False, "Invalid characters in host part"
        if part.startswith('-') or part.endswith('-'):
            return False, "Host parts cannot start or end with hyphen"
    
    # Check TLD
    tld = parts[-1]
    if len(tld) < 2 or not re.match(r'^[a-zA-Z]+$', tld):
        return False, "Invalid top-level domain"
    
    return True, "Valid IMAP host"

def validate_file_upload_enhanced(filename: str, file_size: int = None, 
                                file_content: bytes = None) -> Tuple[bool, str]:
    """
    Enhanced file upload validation with security checks
    
    Args:
        filename: Name of the file
        file_size: Size of file in bytes (optional)
        file_content: File content for deep inspection (optional)
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not filename:
        return False, "Filename is required"
    
    # Sanitize filename first
    filename = filename.strip()
    
    # Check filename length
    if len(filename) > 255:
        return False, "Filename too long (max 255 characters)"
    
    # Check for dangerous characters
    dangerous_chars = ['<', '>', '"', '|', '?', '*', ':', '\\', '/']
    if any(char in filename for char in dangerous_chars):
        return False, "Filename contains invalid characters"
    
    # Check for dangerous filenames
    dangerous_names = [
        'con', 'prn', 'aux', 'nul', 'com1', 'com2', 'com3', 'com4', 'com5',
        'com6', 'com7', 'com8', 'com9', 'lpt1', 'lpt2', 'lpt3', 'lpt4',
        'lpt5', 'lpt6', 'lpt7', 'lpt8', 'lpt9'
    ]
    name_without_ext = filename.rsplit('.', 1)[0].lower()
    if name_without_ext in dangerous_names:
        return False, "Reserved filename not allowed"
    
    # Check file extension
    if '.' not in filename:
        return False, "File must have an extension"
    
    ext = filename.rsplit('.', 1)[1].lower()
    
    # Allowed extensions for email attachments
    allowed_extensions = {
        # Documents
        'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt', 'rtf', 'odt',
        # Images
        'jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff', 'svg',
        # Archives
        'zip', 'rar', '7z', 'tar', 'gz',
        # Other common types
        'csv', 'xml', 'json'
    }
    
    # Dangerous extensions
    dangerous_extensions = {
        'exe', 'scr', 'bat', 'cmd', 'com', 'pif', 'vbs', 'vbe', 'js', 'jse',
        'wsf', 'wsh', 'msi', 'msp', 'hta', 'cpl', 'jar', 'ps1', 'psm1'
    }
    
    if ext in dangerous_extensions:
        return False, f"File type '{ext}' not allowed for security reasons"
    
    if ext not in allowed_extensions:
        return False, f"File type '{ext}' not supported"
    
    # Check file size if provided
    if file_size is not None:
        max_size = 25 * 1024 * 1024  # 25 MB limit
        if file_size > max_size:
            return False, f"File too large (max {max_size // (1024*1024)} MB)"
        
        if file_size <= 0:
            return False, "File is empty"
    
    # Deep content inspection if file content provided
    if file_content is not None:
        # Check for embedded executables (basic)
        dangerous_signatures = [
            b'MZ',  # PE executable
            b'\x7fELF',  # ELF executable
            b'\xca\xfe\xba\xbe',  # Java class file
            b'PK\x03\x04',  # ZIP (could contain executables)
        ]
        
        # Only check for clearly dangerous signatures in non-archive files
        if ext not in ['zip', 'rar', '7z', 'tar', 'gz']:
            for sig in dangerous_signatures[:3]:  # Skip ZIP check for non-archives
                if file_content.startswith(sig):
                    return False, "File appears to contain executable code"
    
    return True, "File validation passed"

def sanitize_input_string(input_str: str, max_length: int = 1000, 
                         allow_html: bool = False) -> str:
    """
    Sanitize input string for safe processing
    
    Args:
        input_str: Input string to sanitize
        max_length: Maximum allowed length
        allow_html: Whether to allow HTML tags
        
    Returns:
        Sanitized string
    """
    if not input_str:
        return ""
    
    # Truncate if too long
    if len(input_str) > max_length:
        input_str = input_str[:max_length]
    
    # Remove null bytes and control characters
    input_str = ''.join(char for char in input_str if ord(char) >= 32 or char in '\t\n\r')
    
    if not allow_html:
        # Escape HTML entities
        import html
        input_str = html.escape(input_str)
    
    return input_str.strip()