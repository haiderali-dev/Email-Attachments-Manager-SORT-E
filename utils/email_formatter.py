import re
import html
import base64
import mimetypes
from typing import Optional, Tuple, Dict, Any, List
from PyQt5.QtCore import QUrl
from PyQt5.QtGui import QDesktopServices
import urllib.parse

class EmailBodyFormatter:
    """
    Enhanced email body formatter with HTML rendering, link detection, inline image support, and content processing
    """
    
    def __init__(self):
        self.url_pattern = re.compile(
            r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        )
        self.email_pattern = re.compile(
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        )
        self.inline_images = {}  # Store inline images for rendering
        
    def set_inline_images(self, inline_images: List[Dict[str, Any]]):
        """Set inline images for the current email"""
        self.inline_images = {}
        for img in inline_images:
            content_id = img.get('content_id', '')
            if content_id:
                self.inline_images[content_id] = img
        
    def format_email_body(self, text_body: str = None, html_body: str = None, 
                         prefer_html: bool = True, inline_images: List[Dict[str, Any]] = None) -> Tuple[str, str]:
        """
        Format email body for display with enhanced features including inline images
        
        Args:
            text_body: Plain text version of email
            html_body: HTML version of email  
            prefer_html: Whether to prefer HTML over text when both available
            inline_images: List of inline images with content_id, data, and content_type
            
        Returns:
            Tuple of (formatted_content, content_type) where content_type is 'html' or 'text'
        """
        # Set inline images if provided
        if inline_images:
            self.set_inline_images(inline_images)
        
        # Determine which content to use
        if prefer_html and html_body:
            return self._format_html_content(html_body), 'html'
        elif text_body:
            return self._format_text_content(text_body), 'html'  # Return as HTML for consistent rendering
        elif html_body:
            return self._format_html_content(html_body), 'html'
        else:
            return self._create_no_content_message(), 'html'
    
    def _format_html_content(self, html_content: str) -> str:
        """
        Process and sanitize HTML content for safe display with inline image support
        
        Args:
            html_content: Raw HTML content
            
        Returns:
            Sanitized and enhanced HTML content with security headers and inline images
        """
        if not html_content:
            return self._create_no_content_message()
        
        # Process inline images first
        processed_html = self._process_inline_images(html_content)
        
        # Basic HTML sanitization - remove potentially dangerous elements
        sanitized = self._sanitize_html(processed_html)
        
        # Add security headers and meta tags
        secured = self._add_security_headers(sanitized)
        
        # Enhance with custom styling for better readability
        enhanced = self._add_display_styling(secured)
        
        return enhanced
    
    def _process_inline_images(self, html_content: str) -> str:
        """
        Process inline images by converting them to data URIs
        
        Args:
            html_content: HTML content with inline image references
            
        Returns:
            HTML content with inline images converted to data URIs
        """
        if not self.inline_images:
            return html_content
        
        processed_html = html_content
        
        # Replace inline image references with data URIs
        for content_id, img_data in self.inline_images.items():
            try:
                # Create data URI
                mime_type = img_data.get('content_type', 'image/jpeg')
                image_data = img_data.get('data', b'')
                
                if image_data:
                    # Encode image data to base64
                    base64_data = base64.b64encode(image_data).decode('utf-8')
                    data_uri = f"data:{mime_type};base64,{base64_data}"
                    
                    # Replace various inline image reference patterns
                    patterns = [
                        f'cid:{content_id}',  # Content-ID reference
                        f'"{content_id}"',    # Quoted content ID
                        f"'{content_id}'",    # Single quoted content ID
                    ]
                    
                    for pattern in patterns:
                        processed_html = processed_html.replace(pattern, data_uri)
                        
                    # Also replace src attributes that reference the content ID
                    src_pattern = f'src=["\']?cid:{content_id}["\']?'
                    processed_html = re.sub(src_pattern, f'src="{data_uri}"', processed_html, flags=re.IGNORECASE)
                    
            except Exception as e:
                print(f"Error processing inline image {content_id}: {e}")
                continue
        
        return processed_html
    
    def _format_text_content(self, text_content: str) -> str:
        """
        Convert plain text to HTML with enhancements
        
        Args:
            text_content: Plain text content
            
        Returns:
            HTML formatted content
        """
        if not text_content:
            return self._create_no_content_message()
        
        # Escape HTML characters
        escaped = html.escape(text_content)
        
        # Convert line breaks to HTML
        html_content = escaped.replace('\n', '<br>')
        
        # Add clickable links
        html_content = self._make_links_clickable(html_content)
        
        # Add email links
        html_content = self._make_emails_clickable(html_content)
        
        # Wrap in proper HTML structure with styling
        formatted = f"""
        <div style="{self._get_text_email_styles()}">
            {html_content}
        </div>
        """
        
        return formatted
    
    def _sanitize_html(self, html_content: str) -> str:
        """
        Enhanced HTML sanitization for safe display - Less aggressive approach
        
        Args:
            html_content: Raw HTML content
            
        Returns:
            Sanitized HTML content
        """
        if not html_content or not html_content.strip():
            return ""
        
        # Only remove the most dangerous elements
        dangerous_tags = [
            'script', 'object', 'embed', 'applet', 'iframe', 
            'frame', 'frameset', 'base'
        ]
        
        # Only remove the most dangerous event handlers
        dangerous_attributes = [
            'onload', 'onclick', 'onmouseover', 'onerror', 'onmouseout',
            'onkeydown', 'onkeyup', 'onsubmit', 'onchange', 'onfocus',
            'javascript:', 'vbscript:'
        ]
        
        sanitized = html_content
        
        # Remove dangerous tags (less aggressive pattern)
        for tag in dangerous_tags:
            # Remove opening and closing tags with content
            pattern = f'<{tag}\\b[^>]*?>.*?</{tag}>'
            sanitized = re.sub(pattern, '', sanitized, flags=re.IGNORECASE | re.DOTALL)
            # Remove self-closing tags
            pattern = f'<{tag}\\b[^>]*?/?>'
            sanitized = re.sub(pattern, '', sanitized, flags=re.IGNORECASE)
        
        # Remove dangerous attributes (less aggressive)
        for attr in dangerous_attributes:
            # Remove attribute="value" and attribute='value'
            pattern = f'{attr}\\s*=\\s*["\'][^"\']*?["\']'
            sanitized = re.sub(pattern, '', sanitized, flags=re.IGNORECASE)
            # Remove attribute=value (without quotes) - but be more careful
            pattern = f'{attr}\\s*=\\s*[^\\s>]*'
            sanitized = re.sub(pattern, '', sanitized, flags=re.IGNORECASE)
        
        # Fix malformed HTML that might break display
        sanitized = self._fix_html_structure(sanitized)
        
        # Process and fix anchor tags for proper rendering
        sanitized = self._process_anchor_tags(sanitized)
        
        # Convert external links to safe internal handling
        sanitized = self._make_external_links_safe(sanitized)
        
        return sanitized
    
    def _add_security_headers(self, html_content: str) -> str:
        """
        Add security headers and meta tags to HTML content
        
        Args:
            html_content: HTML content to secure
            
        Returns:
            HTML content with security headers
        """
        if not html_content or not html_content.strip():
            return html_content
        
        # Define Content Security Policy for email content
        csp_policy = (
            "default-src 'self'; "
            "script-src 'none'; "
            "object-src 'none'; "
            "frame-src 'none'; "
            "base-uri 'none'; "
            "form-action 'none'; "
            "img-src 'self' data: https:; "
            "style-src 'self' 'unsafe-inline'; "
            "font-src 'self' data:; "
            "connect-src 'none'"
        )
        
        # Security meta tags
        security_headers = f'''
<meta http-equiv="Content-Security-Policy" content="{csp_policy}">
<meta http-equiv="X-Content-Type-Options" content="nosniff">
<meta http-equiv="X-Frame-Options" content="DENY">
<meta http-equiv="X-XSS-Protection" content="1; mode=block">
<meta http-equiv="Referrer-Policy" content="strict-origin-when-cross-origin">
'''
        
        # Check if HTML has proper structure
        if '<html' in html_content.lower():
            # Full HTML document - add headers to head section
            if '<head>' in html_content.lower():
                html_content = html_content.replace('<head>', f'<head>{security_headers}', 1)
            elif '<html>' in html_content.lower():
                html_content = html_content.replace('<html>', f'<html><head>{security_headers}</head>', 1)
            else:
                # HTML tag with attributes
                import re
                html_content = re.sub(r'(<html[^>]*>)', f'\\1<head>{security_headers}</head>', html_content, count=1, flags=re.IGNORECASE)
        else:
            # HTML fragment - wrap with security headers
            html_content = f'''<!DOCTYPE html>
<html>
<head>
{security_headers}
<meta charset="UTF-8">
<title>Email Content</title>
</head>
<body>
{html_content}
</body>
</html>'''
        
        return html_content
    
    def _fix_html_structure(self, html_content: str) -> str:
        """
        Fix common HTML structure issues that might break display - Less aggressive approach
        
        Args:
            html_content: HTML content to fix
            
        Returns:
            Fixed HTML content
        """
        if not html_content:
            return ""
        
        # Only wrap in container if it's completely plain text
        if not html_content.strip().startswith('<') and not html_content.strip().startswith('<!DOCTYPE'):
            html_content = f'<div>{html_content}</div>'
        
        # Fix only the most critical HTML issues
        # Convert self-closing tags that might cause issues
        self_closing_tags = ['img', 'br', 'hr']
        for tag in self_closing_tags:
            # Find tags that are not properly closed
            pattern = f'<{tag}\\b([^>]*?)(?<!\\/)>'
            replacement = f'<{tag}\\1/>'
            html_content = re.sub(pattern, replacement, html_content, flags=re.IGNORECASE)
        
        # Ensure anchor tags are properly structured
        # Fix unclosed anchor tags
        html_content = re.sub(r'<a([^>]*?)(?<!>)>', r'<a\1></a>', html_content, flags=re.IGNORECASE)
        
        # Fix malformed href attributes
        html_content = re.sub(r'href\s*=\s*([^"\s>]+)', r'href="\1"', html_content, flags=re.IGNORECASE)
        
        return html_content
    
    def _process_anchor_tags(self, html_content: str) -> str:
        """
        Process and fix anchor tags to ensure proper HTML rendering
        
        Args:
            html_content: HTML content with anchor tags
            
        Returns:
            HTML with properly formatted anchor tags
        """
        if not html_content:
            return ""
        
        # Pattern to match anchor tags
        anchor_pattern = r'<a\b([^>]*?)>'
        
        def process_anchor(match):
            tag_attributes = match.group(1)
            
            # Ensure href attribute exists and is properly formatted
            if 'href=' not in tag_attributes:
                # If no href, add a placeholder
                tag_attributes += ' href="#"'
            
            # Ensure proper attribute formatting
            # Fix missing quotes around attribute values
            tag_attributes = re.sub(r'(\w+)=([^"\s>]+)', r'\1="\2"', tag_attributes)
            
            # Ensure target and rel attributes for external links
            href_match = re.search(r'href=["\']([^"\']+)["\']', tag_attributes)
            if href_match:
                url = href_match.group(1)
                if url.startswith(('http://', 'https://')) and not url.startswith(('http://localhost', 'https://localhost')):
                    if 'target=' not in tag_attributes:
                        tag_attributes += ' target="_blank"'
                    if 'rel=' not in tag_attributes:
                        tag_attributes += ' rel="noopener noreferrer"'
            
            # Add default styling if not present
            if 'style=' not in tag_attributes:
                tag_attributes += ' style="color: #0066cc; text-decoration: underline;"'
            
            return f'<a{tag_attributes}>'
        
        # Process all anchor tags
        processed_html = re.sub(anchor_pattern, process_anchor, html_content, flags=re.IGNORECASE)
        
        return processed_html
    
    def _make_links_clickable(self, text: str) -> str:
        """
        Convert URLs in text to clickable HTML links
        
        Args:
            text: Text content with URLs
            
        Returns:
            Text with clickable links
        """
        def replace_url(match):
            url = match.group(0)
            # Ensure URL is properly formatted
            if not url.startswith(('http://', 'https://')):
                url = 'http://' + url
            return f'<a href="{url}" style="color: #0066cc; text-decoration: underline;">{match.group(0)}</a>'
        
        return self.url_pattern.sub(replace_url, text)
    
    def _make_emails_clickable(self, text: str) -> str:
        """
        Convert email addresses in text to clickable mailto links
        
        Args:
            text: Text content with email addresses
            
        Returns:
            Text with clickable email links
        """
        def replace_email(match):
            email = match.group(0)
            return f'<a href="mailto:{email}" style="color: #0066cc; text-decoration: underline;">{email}</a>'
        
        return self.email_pattern.sub(replace_email, text)
    
    def _make_external_links_safe(self, html_content: str) -> str:
        """
        Make external links safe by adding proper attributes and ensure proper HTML rendering
        
        Args:
            html_content: HTML content with links
            
        Returns:
            HTML with safe external links and proper rendering
        """
        # Pattern to match anchor tags with href attributes
        link_pattern = r'<a\b([^>]*?href\s*=\s*["\']([^"\']+)["\'][^>]*?)>'
        
        def replace_link(match):
            full_tag = match.group(1)
            url = match.group(2)
            
            # Check if it's an external link
            if url.startswith(('http://', 'https://')) and not url.startswith(('http://localhost', 'https://localhost')):
                # Add security attributes while preserving existing ones
                if 'target=' not in full_tag:
                    full_tag += ' target="_blank"'
                if 'rel=' not in full_tag:
                    full_tag += ' rel="noopener noreferrer"'
                if 'style=' not in full_tag:
                    full_tag += ' style="color: #0066cc; text-decoration: underline;"'
                else:
                    # Add to existing style
                    full_tag = re.sub(r'style=["\']([^"\']*)["\']', 
                                    r'style="\1; color: #0066cc; text-decoration: underline;"', 
                                    full_tag)
            
            return f'<a{full_tag}>'
        
        # Process the HTML content
        processed_html = re.sub(link_pattern, replace_link, html_content, flags=re.IGNORECASE)
        
        # Ensure all anchor tags are properly closed
        processed_html = re.sub(r'<a([^>]*?)(?<!>)>', r'<a\1></a>', processed_html, flags=re.IGNORECASE)
        
        return processed_html
    
    def _add_display_styling(self, html_content: str) -> str:
        """
        Add enhanced styling for better email display
        
        Args:
            html_content: HTML content
            
        Returns:
            HTML with enhanced styling
        """
        # Wrap content with improved styling
        styled_content = f"""
        <div style="{self._get_email_container_styles()}">
            {html_content}
        </div>
        """
        
        return styled_content
    
    def _get_email_container_styles(self) -> str:
        """Get CSS styles for email container"""
        return """
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            font-size: 14px;
            line-height: 1.6;
            color: #333;
            max-width: 100%;
            word-wrap: break-word;
            padding: 15px;
            background-color: #ffffff;
        """
    
    def _get_text_email_styles(self) -> str:
        """Get CSS styles for plain text emails converted to HTML"""
        return """
            font-family: 'Courier New', Consolas, monospace;
            font-size: 13px;
            line-height: 1.5;
            color: #333;
            white-space: pre-wrap;
            word-wrap: break-word;
            padding: 15px;
            background-color: #f8f9fa;
            border-left: 4px solid #0066cc;
            margin: 10px 0;
        """
    
    def _create_no_content_message(self) -> str:
        """Create a styled message for emails with no content"""
        return """
        <div style="text-align: center; padding: 40px; color: #666; font-style: italic;">
            <p>📭 No email content available</p>
            <p style="font-size: 12px;">This email may contain only attachments or the content could not be retrieved.</p>
        </div>
        """
    
    def extract_plain_text(self, html_content: str) -> str:
        """
        Extract plain text from HTML content for search and indexing
        
        Args:
            html_content: HTML content
            
        Returns:
            Plain text version
        """
        if not html_content:
            return ""
        
        # Simple HTML tag removal for plain text extraction
        text = re.sub(r'<[^>]+>', '', html_content)
        
        # Decode HTML entities
        text = html.unescape(text)
        
        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def get_content_preview(self, content: str, max_length: int = 150) -> str:
        """
        Get a preview of email content for list display
        
        Args:
            content: Email content (HTML or text)
            max_length: Maximum length of preview
            
        Returns:
            Content preview
        """
        # Extract plain text if it's HTML
        if content and content.strip().startswith('<'):
            preview_text = self.extract_plain_text(content)
        else:
            preview_text = content or ""
        
        # Truncate if too long
        if len(preview_text) > max_length:
            preview_text = preview_text[:max_length] + "..."
        
        return preview_text
    
    def get_word_count(self, content: str) -> int:
        """
        Get word count from email content
        
        Args:
            content: Email content (HTML or text)
            
        Returns:
            Word count
        """
        if not content:
            return 0
        
        # Extract plain text if it's HTML
        if content.strip().startswith('<'):
            text = self.extract_plain_text(content)
        else:
            text = content
        
        # Count words
        words = text.split()
        return len(words)
    
    def detect_content_type(self, content: str) -> str:
        """
        Detect the type of content in the email
        
        Args:
            content: Email content
            
        Returns:
            Content type description
        """
        if not content:
            return "empty"
        
        content_lower = content.lower()
        
        # Check for HTML indicators
        html_indicators = ['<html>', '<body>', '<div>', '<p>', '<br>', '<table>', '<img', '<a ', '<!doctype']
        html_score = sum(1 for indicator in html_indicators if indicator in content_lower)
        
        # Check for email-specific patterns
        email_patterns = ['@', 'subject:', 'from:', 'to:', 'date:', 'cc:', 'bcc:']
        email_score = sum(1 for pattern in email_patterns if pattern in content_lower)
        
        # Determine content type
        if html_score >= 3:
            return "html_email"
        elif email_score >= 2:
            return "email_text"
        elif '<' in content and '>' in content:
            return "html_fragment"
        else:
            return "plain_text"
    
    @staticmethod
    def open_external_link(url: str):
        """
        Safely open external links in default browser
        
        Args:
            url: URL to open
        """
        try:
            # Validate URL format
            if not url.startswith(('http://', 'https://', 'mailto:')):
                if '@' in url:
                    url = 'mailto:' + url
                else:
                    url = 'http://' + url
            
            QDesktopServices.openUrl(QUrl(url))
        except Exception as e:
            print(f"Error opening URL {url}: {e}")
